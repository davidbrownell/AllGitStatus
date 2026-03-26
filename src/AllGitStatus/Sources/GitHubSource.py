# noqa: D100
import re
import textwrap

from collections.abc import AsyncGenerator

import aiohttp

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo, Source


# ----------------------------------------------------------------------
class GitHubSource(Source):
    """Source for GitHub repository information (stars, forks, issues, etc.)."""

    # ----------------------------------------------------------------------
    @staticmethod
    def CreateGitHubHttpHeaders(github_pat: str | None = None) -> dict[str, str]:
        """Create headers for GitHub API access."""

        headers: dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        if github_pat:
            headers["Authorization"] = f"Bearer {github_pat}"

        return headers

    # ----------------------------------------------------------------------
    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        self._session = session

    # ----------------------------------------------------------------------
    def Applies(self, repo: Repository) -> bool:  # noqa: D102
        return bool(repo.github_owner and repo.github_repo)

    # ----------------------------------------------------------------------
    async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # noqa: D102  # ty: ignore[invalid-method-override]
        assert self.Applies(repo)
        assert repo.remote_url is not None

        github_url = repo.remote_url.removesuffix(".git")

        persisted_info: dict[str, object] = {}

        async for info in self._GenerateStandardInfo(repo, github_url, persisted_info):
            yield info

        async for info in self._GenerateIssueInfo(repo, github_url):
            yield info

        async for info in self._GeneratePullRequestInfo(repo, github_url):
            yield info

        async for info in self._GenerateSecurityAlertInfo(repo, github_url):
            yield info

        default_branch = persisted_info.get("default_branch")

        # Only generate CI/CD info if we have a default branch (repo API succeeded)
        if isinstance(default_branch, str):
            async for info in self._GenerateCICDInfo(repo, github_url, default_branch):
                yield info

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    async def _GenerateStandardInfo(
        self,
        repo: Repository,
        github_url: str,
        persisted_info: dict[str, object],
    ) -> AsyncGenerator[ResultInfo | ErrorInfo]:
        try:
            async with self._session.get(
                f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}"
            ) as response:
                response.raise_for_status()
                result = await response.json()

                # Capture default_branch for use by CI/CD status
                persisted_info["default_branch"] = result.get("default_branch")

                yield ResultInfo(
                    repo,
                    (self.__class__.__name__, "stars"),
                    f"{result.get('stargazers_count', 0):5} ⭐",
                    f"{github_url}/stargazers",
                )

                yield ResultInfo(
                    repo,
                    (self.__class__.__name__, "forks"),
                    f"{result.get('forks_count', 0):5} 🍴",
                    f"{github_url}/forks",
                )

                yield ResultInfo(
                    repo,
                    (self.__class__.__name__, "watchers"),
                    f"{result.get('subscribers_count', 0):5} 👀",
                    f"{github_url}/watchers",
                )

        except Exception as ex:
            yield ErrorInfo(
                repo,
                (self.__class__.__name__, "stars"),
                ex,
            )

    # ----------------------------------------------------------------------
    async def _GenerateIssueInfo(
        self,
        repo: Repository,
        github_url: str,
    ) -> AsyncGenerator[ResultInfo | ErrorInfo]:
        try:
            label_counts: dict[str, int] = {}
            total_count = 0
            issue_data: list[str] = []

            async for issue in self._GeneratePaginatedResults(
                f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}/issues"
            ):
                # GitHub API returns pull requests as issues with a "pull_request" key - skip them
                if "pull_request" in issue:
                    continue

                labels = issue.get("labels", [])

                for label in labels:
                    label_name = label.get("name", "")

                    if label_name:
                        label_counts[label_name] = label_counts.get(label_name, 0) + 1

                total_count += 1

                issue_number = issue.get("number", "?")
                issue_title = issue.get("title", "No title")
                issue_author = issue.get("user", {}).get("login", "unknown")
                issue_labels = [label.get("name", "") for label in issue.get("labels", [])]

                label_str = f" [{', '.join(issue_labels)}]" if issue_labels else ""

                issue_data.append(f"• #{issue_number}{label_str} {issue_title} (by {issue_author})")

            # Build additional info with issue details
            additional_info_lines = [
                f"Issues: {github_url}/issues",
                "",
                f"Total Open Issues: {total_count}",
                "",
            ]

            if label_counts:
                additional_info_lines.append("By Label:")

                for label_name, count in sorted(label_counts.items(), key=lambda x: -x[1]):
                    additional_info_lines.append(f"  {label_name}: {count}")

                additional_info_lines.append("")

            additional_info_lines.extend(issue_data)

            yield ResultInfo(
                repo,
                (self.__class__.__name__, "issues"),
                f"{total_count:5} 🐛",
                "\n".join(additional_info_lines),
            )

        except Exception as ex:
            yield ErrorInfo(
                repo,
                (self.__class__.__name__, "issues"),
                ex,
            )

    # ----------------------------------------------------------------------
    async def _GeneratePullRequestInfo(
        self,
        repo: Repository,
        github_url: str,
    ) -> AsyncGenerator[ResultInfo | ErrorInfo]:
        try:
            total_count = 0
            pr_data: list[str] = []

            async for pr in self._GeneratePaginatedResults(
                f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}/pulls"
            ):
                total_count += 1

                pr_number = pr.get("number", "?")
                pr_title = pr.get("title", "No title")
                pr_author = pr.get("user", {}).get("login", "unknown")
                pr_draft = pr.get("draft", False)

                draft_indicator = "[DRAFT] " if pr_draft else ""

                pr_data.append(f"• #{pr_number} {draft_indicator}{pr_title} (by {pr_author})")

            additional_info_lines = [
                f"Pull Requests: {github_url}/pulls",
                "",
                f"Total Open PRs: {total_count}",
                "",
            ]

            additional_info_lines.extend(pr_data)

            yield ResultInfo(
                repo,
                (self.__class__.__name__, "pull_requests"),
                f"{total_count:5} 🔀",
                "\n".join(additional_info_lines),
            )

        except Exception as ex:
            yield ErrorInfo(
                repo,
                (self.__class__.__name__, "pull_requests"),
                ex,
            )

    # ----------------------------------------------------------------------
    async def _GenerateSecurityAlertInfo(
        self,
        repo: Repository,
        github_url: str,
    ) -> AsyncGenerator[ResultInfo | ErrorInfo]:
        try:
            severity_counts: dict[str, int] = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }
            total_count = 0
            alert_data: list[str] = []

            async for alert in self._GeneratePaginatedResults(
                f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}/dependabot/alerts"
            ):
                severity = alert.get("security_advisory", {}).get("severity", "").lower()

                if severity in severity_counts:
                    severity_counts[severity] += 1

                total_count += 1

                advisory = alert.get("security_advisory", {})
                package = alert.get("security_vulnerability", {}).get("package", {})

                alert_data.append(
                    f"• [{advisory.get('severity', 'unknown').upper()}] {package.get('name', 'unknown')}: {advisory.get('summary', 'No summary')}"
                )

            # Build display value with icon based on severity
            if total_count == 0:
                icon = "🔒"
            elif severity_counts["critical"] > 0:
                icon = "🚨"
            elif severity_counts["high"] > 0:
                icon = "⚠️"
            else:
                icon = "🔔"

            display_value = f"{total_count:3} {icon}"

            # Build additional info with severity breakdown
            additional_info_lines = [
                f"Security Alerts: {github_url}/security/dependabot",
                "",
                f"Total Open Alerts: {total_count}",
                "",
                f"  Critical: {severity_counts['critical']}",
                f"  High:     {severity_counts['high']}",
                f"  Medium:   {severity_counts['medium']}",
                f"  Low:      {severity_counts['low']}",
                "",
            ]

            additional_info_lines.extend(alert_data)

            yield ResultInfo(
                repo,
                (self.__class__.__name__, "security_alerts"),
                display_value,
                "\n".join(additional_info_lines),
            )

        except Exception as ex:
            yield ErrorInfo(
                repo,
                (self.__class__.__name__, "security_alerts"),
                ex,
            )

    # ----------------------------------------------------------------------
    async def _GenerateCICDInfo(
        self,
        repo: Repository,
        github_url: str,
        default_branch: str,
    ) -> AsyncGenerator[ResultInfo | ErrorInfo]:
        info_key = (self.__class__.__name__, "cicd_status")

        try:
            url = f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}/actions/runs?branch={default_branch}&per_page=100"

            async with self._session.get(url) as response:
                response.raise_for_status()
                result = await response.json()

                workflow_runs = result.get("workflow_runs", [])

                if not workflow_runs:
                    yield ResultInfo(
                        repo,
                        info_key,
                        "🔘",
                        textwrap.dedent(
                            """\
                                CI/CD Status: {github_url}/actions

                                No workflow runs found for branch '{default_branch}'
                                """,
                        ).format(
                            github_url=github_url,
                            default_branch=default_branch,
                        ),
                    )
                    return

                # Group by workflow name and take only the most recent run for each
                latest_per_workflow: dict[str, dict] = {}

                for run in workflow_runs:
                    workflow_id = run["workflow_id"]

                    if workflow_id not in latest_per_workflow:
                        latest_per_workflow[workflow_id] = run

                # Count statuses based on most recent run per workflow
                status_counts = {
                    "success": 0,
                    "failure": 0,
                    "in_progress": 0,
                }

                run_details: list[str] = []

                for run in latest_per_workflow.values():
                    conclusion = run.get("conclusion")
                    status = run.get("status")

                    # Determine the effective status
                    if status in ("in_progress", "queued", "pending", "waiting"):
                        status_counts["in_progress"] += 1
                        status_label = "IN PROG"
                    elif conclusion == "success":
                        status_counts["success"] += 1
                        status_label = " PASS  "
                    elif conclusion in ("failure", "cancelled", "timed_out"):
                        status_counts["failure"] += 1
                        status_label = " FAIL  "
                    else:
                        status_label = conclusion or status or "UNKNOWN"

                    run_details.append(f"• [{status_label}] {run['created_at']} {run['path']}: {run['name']}")

                # Determine display icon based on priority: failure > in_progress > success
                if status_counts["failure"] > 0:
                    display_icon = "❌"
                elif status_counts["in_progress"] > 0:
                    display_icon = "⏳"
                elif status_counts["success"] > 0:
                    display_icon = "✅"
                else:
                    display_icon = "🔘"

                # Build additional info
                additional_info_lines = [
                    f"CI/CD Status: {github_url}/actions",
                    "",
                    f"Default Branch: {default_branch}",
                    "",
                    "Summary (latest run per workflow):",
                    f"  Successful:  {status_counts['success']}",
                    f"  Failed:      {status_counts['failure']}",
                    f"  In Progress: {status_counts['in_progress']}",
                    "",
                ]

                additional_info_lines.extend(run_details)

                yield ResultInfo(
                    repo,
                    info_key,
                    display_icon,
                    "\n".join(additional_info_lines),
                )

        except Exception as ex:
            yield ErrorInfo(
                repo,
                info_key,
                ex,
            )

    # ----------------------------------------------------------------------
    async def _GeneratePaginatedResults(self, raw_url: str) -> AsyncGenerator[dict]:
        url: str | None = f"{raw_url}?state=open&per_page=100"
        next_page_regex = re.compile(r"<([^>]+)>")

        while url:
            async with self._session.get(url) as response:
                response.raise_for_status()

                results = await response.json()

                for result in results:
                    yield result

                url = None
                link_header = response.headers.get("Link", "")

                for link in link_header.split(","):
                    if 'rel="next"' in link:
                        match = next_page_regex.search(link)
                        if match:
                            url = match.group(1)

                        break

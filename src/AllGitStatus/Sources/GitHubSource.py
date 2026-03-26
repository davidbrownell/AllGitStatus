# noqa: D100
import re
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
    async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # noqa: D102, PLR0915  # ty: ignore[invalid-method-override]
        assert self.Applies(repo)
        assert repo.remote_url is not None

        github_url = repo.remote_url.removesuffix(".git")

        async with self._session.get(
            f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}"
        ) as response:
            try:
                response.raise_for_status()
                result = await response.json()

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
                    (self.__class__.__name__, "issues"),
                    f"{result.get('open_issues_count', 0):5} 🐛",
                    f"{github_url}/issues",
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

        # Fetch open pull requests count using search API
        async with self._session.get(
            "https://api.github.com/search/issues",
            params={"q": f"repo:{repo.github_owner}/{repo.github_repo} is:pr is:open"},
        ) as pr_response:
            try:
                pr_response.raise_for_status()
                pr_result = await pr_response.json()

                pr_count = pr_result.get("total_count", 0)

                yield ResultInfo(
                    repo,
                    (self.__class__.__name__, "pull_requests"),
                    f"{pr_count:5} 🔀",
                    f"{github_url}/pulls",
                )

            except Exception as ex:
                yield ErrorInfo(
                    repo,
                    (self.__class__.__name__, "pull_requests"),
                    ex,
                )

        # Fetch security alerts (Dependabot alerts) with pagination via Link header
        try:
            alerts: list[dict] = []
            url: str | None = (
                f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}/dependabot/alerts"
                "?state=open&per_page=100"
            )

            next_page_regex = re.compile(r"<([^>]+)>")

            while url:
                async with self._session.get(url) as alerts_response:
                    alerts_response.raise_for_status()
                    page_alerts = await alerts_response.json()

                    alerts.extend(page_alerts)

                    # Parse Link header for next page URL
                    url = None
                    link_header = alerts_response.headers.get("Link", "")

                    for link in link_header.split(","):
                        if 'rel="next"' in link:
                            match = next_page_regex.search(link)
                            if match:
                                url = match.group(1)

                            break

            # Count alerts by severity
            severity_counts: dict[str, int] = {
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            }

            for alert in alerts:
                severity = alert.get("security_advisory", {}).get("severity", "").lower()

                if severity in severity_counts:
                    severity_counts[severity] += 1

            total_alerts = len(alerts)

            # Build display value with icon based on severity
            if total_alerts == 0:
                icon = "🔒"
            elif severity_counts["critical"] > 0:
                icon = "🚨"
            elif severity_counts["high"] > 0:
                icon = "⚠️"
            else:
                icon = "🔔"

            display_value = f"{total_alerts:3} {icon}"

            # Build additional info with severity breakdown
            additional_info_lines = [
                f"Security Alerts: {github_url}/security/dependabot",
                "",
                f"Total Open Alerts: {total_alerts}",
                "",
                f"  Critical: {severity_counts['critical']}",
                f"  High:     {severity_counts['high']}",
                f"  Medium:   {severity_counts['medium']}",
                f"  Low:      {severity_counts['low']}",
                "",
            ]

            for alert in alerts:
                advisory = alert.get("security_advisory", {})
                package = alert.get("security_vulnerability", {}).get("package", {})
                additional_info_lines.append(
                    f"  • [{advisory.get('severity', 'unknown').upper()}] "
                    f"{package.get('name', 'unknown')}: {advisory.get('summary', 'No summary')}"
                )

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

"""Integration tests for AllGitStatus.Sources.GitHubSource module.

These tests make real API calls to GitHub using the davidbrownell/AllGitStatus repository.
"""

import os

from pathlib import Path

import aiohttp
import pytest

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.GitHubSource import GitHubSource
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo


# ----------------------------------------------------------------------
@pytest.fixture
def allgitstatus_repo() -> Repository:
    """Create a Repository object for the davidbrownell/AllGitStatus repository."""

    return Repository(
        path=Path.cwd(),
        remote_url="https://github.com/davidbrownell/AllGitStatus.git",
        github_owner="davidbrownell",
        github_repo="AllGitStatus",
    )


# ----------------------------------------------------------------------
@pytest.fixture
def non_github_repo() -> Repository:
    """Create a Repository object without GitHub info."""

    return Repository(
        path=Path("/local/repo"),
        remote_url="https://gitlab.com/user/repo.git",
        github_owner=None,
        github_repo=None,
    )


# ----------------------------------------------------------------------
@pytest.fixture
async def session():
    """Create an aiohttp session for GitHub API requests."""

    headers = GitHubSource.CreateGitHubHttpHeaders(os.getenv("GITHUB_TOKEN"))
    session = aiohttp.ClientSession(headers=headers)

    try:
        yield session
    finally:
        await session.close()


# ----------------------------------------------------------------------
class TestGitHubSourceApplies:
    """Tests for GitHubSource.Applies method."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_applies_to_github_repo(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Source applies to repositories with GitHub owner and repo."""

        source = GitHubSource(session)

        assert source.Applies(allgitstatus_repo) is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_does_not_apply_to_non_github_repo(
        self, session: aiohttp.ClientSession, non_github_repo: Repository
    ) -> None:
        """Source does not apply to repositories without GitHub info."""

        source = GitHubSource(session)

        assert source.Applies(non_github_repo) is False

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_does_not_apply_when_owner_missing(self, session: aiohttp.ClientSession) -> None:
        """Source does not apply when github_owner is None."""

        repo = Repository(
            path=Path("/test"),
            remote_url="https://github.com/owner/repo.git",
            github_owner=None,
            github_repo="repo",
        )

        source = GitHubSource(session)

        assert source.Applies(repo) is False

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_does_not_apply_when_repo_missing(self, session: aiohttp.ClientSession) -> None:
        """Source does not apply when github_repo is None."""

        repo = Repository(
            path=Path("/test"),
            remote_url="https://github.com/owner/repo.git",
            github_owner="owner",
            github_repo=None,
        )

        source = GitHubSource(session)

        assert source.Applies(repo) is False


# ----------------------------------------------------------------------
class TestGitHubSourceQuery:
    """Integration tests for GitHubSource.Query method using real GitHub API."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_query_returns_valid_results(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Query returns N ResultInfo items with correct structure and content."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # We should get results for each API endpoint:
        # - Standard info API yields 3 results on success (stars, forks, watchers) or 1 error on failure
        # - Issues API yields 1 result
        # - Pull requests API yields 1 result
        # - Security alerts API yields 1 result
        # So we get 6 results on success, or 4 results if the first API fails
        assert len(results) >= 4

        # All results should reference the same repo
        for result in results:
            assert result.repo is allgitstatus_repo

        # Build a dict for easier lookup (only ResultInfo items)
        results_by_key = {r.key[1]: r for r in results if isinstance(r, ResultInfo)}

        # If we hit rate limiting (no ResultInfo items), skip the detailed assertions
        if not results_by_key:
            # Verify we at least got ErrorInfo items with correct keys
            error_keys = {r.key[1] for r in results if isinstance(r, ErrorInfo)}
            assert "stars" in error_keys  # First API call would fail if rate limited
            pytest.skip("GitHub API rate limit exceeded - skipping detailed assertions")

        # Verify stars info (if not rate limited)
        if "stars" in results_by_key:
            stars = results_by_key["stars"]
            assert stars.key == ("GitHubSource", "stars")
            assert "\u2b50" in stars.display_value
            assert stars.additional_info == "https://github.com/davidbrownell/AllGitStatus/stargazers"

        # Verify forks info (if not rate limited)
        if "forks" in results_by_key:
            forks = results_by_key["forks"]
            assert forks.key == ("GitHubSource", "forks")
            assert "\U0001f374" in forks.display_value
            assert forks.additional_info == "https://github.com/davidbrownell/AllGitStatus/forks"

        # Verify issues info (if not rate limited)
        if "issues" in results_by_key:
            issues = results_by_key["issues"]
            assert issues.key == ("GitHubSource", "issues")
            assert "\U0001f41b" in issues.display_value
            # additional_info now contains detailed issue info, not just URL
            assert isinstance(issues.additional_info, str)
            assert "github.com/davidbrownell/AllGitStatus/issues" in issues.additional_info
            assert "Total Open Issues:" in issues.additional_info

        # Verify watchers info (if not rate limited)
        if "watchers" in results_by_key:
            watchers = results_by_key["watchers"]
            assert watchers.key == ("GitHubSource", "watchers")
            assert "\U0001f440" in watchers.display_value
            assert watchers.additional_info == "https://github.com/davidbrownell/AllGitStatus/watchers"

        # Verify pull_requests info (if not rate limited)
        if "pull_requests" in results_by_key:
            pull_requests = results_by_key["pull_requests"]
            assert pull_requests.key == ("GitHubSource", "pull_requests")
            assert "\U0001f500" in pull_requests.display_value
            # additional_info now contains detailed PR info, not just URL
            assert isinstance(pull_requests.additional_info, str)
            assert "github.com/davidbrownell/AllGitStatus/pulls" in pull_requests.additional_info
            assert "Total Open PRs:" in pull_requests.additional_info

        # Verify all display values contain numeric counts (for ResultInfo items)
        for result in results:
            if isinstance(result, ResultInfo) and result.key[1] not in ["cicd_status", "archived", "release"]:
                number_part = result.display_value.split()[0]
                assert number_part.isdigit(), f"Expected number in '{result.display_value}'"

        # Verify URLs don't have .git suffix (for ResultInfo items with URL additional_info)
        for result in results:
            if isinstance(result, ResultInfo) and isinstance(result.additional_info, str):
                if result.additional_info.startswith("http"):
                    assert not result.additional_info.endswith(".git")
                    assert "github.com/davidbrownell/AllGitStatus/" in result.additional_info

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_query_nonexistent_repo_returns_error(self, session: aiohttp.ClientSession) -> None:
        """Query returns ErrorInfo for non-existent repository."""

        repo = Repository(
            path=Path("/test"),
            remote_url="https://github.com/nonexistent-user-12345/nonexistent-repo-67890.git",
            github_owner="nonexistent-user-12345",
            github_repo="nonexistent-repo-67890",
        )

        source = GitHubSource(session)

        results = [info async for info in source.Query(repo)]

        # Five API calls for nonexistent repos (stars, issues, pull_requests, security_alerts, release)
        # CI/CD is skipped because we don't have default_branch when repo API fails
        # Note: release returns ResultInfo with "-" when no releases found (404)
        assert len(results) == 5
        assert results[0].key == ("GitHubSource", "stars")
        assert results[1].key == ("GitHubSource", "issues")
        assert results[2].key == ("GitHubSource", "pull_requests")
        assert results[3].key == ("GitHubSource", "security_alerts")
        assert results[4].key == ("GitHubSource", "release")
        # First four results are errors, release may be a ResultInfo (404 handled gracefully)
        assert all(isinstance(r, ErrorInfo) for r in results[:4])


# ----------------------------------------------------------------------
class TestGitHubSourceSecurityAlerts:
    """Tests for GitHubSource security alerts functionality."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_security_alerts_result_has_correct_key(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Security alerts result has the correct key structure."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the security_alerts result
        security_result = next((r for r in results if r.key[1] == "security_alerts"), None)

        assert security_result is not None
        assert security_result.key == ("GitHubSource", "security_alerts")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_security_alerts_display_value_format(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Security alerts display value contains a count and an icon."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the security_alerts result
        security_result = next(
            (r for r in results if r.key[1] == "security_alerts" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify the format
        if security_result is not None:
            # Display value should contain a number and one of the security icons
            assert any(icon in security_result.display_value for icon in ["🔒", "🚨", "⚠️", "🔔"])

            # Should have a numeric count
            number_part = security_result.display_value.split()[0]
            assert number_part.isdigit()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_security_alerts_additional_info_contains_url(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Security alerts additional info contains the security page URL."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the security_alerts result
        security_result = next(
            (r for r in results if r.key[1] == "security_alerts" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify additional info
        if security_result is not None:
            assert isinstance(security_result.additional_info, str)
            assert "security/dependabot" in security_result.additional_info
            assert "github.com/davidbrownell/AllGitStatus" in security_result.additional_info

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_security_alerts_additional_info_contains_severity_breakdown(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Security alerts additional info contains severity breakdown."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the security_alerts result
        security_result = next(
            (r for r in results if r.key[1] == "security_alerts" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify severity breakdown
        if security_result is not None:
            assert isinstance(security_result.additional_info, str)
            assert "Critical:" in security_result.additional_info
            assert "High:" in security_result.additional_info
            assert "Medium:" in security_result.additional_info
            assert "Low:" in security_result.additional_info


# ----------------------------------------------------------------------
class TestGitHubSourceIssues:
    """Integration tests for GitHubSource issues functionality."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_issues_result_has_correct_key(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Issues result has the correct key structure."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the issues result
        issues_result = next((r for r in results if r.key[1] == "issues"), None)

        assert issues_result is not None
        assert issues_result.key == ("GitHubSource", "issues")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_issues_display_value_format(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Issues display value contains a count and the bug icon."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the issues result
        issues_result = next(
            (r for r in results if r.key[1] == "issues" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify the format
        if issues_result is not None:
            # Display value should contain the bug icon
            assert "🐛" in issues_result.display_value

            # Should have a numeric count
            number_part = issues_result.display_value.split()[0]
            assert number_part.isdigit()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_issues_additional_info_contains_url(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Issues additional info contains the issues page URL."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the issues result
        issues_result = next(
            (r for r in results if r.key[1] == "issues" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify additional info
        if issues_result is not None:
            assert isinstance(issues_result.additional_info, str)
            assert "/issues" in issues_result.additional_info
            assert "github.com/davidbrownell/AllGitStatus" in issues_result.additional_info

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_issues_additional_info_contains_total_count(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Issues additional info contains total count."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the issues result
        issues_result = next(
            (r for r in results if r.key[1] == "issues" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify total count
        if issues_result is not None:
            assert isinstance(issues_result.additional_info, str)
            assert "Total Open Issues:" in issues_result.additional_info


# ----------------------------------------------------------------------
class TestGitHubSourcePullRequests:
    """Integration tests for GitHubSource pull requests functionality."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_requests_result_has_correct_key(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Pull requests result has the correct key structure."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the pull_requests result
        pr_result = next((r for r in results if r.key[1] == "pull_requests"), None)

        assert pr_result is not None
        assert pr_result.key == ("GitHubSource", "pull_requests")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_requests_display_value_format(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Pull requests display value contains a count and the PR icon."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the pull_requests result
        pr_result = next(
            (r for r in results if r.key[1] == "pull_requests" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify the format
        if pr_result is not None:
            # Display value should contain the PR icon
            assert "🔀" in pr_result.display_value

            # Should have a numeric count
            number_part = pr_result.display_value.split()[0]
            assert number_part.isdigit()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_requests_additional_info_contains_url(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Pull requests additional info contains the pulls page URL."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the pull_requests result
        pr_result = next(
            (r for r in results if r.key[1] == "pull_requests" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify additional info
        if pr_result is not None:
            assert isinstance(pr_result.additional_info, str)
            assert "/pulls" in pr_result.additional_info
            assert "github.com/davidbrownell/AllGitStatus" in pr_result.additional_info

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_requests_additional_info_contains_total_count(
        self, session: aiohttp.ClientSession, allgitstatus_repo: Repository
    ) -> None:
        """Pull requests additional info contains total count."""

        source = GitHubSource(session)

        results = [info async for info in source.Query(allgitstatus_repo)]

        # Find the pull_requests result
        pr_result = next(
            (r for r in results if r.key[1] == "pull_requests" and isinstance(r, ResultInfo)),
            None,
        )

        # If we got a ResultInfo (not ErrorInfo), verify total count
        if pr_result is not None:
            assert isinstance(pr_result.additional_info, str)
            assert "Total Open PRs:" in pr_result.additional_info

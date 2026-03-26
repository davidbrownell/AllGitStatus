"""Unit tests for AllGitStatus.Sources.GitHubSource module with mocked API responses."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from typing import cast

import pytest

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.GitHubSource import GitHubSource
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo


# ----------------------------------------------------------------------
@pytest.fixture
def github_repo() -> Repository:
    """Create a Repository object with GitHub info."""

    return Repository(
        path=Path("/test/repo"),
        remote_url="https://github.com/owner/repo.git",
        github_owner="owner",
        github_repo="repo",
    )


# ----------------------------------------------------------------------
def create_mock_response(json_data: object, status: int = 200) -> MagicMock:
    """Create a mock aiohttp response."""

    response = MagicMock()
    response.json = AsyncMock(return_value=json_data)
    response.raise_for_status = MagicMock()

    if status >= 400:
        from aiohttp import ClientResponseError

        response.raise_for_status.side_effect = ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=status,
            message="Error",
        )

    return response


# ----------------------------------------------------------------------
def create_mock_session(responses: list[MagicMock]) -> MagicMock:
    """Create a mock aiohttp session that returns responses in order."""

    session = MagicMock()
    response_iter = iter(responses)

    def get_context_manager(*args, **kwargs):  # noqa: ARG001
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=next(response_iter))
        cm.__aexit__ = AsyncMock(return_value=None)
        return cm

    session.get = get_context_manager

    return session


# ----------------------------------------------------------------------
class TestCreateGitHubHttpHeaders:
    """Tests for GitHubSource.CreateGitHubHttpHeaders method."""

    # ----------------------------------------------------------------------
    def test_headers_without_pat(self) -> None:
        """Headers are created without authorization when no PAT provided."""

        headers = GitHubSource.CreateGitHubHttpHeaders()

        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert "Authorization" not in headers

    # ----------------------------------------------------------------------
    def test_headers_with_pat(self) -> None:
        """Headers include authorization when PAT provided."""

        headers = GitHubSource.CreateGitHubHttpHeaders("test-token")

        assert headers["Accept"] == "application/vnd.github+json"
        assert headers["X-GitHub-Api-Version"] == "2022-11-28"
        assert headers["Authorization"] == "Bearer test-token"

    # ----------------------------------------------------------------------
    def test_headers_with_none_pat(self) -> None:
        """Headers don't include authorization when PAT is None."""

        headers = GitHubSource.CreateGitHubHttpHeaders(None)

        assert "Authorization" not in headers


# ----------------------------------------------------------------------
class TestRepositoryInfo:
    """Tests for repository info (stars, forks, issues, watchers)."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_stars_result_has_correct_key_and_format(self, github_repo: Repository) -> None:
        """Stars result has the correct key and display format."""

        responses = [
            create_mock_response(
                {"stargazers_count": 42, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        stars_result = next(r for r in results if r.key[1] == "stars")

        assert isinstance(stars_result, ResultInfo)
        assert stars_result.key == ("GitHubSource", "stars")
        assert "42" in stars_result.display_value
        assert "⭐" in stars_result.display_value
        assert stars_result.additional_info == "https://github.com/owner/repo/stargazers"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_forks_result_has_correct_key_and_format(self, github_repo: Repository) -> None:
        """Forks result has the correct key and display format."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 15, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        forks_result = next(r for r in results if r.key[1] == "forks")

        assert isinstance(forks_result, ResultInfo)
        assert forks_result.key == ("GitHubSource", "forks")
        assert "15" in forks_result.display_value
        assert "🍴" in forks_result.display_value
        assert forks_result.additional_info == "https://github.com/owner/repo/forks"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_issues_result_has_correct_key_and_format(self, github_repo: Repository) -> None:
        """Issues result has the correct key and display format."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 7, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        issues_result = next(r for r in results if r.key[1] == "issues")

        assert isinstance(issues_result, ResultInfo)
        assert issues_result.key == ("GitHubSource", "issues")
        assert "7" in issues_result.display_value
        assert "🐛" in issues_result.display_value
        assert issues_result.additional_info == "https://github.com/owner/repo/issues"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_watchers_result_has_correct_key_and_format(self, github_repo: Repository) -> None:
        """Watchers result has the correct key and display format."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 25}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        watchers_result = next(r for r in results if r.key[1] == "watchers")

        assert isinstance(watchers_result, ResultInfo)
        assert watchers_result.key == ("GitHubSource", "watchers")
        assert "25" in watchers_result.display_value
        assert "👀" in watchers_result.display_value
        assert watchers_result.additional_info == "https://github.com/owner/repo/watchers"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_zero_counts_displayed_correctly(self, github_repo: Repository) -> None:
        """Zero counts are displayed correctly for all metrics."""

        responses = [
            create_mock_response(
                {"stargazers_count": 0, "forks_count": 0, "open_issues_count": 0, "subscribers_count": 0}
            ),
            create_mock_response({"total_count": 0}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        for key in ["stars", "forks", "issues", "watchers"]:
            result = next(r for r in results if r.key[1] == key)
            assert isinstance(result, ResultInfo)
            assert "0" in result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_missing_counts_default_to_zero(self, github_repo: Repository) -> None:
        """Missing count fields default to zero."""

        responses = [
            create_mock_response({}),  # Empty response - all fields missing
            create_mock_response({"total_count": 0}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        for key in ["stars", "forks", "issues", "watchers"]:
            result = next(r for r in results if r.key[1] == key)
            assert isinstance(result, ResultInfo)
            assert "0" in result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_large_counts_formatted_correctly(self, github_repo: Repository) -> None:
        """Large counts are formatted with proper width."""

        responses = [
            create_mock_response(
                {
                    "stargazers_count": 12345,
                    "forks_count": 9999,
                    "open_issues_count": 500,
                    "subscribers_count": 1000,
                }
            ),
            create_mock_response({"total_count": 50}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        stars_result = next(r for r in results if r.key[1] == "stars")
        assert "12345" in stars_result.display_value

        forks_result = next(r for r in results if r.key[1] == "forks")
        assert "9999" in forks_result.display_value

        issues_result = next(r for r in results if r.key[1] == "issues")
        assert "500" in issues_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_url_strips_git_suffix(self, github_repo: Repository) -> None:
        """Additional info URLs have .git suffix stripped."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        for result in results:
            if isinstance(result, ResultInfo) and isinstance(result.additional_info, str):
                if result.additional_info.startswith("http"):
                    assert not result.additional_info.endswith(".git")


# ----------------------------------------------------------------------
class TestPullRequests:
    """Tests for pull requests functionality."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_requests_result_has_correct_key_and_format(self, github_repo: Repository) -> None:
        """Pull requests result has the correct key and display format."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 8}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        pr_result = next(r for r in results if r.key[1] == "pull_requests")

        assert isinstance(pr_result, ResultInfo)
        assert pr_result.key == ("GitHubSource", "pull_requests")
        assert "8" in pr_result.display_value
        assert "🔀" in pr_result.display_value
        assert pr_result.additional_info == "https://github.com/owner/repo/pulls"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_requests_zero_count(self, github_repo: Repository) -> None:
        """Pull requests with zero count displays correctly."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 0}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        pr_result = next(r for r in results if r.key[1] == "pull_requests")

        assert isinstance(pr_result, ResultInfo)
        assert "0" in pr_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_requests_missing_total_count_defaults_to_zero(self, github_repo: Repository) -> None:
        """Missing total_count in PR response defaults to zero."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({}),  # Missing total_count
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        pr_result = next(r for r in results if r.key[1] == "pull_requests")

        assert isinstance(pr_result, ResultInfo)
        assert "0" in pr_result.display_value


# ----------------------------------------------------------------------
class TestRepoApiErrorHandling:
    """Tests for repository API error handling."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_repo_api_error_returns_error_info_for_stars(self, github_repo: Repository) -> None:
        """Repository API error returns ErrorInfo with stars key."""

        responses = [
            create_mock_response({}, status=404),  # Repo not found
            create_mock_response({"total_count": 0}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        # First result should be ErrorInfo for stars
        stars_result = results[0]
        assert isinstance(stars_result, ErrorInfo)
        assert stars_result.key == ("GitHubSource", "stars")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_repo_api_error_does_not_yield_forks_issues_watchers(self, github_repo: Repository) -> None:
        """Repository API error means forks, issues, watchers are not yielded."""

        responses = [
            create_mock_response({}, status=404),  # Repo not found
            create_mock_response({"total_count": 0}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        result_keys = [r.key[1] for r in results]

        # When repo API fails, we only get ErrorInfo for stars, then PRs and security_alerts still run
        assert "stars" in result_keys
        assert "forks" not in result_keys
        assert "issues" not in result_keys
        assert "watchers" not in result_keys
        assert "pull_requests" in result_keys
        assert "security_alerts" in result_keys

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pr_api_error_returns_error_info(self, github_repo: Repository) -> None:
        """PR search API error returns ErrorInfo."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({}, status=403),  # Rate limited or forbidden
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        pr_result = next(r for r in results if r.key[1] == "pull_requests")

        assert isinstance(pr_result, ErrorInfo)
        assert pr_result.key == ("GitHubSource", "pull_requests")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pr_error_does_not_affect_other_results(self, github_repo: Repository) -> None:
        """PR API error does not affect stars, forks, issues, watchers results."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({}, status=500),  # Server error
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        # Stars, forks, issues, watchers should all be ResultInfo
        for key in ["stars", "forks", "issues", "watchers"]:
            result = next(r for r in results if r.key[1] == key)
            assert isinstance(result, ResultInfo)


# ----------------------------------------------------------------------
class TestSecurityAlertsNoAlerts:
    """Tests for security alerts when repository has no alerts."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_no_alerts_shows_lock_icon(self, github_repo: Repository) -> None:
        """Display shows lock icon when no security alerts exist."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),  # Empty alerts array
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "🔒" in security_result.display_value
        assert "0" in security_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_no_alerts_severity_counts_are_zero(self, github_repo: Repository) -> None:
        """Additional info shows all severity counts as zero."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "Critical: 0" in cast(str, security_result.additional_info)
        assert "High:     0" in cast(str, security_result.additional_info)
        assert "Medium:   0" in cast(str, security_result.additional_info)
        assert "Low:      0" in cast(str, security_result.additional_info)


# ----------------------------------------------------------------------
class TestSecurityAlertsCriticalSeverity:
    """Tests for security alerts with critical severity."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_critical_alerts_show_siren_icon(self, github_repo: Repository) -> None:
        """Display shows siren icon when critical alerts exist."""

        alerts = [
            {
                "security_advisory": {"severity": "critical", "summary": "Critical vulnerability"},
                "security_vulnerability": {"package": {"name": "package-a"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "🚨" in security_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_critical_takes_precedence_over_high(self, github_repo: Repository) -> None:
        """Siren icon is shown when both critical and high alerts exist."""

        alerts = [
            {
                "security_advisory": {"severity": "critical", "summary": "Critical issue"},
                "security_vulnerability": {"package": {"name": "pkg-critical"}},
            },
            {
                "security_advisory": {"severity": "high", "summary": "High issue"},
                "security_vulnerability": {"package": {"name": "pkg-high"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "🚨" in security_result.display_value
        assert "2" in security_result.display_value


# ----------------------------------------------------------------------
class TestSecurityAlertsHighSeverity:
    """Tests for security alerts with high severity (no critical)."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_high_alerts_show_warning_icon(self, github_repo: Repository) -> None:
        """Display shows warning icon when high alerts exist (no critical)."""

        alerts = [
            {
                "security_advisory": {"severity": "high", "summary": "High vulnerability"},
                "security_vulnerability": {"package": {"name": "package-b"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "⚠️" in security_result.display_value


# ----------------------------------------------------------------------
class TestSecurityAlertsMediumLowSeverity:
    """Tests for security alerts with medium/low severity only."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_medium_alerts_show_bell_icon(self, github_repo: Repository) -> None:
        """Display shows bell icon when only medium alerts exist."""

        alerts = [
            {
                "security_advisory": {"severity": "medium", "summary": "Medium vulnerability"},
                "security_vulnerability": {"package": {"name": "package-c"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "🔔" in security_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_low_alerts_show_bell_icon(self, github_repo: Repository) -> None:
        """Display shows bell icon when only low alerts exist."""

        alerts = [
            {
                "security_advisory": {"severity": "low", "summary": "Low vulnerability"},
                "security_vulnerability": {"package": {"name": "package-d"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "🔔" in security_result.display_value


# ----------------------------------------------------------------------
class TestSecurityAlertsSeverityCounting:
    """Tests for correct severity counting in security alerts."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_multiple_alerts_counted_correctly(self, github_repo: Repository) -> None:
        """Multiple alerts are counted and categorized correctly."""

        alerts = [
            {
                "security_advisory": {"severity": "critical", "summary": "Critical 1"},
                "security_vulnerability": {"package": {"name": "pkg1"}},
            },
            {
                "security_advisory": {"severity": "critical", "summary": "Critical 2"},
                "security_vulnerability": {"package": {"name": "pkg2"}},
            },
            {
                "security_advisory": {"severity": "high", "summary": "High 1"},
                "security_vulnerability": {"package": {"name": "pkg3"}},
            },
            {
                "security_advisory": {"severity": "medium", "summary": "Medium 1"},
                "security_vulnerability": {"package": {"name": "pkg4"}},
            },
            {
                "security_advisory": {"severity": "low", "summary": "Low 1"},
                "security_vulnerability": {"package": {"name": "pkg5"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "5" in security_result.display_value
        assert "Critical: 2" in cast(str, security_result.additional_info)
        assert "High:     1" in cast(str, security_result.additional_info)
        assert "Medium:   1" in cast(str, security_result.additional_info)
        assert "Low:      1" in cast(str, security_result.additional_info)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_unknown_severity_not_counted(self, github_repo: Repository) -> None:
        """Alerts with unknown severity are included in total but not severity breakdown."""

        alerts = [
            {
                "security_advisory": {"severity": "unknown", "summary": "Unknown severity"},
                "security_vulnerability": {"package": {"name": "pkg1"}},
            },
            {
                "security_advisory": {"summary": "Missing severity"},
                "security_vulnerability": {"package": {"name": "pkg2"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        # Total should be 2 (includes unknown severities)
        assert "2" in security_result.display_value
        # But known severity counts should all be 0
        assert "Critical: 0" in cast(str, security_result.additional_info)
        assert "High:     0" in cast(str, security_result.additional_info)
        assert "Medium:   0" in cast(str, security_result.additional_info)
        assert "Low:      0" in cast(str, security_result.additional_info)


# ----------------------------------------------------------------------
class TestSecurityAlertsAdditionalInfo:
    """Tests for security alerts additional info content."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_additional_info_contains_security_url(self, github_repo: Repository) -> None:
        """Additional info contains the security page URL."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "https://github.com/owner/repo/security/dependabot" in cast(
            str, security_result.additional_info
        )

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_additional_info_shows_alerts(self, github_repo: Repository) -> None:
        """Additional info shows alerts with package names and summaries."""

        alerts = [
            {
                "security_advisory": {"severity": "high", "summary": "SQL Injection vulnerability"},
                "security_vulnerability": {"package": {"name": "vulnerable-package"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "[HIGH]" in cast(str, security_result.additional_info)
        assert "vulnerable-package" in cast(str, security_result.additional_info)
        assert "SQL Injection vulnerability" in cast(str, security_result.additional_info)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_additional_info_shows_all_alerts(self, github_repo: Repository) -> None:
        """Additional info shows all alerts."""

        alerts = [
            {
                "security_advisory": {"severity": "medium", "summary": f"Alert {i}"},
                "security_vulnerability": {"package": {"name": f"pkg-{i}"}},
            }
            for i in range(8)
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        # Verify all alerts are shown
        for i in range(8):
            assert f"pkg-{i}" in cast(str, security_result.additional_info)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_no_recent_alerts_section_when_empty(self, github_repo: Repository) -> None:
        """No 'Recent Alerts' section when there are no alerts."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response([]),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "Recent Alerts:" not in cast(str, security_result.additional_info)


# ----------------------------------------------------------------------
class TestSecurityAlertsErrorHandling:
    """Tests for security alerts error handling."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_api_error_returns_error_info(self, github_repo: Repository) -> None:
        """API error returns ErrorInfo for security alerts."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response({}, status=403),  # Forbidden - no access to security alerts
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ErrorInfo)
        assert security_result.key == ("GitHubSource", "security_alerts")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_other_results_not_affected_by_security_error(self, github_repo: Repository) -> None:
        """Other results are returned even when security alerts API fails."""

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response({}, status=403),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        # Should have 6 results total
        assert len(results) == 6

        # Stars, forks, issues, watchers, PRs should all be ResultInfo
        non_security_results = [r for r in results if r.key[1] != "security_alerts"]
        assert len(non_security_results) == 5
        assert all(isinstance(r, ResultInfo) for r in non_security_results)


# ----------------------------------------------------------------------
class TestSecurityAlertsMissingFields:
    """Tests for handling alerts with missing fields."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_missing_package_name_shows_unknown(self, github_repo: Repository) -> None:
        """Missing package name shows 'unknown' in output."""

        alerts = [
            {
                "security_advisory": {"severity": "high", "summary": "Some issue"},
                "security_vulnerability": {},  # No package info
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "unknown:" in cast(str, security_result.additional_info)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_missing_summary_shows_no_summary(self, github_repo: Repository) -> None:
        """Missing summary shows 'No summary' in output."""

        alerts = [
            {
                "security_advisory": {"severity": "high"},  # No summary
                "security_vulnerability": {"package": {"name": "some-pkg"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "No summary" in cast(str, security_result.additional_info)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_missing_severity_shows_unknown(self, github_repo: Repository) -> None:
        """Missing severity shows 'UNKNOWN' in output."""

        alerts = [
            {
                "security_advisory": {"summary": "Some issue"},  # No severity
                "security_vulnerability": {"package": {"name": "some-pkg"}},
            },
        ]

        responses = [
            create_mock_response(
                {"stargazers_count": 10, "forks_count": 5, "open_issues_count": 2, "subscribers_count": 3}
            ),
            create_mock_response({"total_count": 1}),
            create_mock_response(alerts),
        ]
        session = create_mock_session(responses)
        source = GitHubSource(session)

        results = [info async for info in source.Query(github_repo)]

        security_result = next(r for r in results if r.key[1] == "security_alerts")

        assert isinstance(security_result, ResultInfo)
        assert "[UNKNOWN]" in cast(str, security_result.additional_info)

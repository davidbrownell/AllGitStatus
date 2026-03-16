"""Integration tests for AllGitStatus.Sources.GitHubSource module.

These tests make real API calls to GitHub using the davidbrownell/AllGitStatus repository.
"""

from pathlib import Path

import pytest

from AllGitStatus.Auth import CreateAuthenticatedSession
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
class TestGitHubSourceApplies:
    """Tests for GitHubSource.Applies method."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_applies_to_github_repo(self, allgitstatus_repo: Repository) -> None:
        """Source applies to repositories with GitHub owner and repo."""

        async with CreateAuthenticatedSession() as session:
            source = GitHubSource(session)

            assert source.Applies(allgitstatus_repo) is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_does_not_apply_to_non_github_repo(self, non_github_repo: Repository) -> None:
        """Source does not apply to repositories without GitHub info."""

        async with CreateAuthenticatedSession() as session:
            source = GitHubSource(session)

            assert source.Applies(non_github_repo) is False

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_does_not_apply_when_owner_missing(self) -> None:
        """Source does not apply when github_owner is None."""

        repo = Repository(
            path=Path("/test"),
            remote_url="https://github.com/owner/repo.git",
            github_owner=None,
            github_repo="repo",
        )

        async with CreateAuthenticatedSession() as session:
            source = GitHubSource(session)

            assert source.Applies(repo) is False

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_does_not_apply_when_repo_missing(self) -> None:
        """Source does not apply when github_repo is None."""

        repo = Repository(
            path=Path("/test"),
            remote_url="https://github.com/owner/repo.git",
            github_owner="owner",
            github_repo=None,
        )

        async with CreateAuthenticatedSession() as session:
            source = GitHubSource(session)

            assert source.Applies(repo) is False


# ----------------------------------------------------------------------
class TestGitHubSourceQuery:
    """Integration tests for GitHubSource.Query method using real GitHub API."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_query_returns_valid_results(self, allgitstatus_repo: Repository) -> None:
        """Query returns four ResultInfo items with correct structure and content."""

        async with CreateAuthenticatedSession() as session:
            source = GitHubSource(session)

            results = [info async for info in source.Query(allgitstatus_repo)]

        # Verify we get exactly 4 ResultInfo items
        assert len(results) == 4
        assert all(isinstance(r, ResultInfo) for r in results)

        # All results should reference the same repo
        for result in results:
            assert result.repo is allgitstatus_repo

        # Build a dict for easier lookup
        results_by_key = {r.key[1]: r for r in results}

        # Verify stars info
        stars = results_by_key["stars"]
        assert stars.key == ("GitHubSource", "stars")
        assert "⭐" in stars.display_value
        assert stars.additional_info == "https://github.com/davidbrownell/AllGitStatus/stargazers"

        # Verify forks info
        forks = results_by_key["forks"]
        assert forks.key == ("GitHubSource", "forks")
        assert "🍴" in forks.display_value
        assert forks.additional_info == "https://github.com/davidbrownell/AllGitStatus/forks"

        # Verify issues info
        issues = results_by_key["issues"]
        assert issues.key == ("GitHubSource", "issues")
        assert "🐛" in issues.display_value
        assert issues.additional_info == "https://github.com/davidbrownell/AllGitStatus/issues"

        # Verify watchers info
        watchers = results_by_key["watchers"]
        assert watchers.key == ("GitHubSource", "watchers")
        assert "👀" in watchers.display_value
        assert watchers.additional_info == "https://github.com/davidbrownell/AllGitStatus/watchers"

        # Verify all display values contain numeric counts
        for result in results:
            number_part = result.display_value.split()[0]
            assert number_part.isdigit(), f"Expected number in '{result.display_value}'"

        # Verify URLs don't have .git suffix
        for result in results:
            assert isinstance(result.additional_info, str)
            assert not result.additional_info.endswith(".git")
            assert "github.com/davidbrownell/AllGitStatus/" in result.additional_info

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_query_nonexistent_repo_returns_error(self) -> None:
        """Query returns ErrorInfo for non-existent repository."""

        repo = Repository(
            path=Path("/test"),
            remote_url="https://github.com/nonexistent-user-12345/nonexistent-repo-67890.git",
            github_owner="nonexistent-user-12345",
            github_repo="nonexistent-repo-67890",
        )

        async with CreateAuthenticatedSession() as session:
            source = GitHubSource(session)

            results = [info async for info in source.Query(repo)]

        assert len(results) == 1
        assert isinstance(results[0], ErrorInfo)
        assert results[0].key == ("GitHubSource", "stars")

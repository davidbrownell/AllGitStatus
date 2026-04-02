"""Unit tests for AllGitStatus.Repository module."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from AllGitStatus.Repository import EnumerateRepositories, Repository


# ----------------------------------------------------------------------
class TestRepository:
    """Tests for the Repository dataclass."""

    # ----------------------------------------------------------------------
    def test_default_values(self) -> None:
        """Repository is created with correct default values."""

        repo = Repository(path=Path("/test/path"))

        assert repo.path == Path("/test/path")
        assert repo.remote_url is None
        assert repo.github_owner is None
        assert repo.github_repo is None

    # ----------------------------------------------------------------------
    def test_all_fields_provided(self) -> None:
        """Repository is created with all fields provided."""

        repo = Repository(
            path=Path("/test/path"),
            remote_url="https://github.com/owner/repo.git",
            github_owner="owner",
            github_repo="repo",
        )

        assert repo.path == Path("/test/path")
        assert repo.remote_url == "https://github.com/owner/repo.git"
        assert repo.github_owner == "owner"
        assert repo.github_repo == "repo"

    # ----------------------------------------------------------------------
    def test_frozen_dataclass(self) -> None:
        """Repository dataclass is immutable (frozen)."""

        repo = Repository(path=Path("/test/path"))

        with pytest.raises(AttributeError):
            repo.path = Path("/another/path")  # ty: ignore[invalid-assignment]

        with pytest.raises(AttributeError):
            repo.remote_url = "https://example.com"  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
class TestFromDirectory:
    """Tests for the Repository.FromDirectory async classmethod."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_successful_https_url_with_git_suffix(self) -> None:
        """Repository is created from HTTPS URL ending with .git."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"https://github.com/myowner/myrepo.git\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.path == Path("/test/repo")
            assert repo.remote_url == "https://github.com/myowner/myrepo.git"
            assert repo.github_owner == "myowner"
            assert repo.github_repo == "myrepo"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_successful_https_url_without_git_suffix(self) -> None:
        """Repository is created from HTTPS URL without .git suffix."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"https://github.com/owner/repo\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.remote_url == "https://github.com/owner/repo"
            assert repo.github_owner == "owner"
            assert repo.github_repo == "repo"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_successful_ssh_url(self) -> None:
        """Repository is created from SSH URL format."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"git@github.com:owner/repo.git\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.remote_url == "git@github.com:owner/repo.git"
            assert repo.github_owner == "owner"
            assert repo.github_repo == "repo"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_successful_ssh_url_without_git_suffix(self) -> None:
        """Repository is created from SSH URL without .git suffix."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"git@github.com:myuser/myproject\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.remote_url == "git@github.com:myuser/myproject"
            assert repo.github_owner == "myuser"
            assert repo.github_repo == "myproject"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_https_url_with_trailing_slash(self) -> None:
        """Repository is created from HTTPS URL with trailing slash."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"https://github.com/owner/repo/\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.remote_url == "https://github.com/owner/repo/"
            assert repo.github_owner == "owner"
            assert repo.github_repo == "repo"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_git_command_fails_with_nonzero_exit(self) -> None:
        """Repository is created without remote info when git command fails."""

        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"error: No such remote 'origin'\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.path == Path("/test/repo")
            assert repo.remote_url is None
            assert repo.github_owner is None
            assert repo.github_repo is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_git_command_raises_exception(self) -> None:
        """Repository is created without remote info when git command raises exception."""

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = FileNotFoundError("git not found")

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.path == Path("/test/repo")
            assert repo.remote_url is None
            assert repo.github_owner is None
            assert repo.github_repo is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_non_github_remote_url(self) -> None:
        """Repository is created with remote URL but no GitHub info for non-GitHub remotes."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"https://gitlab.com/owner/repo.git\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.remote_url == "https://gitlab.com/owner/repo.git"
            assert repo.github_owner is None
            assert repo.github_repo is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_git_command_called_with_correct_arguments(self) -> None:
        """Git command is called with correct arguments."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"https://github.com/o/r.git\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            test_path = Path("/my/test/repo")
            await Repository.FromDirectory(test_path)

            mock_exec.assert_called_once()
            call_args = mock_exec.call_args

            # Verify positional arguments
            assert call_args[0] == ("git", "-C", str(test_path), "remote", "get-url", "origin")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_whitespace_stripped_from_output(self) -> None:
        """Whitespace is stripped from git command output."""

        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"  https://github.com/owner/repo.git  \n\n", None))

        with patch("AllGitStatus.Repository.asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.return_value = mock_proc

            repo = await Repository.FromDirectory(Path("/test/repo"))

            assert repo.remote_url == "https://github.com/owner/repo.git"


# ----------------------------------------------------------------------
class TestEnumerateRepositories:
    """Tests for the EnumerateRepositories async generator function."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_non_directory_path(self) -> None:
        """No repositories yielded when path is not a directory."""

        with patch.object(Path, "is_dir", return_value=False):
            repos = [repo async for repo in EnumerateRepositories(Path("/nonexistent"))]

            assert repos == []

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_directory_with_no_repos(self) -> None:
        """No repositories yielded when directory contains no git repos."""

        def mock_walk(path):
            yield (str(path), ["subdir1", "subdir2"], ["file.txt"])
            yield (str(path / "subdir1"), [], ["other.txt"])
            yield (str(path / "subdir2"), [], [])

        with (
            patch.object(Path, "is_dir", return_value=True),
            patch("AllGitStatus.Repository.os.walk", side_effect=mock_walk),
        ):
            repos = [repo async for repo in EnumerateRepositories(Path("/test/root"))]

            assert repos == []

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_single_repository_found(self) -> None:
        """Single repository is found and yielded."""

        directories = [".git", "src"]

        def mock_walk(path):
            yield (str(path), directories, ["README.md"])

        mock_repo = Repository(path=Path("/test/root"))

        with (
            patch.object(Path, "is_dir", return_value=True),
            patch("AllGitStatus.Repository.os.walk", side_effect=mock_walk),
            patch.object(Repository, "FromDirectory", new_callable=AsyncMock, return_value=mock_repo),
        ):
            repos = [repo async for repo in EnumerateRepositories(Path("/test/root"))]

            assert len(repos) == 1
            assert repos[0] is mock_repo

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_directories_cleared_after_finding_repo(self) -> None:
        """Directories list is cleared after finding a git repo to prevent further traversal."""

        # This list will be modified by the code under test
        root_dirs: list[str] = [".git", "subproject", "another_dir"]

        def mock_walk(path):
            yield (str(path), root_dirs, ["README.md"])

        mock_repo = Repository(path=Path("/test/root"))

        with (
            patch.object(Path, "is_dir", return_value=True),
            patch("AllGitStatus.Repository.os.walk", side_effect=mock_walk),
            patch.object(Repository, "FromDirectory", new_callable=AsyncMock, return_value=mock_repo),
        ):
            repos = [repo async for repo in EnumerateRepositories(Path("/test/root"))]

            assert len(repos) == 1
            # Verify directories list was cleared to prevent os.walk from descending
            assert root_dirs == []

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_multiple_sibling_repos(self) -> None:
        """Multiple sibling repositories are all found."""

        repo1_dirs: list[str] = [".git"]
        repo2_dirs: list[str] = [".git"]

        def mock_walk(path):
            yield (str(path), ["repo1", "repo2"], [])
            yield (str(path / "repo1"), repo1_dirs, ["file1.txt"])
            yield (str(path / "repo2"), repo2_dirs, ["file2.txt"])

        call_count = 0

        async def mock_from_directory(path: Path) -> Repository:
            nonlocal call_count
            call_count += 1
            return Repository(path=path)

        with (
            patch.object(Path, "is_dir", return_value=True),
            patch("AllGitStatus.Repository.os.walk", side_effect=mock_walk),
            patch.object(Repository, "FromDirectory", side_effect=mock_from_directory),
        ):
            repos = [repo async for repo in EnumerateRepositories(Path("/test/root"))]

            assert len(repos) == 2
            assert call_count == 2

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_from_directory_called_with_correct_path(self) -> None:
        """FromDirectory is called with the correct repository path."""

        directories = [".git"]

        def mock_walk(path):
            yield ("/test/root/myrepo", directories, ["README.md"])

        mock_repo = Repository(path=Path("/test/root/myrepo"))

        with (
            patch.object(Path, "is_dir", return_value=True),
            patch("AllGitStatus.Repository.os.walk", side_effect=mock_walk),
            patch.object(
                Repository, "FromDirectory", new_callable=AsyncMock, return_value=mock_repo
            ) as mock_from_dir,
        ):
            repos = [repo async for repo in EnumerateRepositories(Path("/test/root"))]

            assert len(repos) == 1
            mock_from_dir.assert_called_once_with(Path("/test/root/myrepo"))

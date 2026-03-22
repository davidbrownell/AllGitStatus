"""Integration tests for AllGitStatus.Sources.LocalGitSource module.

These tests create real git repositories in temporary directories to exercise each scenario.
"""

import asyncio
import subprocess
from pathlib import Path

import pytest

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.LocalGitSource import LocalGitSource
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo


# ----------------------------------------------------------------------
# |  Helper Functions
# ----------------------------------------------------------------------
def run_git(repo_path: Path, *args: str) -> str:
    """Run a git command in the specified repository."""

    result = subprocess.run(
        ["git", "-C", str(repo_path), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def init_repo(repo_path: Path) -> None:
    """Initialize a git repository with initial commit."""

    repo_path.mkdir(parents=True, exist_ok=True)
    run_git(repo_path, "init")
    run_git(repo_path, "config", "user.email", "test@test.com")
    run_git(repo_path, "config", "user.name", "Test User")
    # Disable autocrlf to ensure consistent behavior across platforms
    run_git(repo_path, "config", "core.autocrlf", "false")

    # Create initial commit
    (repo_path / "README.md").write_bytes(b"# Test Repo\n")
    run_git(repo_path, "add", "README.md")
    run_git(repo_path, "commit", "-m", "Initial commit")


# ----------------------------------------------------------------------
# |  Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def repo_path(tmp_path: Path) -> Path:
    """Create and return a path for a test repository."""

    path = tmp_path / "test_repo"
    init_repo(path)
    return path


@pytest.fixture
def repo(repo_path: Path) -> Repository:
    """Create a Repository object for the test repository."""

    return Repository(path=repo_path)


# ----------------------------------------------------------------------
class TestLocalGitSourceCurrentBranch:
    """Tests for current branch detection."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_detects_main_branch(self, repo_path: Path, repo: Repository) -> None:
        """Detects the current branch name (main or master)."""

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        branch_result = next(r for r in results if r.key[1] == "current_branch")
        assert isinstance(branch_result, ResultInfo)
        # Git may use 'main' or 'master' depending on configuration
        assert branch_result.display_value in ["main", "master"]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_detects_feature_branch(self, repo_path: Path, repo: Repository) -> None:
        """Detects a feature branch name."""

        run_git(repo_path, "checkout", "-b", "feature/test-branch")

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        branch_result = next(r for r in results if r.key[1] == "current_branch")
        assert isinstance(branch_result, ResultInfo)
        assert branch_result.display_value == "feature/test-branch"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_detects_detached_head(self, repo_path: Path, repo: Repository) -> None:
        """Detects detached HEAD state."""

        # Get the commit hash and checkout to detached HEAD
        commit_hash = run_git(repo_path, "rev-parse", "HEAD")
        run_git(repo_path, "checkout", commit_hash)

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        branch_result = next(r for r in results if r.key[1] == "current_branch")
        assert isinstance(branch_result, ResultInfo)
        assert "HEAD detached" in branch_result.display_value
        assert branch_result.additional_info == "<Detached HEAD state>"


# ----------------------------------------------------------------------
class TestLocalGitSourceLocalStatus:
    """Tests for local status detection (staged, unstaged, untracked)."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_clean_working_directory(self, repo_path: Path, repo: Repository) -> None:
        """Reports zeros for clean working directory."""

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        status_result = next(r for r in results if r.key[1] == "local_status")
        assert isinstance(status_result, ResultInfo)
        assert "  0 ✅" in status_result.display_value
        assert "  0 🟡" in status_result.display_value
        assert "  0 ❓" in status_result.display_value
        assert status_result.additional_info == "<No local changes>"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_untracked_files(self, repo_path: Path, repo: Repository) -> None:
        """Counts untracked files."""

        (repo_path / "untracked1.txt").write_bytes(b"untracked content")
        (repo_path / "untracked2.txt").write_bytes(b"more untracked")

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        status_result = next(r for r in results if r.key[1] == "local_status")
        assert isinstance(status_result, ResultInfo)
        assert "  2 ❓" in status_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_staged_files(self, repo_path: Path, repo: Repository) -> None:
        """Counts staged files."""

        (repo_path / "staged1.txt").write_bytes(b"staged content")
        (repo_path / "staged2.txt").write_bytes(b"more staged")
        (repo_path / "staged3.txt").write_bytes(b"even more staged")
        run_git(repo_path, "add", "staged1.txt", "staged2.txt", "staged3.txt")

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        status_result = next(r for r in results if r.key[1] == "local_status")
        assert isinstance(status_result, ResultInfo)
        assert "  3 ✅" in status_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_unstaged_modifications(self, repo_path: Path, repo: Repository) -> None:
        """Counts unstaged modifications to tracked files."""

        # Create a new file, stage and commit it
        (repo_path / "tracked.txt").write_bytes(b"original content")
        run_git(repo_path, "add", "tracked.txt")
        run_git(repo_path, "commit", "-m", "Add tracked file")

        # Now modify the committed file without staging
        (repo_path / "tracked.txt").write_bytes(b"modified content")

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        status_result = next(r for r in results if r.key[1] == "local_status")
        assert isinstance(status_result, ResultInfo)
        assert "  0 ✅" in status_result.display_value  # 0 staged
        assert "  1 🟡" in status_result.display_value  # 1 unstaged

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_mixed_status(self, repo_path: Path, repo: Repository) -> None:
        """Counts combination of staged, unstaged, and untracked."""

        # Create a file, stage and commit it (so we can have unstaged changes later)
        (repo_path / "existing.txt").write_bytes(b"original")
        run_git(repo_path, "add", "existing.txt")
        run_git(repo_path, "commit", "-m", "Add existing file")

        # Create and stage a new file
        (repo_path / "staged.txt").write_bytes(b"staged")
        run_git(repo_path, "add", "staged.txt")

        # Modify the committed file (unstaged)
        (repo_path / "existing.txt").write_bytes(b"modified")

        # Create untracked files
        (repo_path / "untracked1.txt").write_bytes(b"untracked")
        (repo_path / "untracked2.txt").write_bytes(b"untracked2")

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        status_result = next(r for r in results if r.key[1] == "local_status")
        assert isinstance(status_result, ResultInfo)
        assert "  1 ✅" in status_result.display_value  # 1 staged
        assert "  1 🟡" in status_result.display_value  # 1 unstaged
        assert "  2 ❓" in status_result.display_value  # 2 untracked


# ----------------------------------------------------------------------
class TestLocalGitSourceStashes:
    """Tests for stash counting."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_no_stashes(self, repo_path: Path, repo: Repository) -> None:
        """Reports zero stashes when none exist."""

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        stash_result = next(r for r in results if r.key[1] == "stashes")
        assert isinstance(stash_result, ResultInfo)
        assert "  0 🧺" in stash_result.display_value
        assert stash_result.additional_info == "<No stashes>"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_single_stash(self, repo_path: Path, repo: Repository) -> None:
        """Counts a single stash."""

        (repo_path / "README.md").write_bytes(b"Modified for stash\n")
        run_git(repo_path, "stash", "push", "-m", "Test stash")

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        stash_result = next(r for r in results if r.key[1] == "stashes")
        assert isinstance(stash_result, ResultInfo)
        assert "  1 🧺" in stash_result.display_value
        assert "Test stash" in stash_result.additional_info  # ty: ignore[unsupported-operator]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_multiple_stashes(self, repo_path: Path, repo: Repository) -> None:
        """Counts multiple stashes."""

        # Create first stash
        (repo_path / "README.md").write_bytes(b"First modification\n")
        run_git(repo_path, "stash", "push", "-m", "First stash")

        # Create second stash
        (repo_path / "README.md").write_bytes(b"Second modification\n")
        run_git(repo_path, "stash", "push", "-m", "Second stash")

        # Create third stash
        (repo_path / "README.md").write_bytes(b"Third modification\n")
        run_git(repo_path, "stash", "push", "-m", "Third stash")

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        stash_result = next(r for r in results if r.key[1] == "stashes")
        assert isinstance(stash_result, ResultInfo)
        assert "  3 🧺" in stash_result.display_value


# ----------------------------------------------------------------------
class TestLocalGitSourceRemoteStatus:
    """Tests for remote status detection."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_no_remote(self, repo_path: Path, repo: Repository) -> None:
        """Reports no changes when there's no remote."""

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        remote_result = next(r for r in results if r.key[1] == "remote_status")
        assert isinstance(remote_result, ResultInfo)
        assert "  0 🔼" in remote_result.display_value
        assert "  0 🔽" in remote_result.display_value
        assert remote_result.additional_info == "<No remote changes>"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_no_remote_in_detached_head(self, repo_path: Path, repo: Repository) -> None:
        """Reports no changes in detached HEAD state."""

        commit_hash = run_git(repo_path, "rev-parse", "HEAD")
        run_git(repo_path, "checkout", commit_hash)

        # Update repo object for detached head
        detached_repo = Repository(path=repo_path)

        source = LocalGitSource()
        results = [info async for info in source.Query(detached_repo)]

        remote_result = next(r for r in results if r.key[1] == "remote_status")
        assert isinstance(remote_result, ResultInfo)
        assert "  0 🔼" in remote_result.display_value
        assert "  0 🔽" in remote_result.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_local_commits_ahead_of_remote(self, tmp_path: Path) -> None:
        """Detects local commits that need to be pushed."""

        # Create a bare "remote" repository
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Create local repository and add remote
        local_path = tmp_path / "local"
        init_repo(local_path)
        run_git(local_path, "remote", "add", "origin", str(remote_path))

        # Push initial commit
        branch = run_git(local_path, "branch", "--show-current")
        run_git(local_path, "push", "-u", "origin", branch)

        # Create local commits not pushed
        (local_path / "file1.txt").write_bytes(b"content1")
        run_git(local_path, "add", "file1.txt")
        run_git(local_path, "commit", "-m", "Local commit 1")

        (local_path / "file2.txt").write_bytes(b"content2")
        run_git(local_path, "add", "file2.txt")
        run_git(local_path, "commit", "-m", "Local commit 2")

        repo = Repository(path=local_path)
        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        remote_result = next(r for r in results if r.key[1] == "remote_status")
        assert isinstance(remote_result, ResultInfo)
        assert "  2 🔼" in remote_result.display_value  # 2 commits to push
        assert "  0 🔽" in remote_result.display_value  # 0 commits to pull
        assert remote_result.state_data["has_local_changes"] is True  # ty: ignore[not-subscriptable]
        assert remote_result.state_data["has_remote_changes"] is False  # ty: ignore[not-subscriptable]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_remote_commits_to_pull(self, tmp_path: Path) -> None:
        """Detects remote commits that need to be pulled."""

        # Create a bare "remote" repository
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Create first local repository and push
        local1_path = tmp_path / "local1"
        init_repo(local1_path)
        run_git(local1_path, "remote", "add", "origin", str(remote_path))
        branch = run_git(local1_path, "branch", "--show-current")
        run_git(local1_path, "push", "-u", "origin", branch)

        # Clone to second local repository
        local2_path = tmp_path / "local2"
        subprocess.run(["git", "clone", str(remote_path), str(local2_path)], check=True)
        run_git(local2_path, "config", "user.email", "test@test.com")
        run_git(local2_path, "config", "user.name", "Test User")

        # Make commits in first repo and push
        (local1_path / "remote_file1.txt").write_bytes(b"remote content 1")
        run_git(local1_path, "add", "remote_file1.txt")
        run_git(local1_path, "commit", "-m", "Remote commit 1")
        run_git(local1_path, "push")

        # Query from second repo (should see commits to pull)
        repo = Repository(path=local2_path)
        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        remote_result = next(r for r in results if r.key[1] == "remote_status")
        assert isinstance(remote_result, ResultInfo)
        assert "  0 🔼" in remote_result.display_value  # 0 commits to push
        assert "  1 🔽" in remote_result.display_value  # 1 commit to pull
        assert remote_result.state_data["has_local_changes"] is False  # ty: ignore[not-subscriptable]
        assert remote_result.state_data["has_remote_changes"] is True  # ty: ignore[not-subscriptable]


# ----------------------------------------------------------------------
class TestLocalGitSourceQueryStructure:
    """Tests for overall Query structure and behavior."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_four_results(self, repo_path: Path, repo: Repository) -> None:
        """Query returns exactly four results."""

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        assert len(results) == 4
        keys = [r.key[1] for r in results]
        assert "current_branch" in keys
        assert "local_status" in keys
        assert "stashes" in keys
        assert "remote_status" in keys

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_all_results_reference_repo(self, repo_path: Path, repo: Repository) -> None:
        """All results reference the queried repository."""

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        for result in results:
            assert result.repo is repo

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_all_keys_have_correct_class_name(self, repo_path: Path, repo: Repository) -> None:
        """All result keys have LocalGitSource as the class name."""

        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        for result in results:
            assert result.key[0] == "LocalGitSource"


# ----------------------------------------------------------------------
class TestRawGitCommandErrorHandling:
    """Tests for _RawGitCommand error path."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_raises_runtime_error_on_git_failure(self, tmp_path: Path) -> None:
        """RuntimeError is raised when git command fails with raise_on_error=True."""

        # Create a directory that is NOT a git repository
        non_repo_path = tmp_path / "not_a_repo"
        non_repo_path.mkdir()

        # Attempting to run a git command in a non-repo should fail
        # Error format: "git \"status\""\n\n<git error output>\n
        with pytest.raises(
            RuntimeError,
            match=r'"git "status""\n\n.*(?:fatal|not a git repository).*',
        ):
            await LocalGitSource._RawGitCommand(non_repo_path, "status")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_error_code_when_raise_on_error_false(self, tmp_path: Path) -> None:
        """Returns non-zero exit code when raise_on_error=False."""

        # Create a directory that is NOT a git repository
        non_repo_path = tmp_path / "not_a_repo"
        non_repo_path.mkdir()

        # With raise_on_error=False, should return the error code instead of raising
        return_code, output = await LocalGitSource._RawGitCommand(
            non_repo_path, "status", raise_on_error=False
        )

        assert return_code != 0
        assert "fatal" in output.lower() or "not a git repository" in output.lower()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_successful_command_returns_zero(self, repo_path: Path) -> None:
        """Successful git command returns zero exit code."""

        return_code, output = await LocalGitSource._RawGitCommand(repo_path, "status", raise_on_error=False)

        assert return_code == 0

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_invalid_git_subcommand_raises_error(self, repo_path: Path) -> None:
        """Invalid git subcommand raises RuntimeError."""

        # Error format: "git \"not-a-real-command\""\n\n<git error output>\n
        with pytest.raises(
            RuntimeError,
            match=r'"git "not-a-real-command""\n\n.*not-a-real-command.*is not a git command.*',
        ):
            await LocalGitSource._RawGitCommand(repo_path, "not-a-real-command")


# ----------------------------------------------------------------------
class TestExecuteErrorHandling:
    """Tests for _Execute exception path."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_error_info_when_callback_raises_exception(self, repo: Repository) -> None:
        """Returns ErrorInfo when callback raises an exception."""

        test_exception = ValueError("Test exception message")

        async def failing_callback() -> LocalGitSource._InternalResultInfo:
            raise test_exception

        result = await LocalGitSource._Execute(
            repo,
            ("LocalGitSource", "test_key"),
            failing_callback,
        )

        assert isinstance(result, ErrorInfo)
        assert result.repo is repo
        assert result.key == ("LocalGitSource", "test_key")
        assert result.error is test_exception
        assert str(result.error) == "Test exception message"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_result_info_when_callback_succeeds(self, repo: Repository) -> None:
        """Returns ResultInfo when callback succeeds."""

        async def successful_callback() -> LocalGitSource._InternalResultInfo:
            return LocalGitSource._InternalResultInfo(
                display_value="test display",
                additional_info="test additional",
                state_data={"key": "value"},
            )

        result = await LocalGitSource._Execute(
            repo,
            ("LocalGitSource", "test_key"),
            successful_callback,
        )

        assert isinstance(result, ResultInfo)
        assert result.repo is repo
        assert result.key == ("LocalGitSource", "test_key")
        assert result.display_value == "test display"
        assert result.additional_info == "test additional"
        assert result.state_data == {"key": "value"}


# ----------------------------------------------------------------------
class TestLocalGitSourceDivergedState:
    """Tests for diverged state (both local and remote commits)."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_diverged_commits(self, tmp_path: Path) -> None:
        """Detects when local and remote have diverged (both ahead and behind)."""

        # Create a bare "remote" repository
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Create first local repository and push initial commit
        local1_path = tmp_path / "local1"
        init_repo(local1_path)
        run_git(local1_path, "remote", "add", "origin", str(remote_path))
        branch = run_git(local1_path, "branch", "--show-current")
        run_git(local1_path, "push", "-u", "origin", branch)

        # Clone to second local repository
        local2_path = tmp_path / "local2"
        subprocess.run(["git", "clone", str(remote_path), str(local2_path)], check=True)
        run_git(local2_path, "config", "user.email", "test@test.com")
        run_git(local2_path, "config", "user.name", "Test User")

        # Make a commit in local1 and push (this will be "remote" changes for local2)
        (local1_path / "remote_file.txt").write_bytes(b"remote content")
        run_git(local1_path, "add", "remote_file.txt")
        run_git(local1_path, "commit", "-m", "Remote commit")
        run_git(local1_path, "push")

        # Make a commit in local2 (this will be "local" changes)
        (local2_path / "local_file.txt").write_bytes(b"local content")
        run_git(local2_path, "add", "local_file.txt")
        run_git(local2_path, "commit", "-m", "Local commit")

        # Query from local2 - should see both local and remote changes
        repo = Repository(path=local2_path)
        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]

        remote_result = next(r for r in results if r.key[1] == "remote_status")
        assert isinstance(remote_result, ResultInfo)
        assert "  1 🔼" in remote_result.display_value  # 1 commit to push
        assert "  1 🔽" in remote_result.display_value  # 1 commit to pull
        assert remote_result.state_data["has_local_changes"] is True  # ty: ignore[not-subscriptable]
        assert remote_result.state_data["has_remote_changes"] is True  # ty: ignore[not-subscriptable]


# ----------------------------------------------------------------------
class TestLocalGitSourcePull:
    """Tests for the Pull method."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_fetches_remote_commits(self, tmp_path: Path) -> None:
        """Pull fetches and integrates remote commits."""

        # Create a bare "remote" repository
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Create first local repository and push
        local1_path = tmp_path / "local1"
        init_repo(local1_path)
        run_git(local1_path, "remote", "add", "origin", str(remote_path))
        branch = run_git(local1_path, "branch", "--show-current")
        run_git(local1_path, "push", "-u", "origin", branch)

        # Clone to second local repository
        local2_path = tmp_path / "local2"
        subprocess.run(["git", "clone", str(remote_path), str(local2_path)], check=True)
        run_git(local2_path, "config", "user.email", "test@test.com")
        run_git(local2_path, "config", "user.name", "Test User")

        # Make a commit in local1 and push
        (local1_path / "new_file.txt").write_bytes(b"new content")
        run_git(local1_path, "add", "new_file.txt")
        run_git(local1_path, "commit", "-m", "New commit from local1")
        run_git(local1_path, "push")

        # Verify local2 doesn't have the file yet
        assert not (local2_path / "new_file.txt").exists()

        # Pull in local2
        repo = Repository(path=local2_path)
        await LocalGitSource.Pull(repo)

        # Verify local2 now has the file
        assert (local2_path / "new_file.txt").exists()
        assert (local2_path / "new_file.txt").read_bytes() == b"new content"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_with_no_remote_changes(self, tmp_path: Path) -> None:
        """Pull succeeds when there are no remote changes."""

        # Create a bare "remote" repository
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Create local repository and push
        local_path = tmp_path / "local"
        init_repo(local_path)
        run_git(local_path, "remote", "add", "origin", str(remote_path))
        branch = run_git(local_path, "branch", "--show-current")
        run_git(local_path, "push", "-u", "origin", branch)

        # Pull should succeed with no changes
        repo = Repository(path=local_path)
        await LocalGitSource.Pull(repo)  # Should not raise

        # Verify repo is still valid
        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]
        assert len(results) == 4


# ----------------------------------------------------------------------
class TestLocalGitSourcePush:
    """Tests for the Push method."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_push_sends_local_commits(self, tmp_path: Path) -> None:
        """Push sends local commits to remote."""

        # Create a bare "remote" repository
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Create local repository and push initial commit
        local_path = tmp_path / "local"
        init_repo(local_path)
        run_git(local_path, "remote", "add", "origin", str(remote_path))
        branch = run_git(local_path, "branch", "--show-current")
        run_git(local_path, "push", "-u", "origin", branch)

        # Make a new commit locally
        (local_path / "pushed_file.txt").write_bytes(b"pushed content")
        run_git(local_path, "add", "pushed_file.txt")
        run_git(local_path, "commit", "-m", "Commit to push")

        # Verify we have a commit to push
        repo = Repository(path=local_path)
        source = LocalGitSource()
        results_before = [info async for info in source.Query(repo)]
        remote_result_before = next(r for r in results_before if r.key[1] == "remote_status")
        assert isinstance(remote_result_before, ResultInfo)
        assert "  1 🔼" in remote_result_before.display_value

        # Push
        await LocalGitSource.Push(repo)

        # Verify we no longer have commits to push
        results_after = [info async for info in source.Query(repo)]
        remote_result_after = next(r for r in results_after if r.key[1] == "remote_status")
        assert isinstance(remote_result_after, ResultInfo)
        assert "  0 🔼" in remote_result_after.display_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_push_with_no_local_commits(self, tmp_path: Path) -> None:
        """Push succeeds when there are no local commits to push."""

        # Create a bare "remote" repository
        remote_path = tmp_path / "remote.git"
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Create local repository and push
        local_path = tmp_path / "local"
        init_repo(local_path)
        run_git(local_path, "remote", "add", "origin", str(remote_path))
        branch = run_git(local_path, "branch", "--show-current")
        run_git(local_path, "push", "-u", "origin", branch)

        # Push should succeed with no changes
        repo = Repository(path=local_path)
        await LocalGitSource.Push(repo)  # Should not raise

        # Verify repo is still valid
        source = LocalGitSource()
        results = [info async for info in source.Query(repo)]
        assert len(results) == 4

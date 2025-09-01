from pathlib import Path

import pytest

from dbrownell_Common import SubprocessEx

from AllGitStatus.Lib import *


# ----------------------------------------------------------------------
def test_RepositoryData() -> None:
    rd = RepositoryData(
        Path("/some/path"),
        "the_branch",
        ["working_change1"],
        ["local_change1"],
        ["remote_change1", "remote_change2"],
    )

    assert rd.path == Path("/some/path")
    assert rd.branch == "the_branch"
    assert rd.working_changes == ["working_change1"]
    assert rd.local_changes == ["local_change1"]
    assert rd.remote_changes == ["remote_change1", "remote_change2"]


# ----------------------------------------------------------------------
def test_GitError() -> None:
    repo_path = Path("/some/repo")

    ge = GitError(repo_path, "the_command", 123, "the output")

    assert str(ge) == f"Error executing 'the_command' in '{repo_path}': the output"
    assert ge.repository_path == repo_path
    assert ge.command == "the_command"
    assert ge.returncode == 123
    assert ge.output == "the output"


# ----------------------------------------------------------------------
class TestExecuteGitCommand:
    repo_root = Path(__file__).parent.parent

    # ----------------------------------------------------------------------
    def test_Success(self) -> None:
        result = ExecuteGitCommand("git --version", self.repo_root)
        assert result

    # ----------------------------------------------------------------------
    def test_Error(self) -> None:
        with pytest.raises(GitError) as ex_info:
            ExecuteGitCommand("git invalid-command", self.repo_root)

        ex = ex_info.value

        assert ex.repository_path == self.repo_root
        assert ex.command == "git invalid-command"
        assert ex.returncode != 0
        assert ex.output


# ----------------------------------------------------------------------
def test_GenerateRepos(fs) -> None:
    fs.create_dir("/root")
    fs.create_dir("/root/repo1/.git")
    fs.create_dir("/root/collection/repo2/.git")
    fs.create_dir("/root/collection/repo3/.git")
    fs.create_dir("/root/collection/repo4/.git")
    fs.create_dir("/root/this/one/is/deeply/nested/repo5/.git")

    assert set(GenerateRepos(Path("/root"))) == {
        Path("/root/repo1"),
        Path("/root/collection/repo2"),
        Path("/root/collection/repo3"),
        Path("/root/collection/repo4"),
        Path("/root/this/one/is/deeply/nested/repo5"),
    }


# ----------------------------------------------------------------------
class TestGetRepositoryData:
    # ----------------------------------------------------------------------
    def test_NoRemote(self, tmp_path) -> None:
        repo = tmp_path / "repo"

        repo.mkdir(parents=True)

        assert SubprocessEx.Run("git init", cwd=repo).returncode == 0

        repo_data = GetRepositoryData(repo)

        assert repo_data.path == repo
        assert repo_data.branch in ["main", "master"], repo_data.branch
        assert repo_data.working_changes == []
        assert repo_data.local_changes == []
        assert repo_data.remote_changes == []

    # ----------------------------------------------------------------------
    def test_NoChanges(self, tmp_path) -> None:
        repo = tmp_path / "repo"
        clone = tmp_path / "clone"

        repo.mkdir(parents=True)

        assert SubprocessEx.Run("git init", cwd=repo).returncode == 0

        assert SubprocessEx.Run('git config user.name "Testing"', cwd=repo).returncode == 0
        assert SubprocessEx.Run('git config user.email "test@testing.com"', cwd=repo).returncode == 0

        # Create commits in the original repo
        (repo / "file1.txt").write_text("file1")
        assert SubprocessEx.Run('git add file1.txt && git commit -m "commit 1"', cwd=repo).returncode == 0

        (repo / "file2.txt").write_text("file2")
        assert SubprocessEx.Run('git add file2.txt && git commit -m "commit 2"', cwd=repo).returncode == 0

        # Clone the repo
        assert SubprocessEx.Run("git clone repo clone", cwd=tmp_path).returncode == 0

        # Get the data
        repo_data = GetRepositoryData(clone)

        assert repo_data.path == clone
        assert repo_data.branch in ["main", "master"], repo_data.branch
        assert repo_data.working_changes == []
        assert repo_data.local_changes == []
        assert repo_data.remote_changes == []

    # ----------------------------------------------------------------------
    def test_Complete(self, tmp_path) -> None:
        repo = tmp_path / "repo"
        clone = tmp_path / "clone"

        repo.mkdir(parents=True)

        assert SubprocessEx.Run("git init", cwd=repo).returncode == 0

        assert SubprocessEx.Run('git config user.name "Testing"', cwd=repo).returncode == 0
        assert SubprocessEx.Run('git config user.email "test@testing.com"', cwd=repo).returncode == 0

        assert SubprocessEx.Run("git clone repo clone", cwd=tmp_path).returncode == 0

        assert SubprocessEx.Run('git config user.name "Testing"', cwd=clone).returncode == 0
        assert SubprocessEx.Run('git config user.email "test@testing.com"', cwd=clone).returncode == 0

        # Create commits in the original repo
        (repo / "file1.txt").write_text("file1")
        assert SubprocessEx.Run('git add file1.txt && git commit -m "commit 1"', cwd=repo).returncode == 0

        (repo / "file2.txt").write_text("file2")
        assert SubprocessEx.Run('git add file2.txt && git commit -m "commit 2"', cwd=repo).returncode == 0

        # Create commits in the clone
        assert SubprocessEx.Run("git fetch", cwd=clone).returncode == 0

        (clone / "file3.txt").write_text("file3")
        assert SubprocessEx.Run('git add file3.txt && git commit -m "commit 3"', cwd=clone).returncode == 0

        (clone / "file4.txt").write_text("file4")
        assert SubprocessEx.Run('git add file4.txt && git commit -m "commit 4"', cwd=clone).returncode == 0

        # Create working changes in the clone
        (clone / "file5.txt").write_text("file5")
        (clone / "file6.txt").write_text("file6")
        assert SubprocessEx.Run("git add file6.txt", cwd=clone).returncode == 0

        # Get the data
        repo_data = GetRepositoryData(clone)

        assert repo_data.path == clone
        assert repo_data.branch in ["main", "master"], repo_data.branch
        assert repo_data.working_changes == ["A  file6.txt", "?? file5.txt"]

        assert len(repo_data.local_changes) == 2
        assert repo_data.local_changes[0].startswith("commit "), repo_data.local_changes[0]
        assert "commit 3" in repo_data.local_changes[0], repo_data.local_changes[0]
        assert repo_data.local_changes[1].startswith("commit "), repo_data.local_changes[1]
        assert "commit 4" in repo_data.local_changes[1], repo_data.local_changes[1]

        assert len(repo_data.remote_changes) == 2
        assert repo_data.remote_changes[0].startswith("commit "), repo_data.remote_changes[0]
        assert "commit 1" in repo_data.remote_changes[0], repo_data.remote_changes[0]
        assert repo_data.remote_changes[1].startswith("commit "), repo_data.remote_changes[1]
        assert "commit 2" in repo_data.remote_changes[1], repo_data.remote_changes[1]

    # ----------------------------------------------------------------------
    def test_DetachedHead(self, tmp_path):
        repo = tmp_path / "repo"

        repo.mkdir(parents=True)

        assert SubprocessEx.Run("git init", cwd=repo).returncode == 0

        assert SubprocessEx.Run('git config user.name "Testing"', cwd=repo).returncode == 0
        assert SubprocessEx.Run('git config user.email "test@testing.com"', cwd=repo).returncode == 0

        # Create commits in the original repo
        (repo / "file1.txt").write_text("file1")
        assert SubprocessEx.Run('git add file1.txt && git commit -m "commit 1"', cwd=repo).returncode == 0

        (repo / "file2.txt").write_text("file2")
        assert SubprocessEx.Run('git add file2.txt && git commit -m "commit 2"', cwd=repo).returncode == 0

        # Get the commit hashes
        result = SubprocessEx.Run('git log --pretty=format:"%H"', cwd=repo)
        assert result.returncode == 0, result.output

        hash = result.output.strip().splitlines()[-1]

        # Get into a detached head state
        assert SubprocessEx.Run(f"git checkout {hash} --detach", cwd=repo).returncode == 0

        # Get the data
        repo_data = GetRepositoryData(repo)

        assert repo_data.path == repo
        assert repo_data.branch.startswith("HEAD detached at "), repo_data.branch
        assert repo_data.working_changes == []
        assert repo_data.local_changes == []
        assert repo_data.remote_changes == []

        # Make a working change
        (repo / "file3.txt").write_text("file3")

        repo_data = GetRepositoryData(repo)

        assert repo_data.path == repo
        assert repo_data.branch.startswith("HEAD detached at "), repo_data.branch
        assert repo_data.working_changes == ["?? file3.txt"]
        assert repo_data.local_changes == []
        assert repo_data.remote_changes == []

# noqa: D100
import os
import re
import uuid

from collections.abc import Iterator
from pathlib import Path

from attrs import define
from dbrownell_Common import SubprocessEx


# ----------------------------------------------------------------------
# |
# |  Public Types
# |
# ----------------------------------------------------------------------
@define
class RepositoryData:
    """Information about a specific repository."""

    path: Path
    branch: str
    working_changes: list[str]
    local_changes: list[str]
    remote_changes: list[str]


# ----------------------------------------------------------------------
class GitError(Exception):
    """Exception raised when a git command fails."""

    def __init__(
        self,
        repository_path: Path,
        command: str,
        returncode: int,
        output: str,
    ) -> None:
        super().__init__(f"Error executing '{command}' in '{repository_path}': {output}")

        self.repository_path = repository_path
        self.command = command
        self.returncode = returncode
        self.output = output


# ----------------------------------------------------------------------
# |
# |  Public Functions
# |
# ----------------------------------------------------------------------
def ExecuteGitCommand(
    command: str,
    repository_path: Path,
) -> str:
    """Execute a git command."""

    result = SubprocessEx.Run(command, cwd=repository_path)
    if result.returncode != 0:
        raise GitError(repository_path, command, result.returncode, result.output.strip())

    return result.output.strip()


# ----------------------------------------------------------------------
def GenerateRepos(root: Path) -> Iterator[Path]:
    """Generate all git repositories found under the specified root directory."""

    for this_root_str, directories, _ in os.walk(root):
        this_root = Path(this_root_str)

        if ".git" in directories:
            yield this_root

            # Do not spend any more time searching this directory and its descendants
            directories[:] = []


# ----------------------------------------------------------------------
def GetRepositoryData(repository: Path) -> RepositoryData:
    """Get information about a specific repository."""

    is_detached_head = False

    # Get the branch
    branch = ExecuteGitCommand("git branch --show-current", repository)
    if not branch:
        content = ExecuteGitCommand("git status", repository)
        if content.startswith("HEAD detached"):
            is_detached_head = True
            branch = content.splitlines()[0]

    # Get working changes
    working_changes = ExecuteGitCommand("git status --short", repository).splitlines()

    # Does this repo have a remote?
    has_remote = not is_detached_head and bool(ExecuteGitCommand("git remote -v", repository))

    if not has_remote:
        local_changes: list[str] = []
        remote_changes: list[str] = []
    else:
        # Get local changes
        delimiter = str(uuid.uuid4()).replace("-", "")

        content = ExecuteGitCommand(
            f'git log origin/{branch}..{branch} --format="commit %H%nAuthor: %an <%ae>%nDate: %ad%n%n    %s%n%b%n{delimiter}" --reverse',
            repository,
        )

        if not content:
            local_changes = []
        else:
            local_changes = [commit.strip() for commit in re.split(delimiter, content)]

            if not local_changes[-1]:
                local_changes = local_changes[:-1]

        # Get remote changes
        ExecuteGitCommand("git fetch", repository)

        content = ExecuteGitCommand(
            f'git log {branch}..origin/{branch} --first-parent --format="commit %H%nAuthor: %an <%ae>%nDate: %ad%n%n    %s%n%b%n{delimiter}" --reverse',
            repository,
        )

        if not content:
            remote_changes = []
        else:
            remote_changes = [commit.strip() for commit in re.split(delimiter, content)]

            if not remote_changes[-1]:
                remote_changes = remote_changes[:-1]

    return RepositoryData(repository, branch, working_changes, local_changes, remote_changes)

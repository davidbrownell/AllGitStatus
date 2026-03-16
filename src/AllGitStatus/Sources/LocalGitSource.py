# noqa: D100
import asyncio
import re
import textwrap
import uuid

from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path

from rich.console import Group
from rich.panel import Panel
from rich.text import Text

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo, Source


# ----------------------------------------------------------------------
class LocalGitSource(Source):
    """Source of information about local git repositories."""

    # ----------------------------------------------------------------------
    async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # noqa: C901, D102, PLR0915  # ty: ignore[invalid-method-override]
        # ----------------------------------------------------------------------
        # |  Get the current branch
        is_detached_head = False
        branch = None

        # ----------------------------------------------------------------------
        async def GetBranch() -> LocalGitSource._InternalResultInfo:
            nonlocal is_detached_head
            nonlocal branch

            _, branch = await self._RawGitCommand(repo.path, "branch", "--show-current")

            if not branch:
                _, branch = await self._RawGitCommand(repo.path, "status")

                if branch.startswith("HEAD detached"):
                    is_detached_head = True
                    branch = branch.splitlines()[0]

            return LocalGitSource._InternalResultInfo(
                branch,
                "<Detached HEAD state>" if is_detached_head else None,
            )

        # ----------------------------------------------------------------------

        yield await self._Execute(
            repo,
            (self.__class__.__name__, "current_branch"),
            GetBranch,
        )

        # ----------------------------------------------------------------------
        # |  Get the local changes
        # ----------------------------------------------------------------------
        async def GetLocalStatus() -> LocalGitSource._InternalResultInfo:
            _, content = await self._RawGitCommand(repo.path, "status", "--porcelain")

            staged = 0
            unstaged = 0
            untracked = 0

            for line in content.splitlines():
                assert line

                index_status = line[0]
                worktree_status = line[1]

                if index_status == "?":
                    untracked += 1
                elif index_status not in [" ", "?"]:
                    staged += 1
                elif worktree_status not in [" ", "?"]:
                    unstaged += 1

            return LocalGitSource._InternalResultInfo(
                f"{staged:3} ✅ {unstaged:3} 🟡  {untracked:3} ❓",
                content or "<No local changes>",
            )

        # ----------------------------------------------------------------------

        yield await self._Execute(
            repo,
            (self.__class__.__name__, "local_status"),
            GetLocalStatus,
        )

        # ----------------------------------------------------------------------
        # |  Get the stashes
        # ----------------------------------------------------------------------
        async def GetStashes() -> LocalGitSource._InternalResultInfo:
            _, content = await self._RawGitCommand(repo.path, "stash", "list")

            stashes = 0 if not content else len(content.splitlines())

            return LocalGitSource._InternalResultInfo(
                f"{stashes:3} 🧺",
                content or "<No stashes>",
            )

        # ----------------------------------------------------------------------

        yield await self._Execute(
            repo,
            (self.__class__.__name__, "stashes"),
            GetStashes,
        )

        # ----------------------------------------------------------------------
        # |  Get the remote status
        # ----------------------------------------------------------------------
        async def GetRemoteStatus() -> LocalGitSource._InternalResultInfo:
            has_remote = not is_detached_head and bool(
                (await self._RawGitCommand(repo.path, "remote", "-v"))[1]
            )

            if not has_remote:
                local_changes: list[str] = []
                remote_changes: list[str] = []
            else:
                delimiter = str(uuid.uuid4()).replace("-", "")

                # Get the local changes
                _, content = await self._RawGitCommand(
                    repo.path,
                    "log",
                    f"origin/{branch}..{branch}",
                    f"--format=commit %H%nAuthor: %an <%ae>%nDate: %ad%n%n    %s%n%b%n{delimiter}",
                    "--reverse",
                )

                if not content:
                    local_changes = []
                else:
                    local_changes = [commit.strip() for commit in re.split(delimiter, content)]
                    if local_changes and not local_changes[-1]:
                        local_changes = local_changes[:-1]

                # Get the remote changes
                _, content = await self._RawGitCommand(repo.path, "fetch")

                _, content = await self._RawGitCommand(
                    repo.path,
                    "log",
                    f"{branch}..origin/{branch}",
                    f"--format=commit %H%nAuthor: %an <%ae>%nDate: %ad%n%n    %s%n%b%n{delimiter}",
                    "--reverse",
                    "--first-parent",
                )

                if not content:
                    remote_changes = []
                else:
                    remote_changes = [commit.strip() for commit in re.split(delimiter, content)]
                    if remote_changes and not remote_changes[-1]:
                        remote_changes = remote_changes[:-1]

            # Create the additional info
            has_local_changes = bool(local_changes)
            has_remote_changes = bool(remote_changes)

            if not has_local_changes and not has_remote_changes:
                additional_data = "<No remote changes>"
            else:
                panels: list[Panel] = []

                if has_local_changes:
                    panels.append(
                        Panel(
                            Group(
                                *(
                                    Panel(Text(local_change), title=str(local_change_index + 1))
                                    for local_change_index, local_change in enumerate(local_changes)
                                )
                            ),
                            title="Changes to Push",
                            border_style="green",
                        )
                    )
                if has_remote_changes:
                    panels.append(
                        Panel(
                            Group(
                                *(
                                    Panel(Text(remote_change), title=str(remote_change_index + 1))
                                    for remote_change_index, remote_change in enumerate(remote_changes)
                                )
                            ),
                            title="Changes to Pull",
                            border_style="blue",
                        )
                    )

                additional_data = Group(*panels)

            return LocalGitSource._InternalResultInfo(
                f"{len(local_changes):3} 🔼 {len(remote_changes):3} 🔽",
                additional_data,
                state_data={
                    "has_local_changes": has_local_changes,
                    "has_remote_changes": has_remote_changes,
                },
            )

        # ----------------------------------------------------------------------

        yield await self._Execute(
            repo,
            (self.__class__.__name__, "remote_status"),
            GetRemoteStatus,
        )

    # ----------------------------------------------------------------------
    @classmethod
    async def Pull(cls, repo: Repository) -> None:
        """Pull changes from the remote repository."""

        await cls._RawGitCommand(repo.path, "pull")

    # ----------------------------------------------------------------------
    @classmethod
    async def Push(cls, repo: Repository) -> None:
        """Push changes to the remote repository."""

        await cls._RawGitCommand(repo.path, "push")

    # ----------------------------------------------------------------------
    # |
    # |  Private Types
    # |
    # ----------------------------------------------------------------------
    @dataclass(frozen=True)
    class _InternalResultInfo:
        display_value: str
        additional_info: object | None = field(default=None)
        state_data: object | None = field(kw_only=True, default=None)

    # ----------------------------------------------------------------------
    # |
    # |  Private Methods
    # |
    # ----------------------------------------------------------------------
    @staticmethod
    async def _Execute(
        repo: Repository,
        key: tuple[str, str | None],
        callback_func: Callable[[], Awaitable[_InternalResultInfo]],
    ) -> ResultInfo | ErrorInfo:
        try:
            internal_result = await callback_func()

            return ResultInfo(
                repo,
                key,
                internal_result.display_value,
                internal_result.additional_info,
                state_data=internal_result.state_data,
            )

        except Exception as ex:
            return ErrorInfo(repo, key, ex)

    # ----------------------------------------------------------------------
    @staticmethod
    async def _RawGitCommand(
        repo_path: Path,
        *args: str,
        raise_on_error: bool = True,
    ) -> tuple[int, str]:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-C",
            str(repo_path),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        stdout, _ = await proc.communicate()
        stdout = stdout.decode().rstrip()

        if proc.returncode != 0 and raise_on_error:
            msg = textwrap.dedent(
                """\
                "{}"

                {}
                """,
            ).format(
                " ".join(
                    [
                        "git",
                    ]
                    + ['"{}"'.format(arg) for arg in args]
                ),
                stdout,
            )

            raise RuntimeError(msg)

        return proc.returncode or 0, stdout

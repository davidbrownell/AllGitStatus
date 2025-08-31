import asyncio
import textwrap

from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from textual.pilot import Pilot
from textual.widgets import RichLog

from AllGitStatus.Lib import RepositoryData, GetRepositoryData, GitError
from AllGitStatus.MainApp import MainApp


# ----------------------------------------------------------------------
async def test_Startup1():
    async with _GeneratePilot(None) as pilot:
        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["repo1", "branch1", "Δ2"],
            ["repo2", "branch2", "↑2"],
            ["repo3", "branch3", "↓2"],
            ["repo4", "branch4", "Δ3 ↑3 ↓3"],
        ]

        assert pilot.app._data_table.cursor_row == 0

        assert _GetRichLogContent(pilot.app._git_log) == ""
        assert _GetRichLogContent(pilot.app._working_log) == textwrap.dedent(
            """\
            working1
            working2
            """,
        )

        assert _GetRichLogContent(pilot.app._local_log) == ""
        assert _GetRichLogContent(pilot.app._remote_log) == ""


# ----------------------------------------------------------------------
async def test_Startup2():
    async with _GeneratePilot(["down"]) as pilot:
        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["repo1", "branch1", "Δ2"],
            ["repo2", "branch2", "↑2"],
            ["repo3", "branch3", "↓2"],
            ["repo4", "branch4", "Δ3 ↑3 ↓3"],
        ]

        assert pilot.app._data_table.cursor_row == 1

        assert _GetRichLogContent(pilot.app._git_log) == ""
        assert _GetRichLogContent(pilot.app._working_log) == ""

        assert _GetRichLogContent(pilot.app._local_log) == textwrap.dedent(
            """\
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ local1                                                                     │
            ╰────────────────────────────────────────────────────────────────────────────╯
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ local2                                                                     │
            ╰────────────────────────────────────────────────────────────────────────────╯
            """,
        )

        assert _GetRichLogContent(pilot.app._remote_log) == ""


# ----------------------------------------------------------------------
async def test_Startup3():
    async with _GeneratePilot(["down", "down"]) as pilot:
        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["repo1", "branch1", "Δ2"],
            ["repo2", "branch2", "↑2"],
            ["repo3", "branch3", "↓2"],
            ["repo4", "branch4", "Δ3 ↑3 ↓3"],
        ]

        assert pilot.app._data_table.cursor_row == 2

        assert _GetRichLogContent(pilot.app._git_log) == ""
        assert _GetRichLogContent(pilot.app._working_log) == ""
        assert _GetRichLogContent(pilot.app._local_log) == ""
        assert _GetRichLogContent(pilot.app._remote_log) == textwrap.dedent(
            """\
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ remote1                                                                    │
            ╰────────────────────────────────────────────────────────────────────────────╯
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ remote2                                                                    │
            ╰────────────────────────────────────────────────────────────────────────────╯
            """,
        )


# ----------------------------------------------------------------------
async def test_Startup4():
    async with _GeneratePilot(["down", "down", "down"]) as pilot:
        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["repo1", "branch1", "Δ2"],
            ["repo2", "branch2", "↑2"],
            ["repo3", "branch3", "↓2"],
            ["repo4", "branch4", "Δ3 ↑3 ↓3"],
        ]

        assert pilot.app._data_table.cursor_row == 3

        assert _GetRichLogContent(pilot.app._git_log) == ""

        assert _GetRichLogContent(pilot.app._working_log) == textwrap.dedent(
            """\
            workingA
            workingB
            workingC
            """,
        )

        assert _GetRichLogContent(pilot.app._local_log) == textwrap.dedent(
            """\
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ localA                                                                     │
            ╰────────────────────────────────────────────────────────────────────────────╯
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ localB                                                                     │
            ╰────────────────────────────────────────────────────────────────────────────╯
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ localC                                                                     │
            ╰────────────────────────────────────────────────────────────────────────────╯
            """,
        )

        assert _GetRichLogContent(pilot.app._remote_log) == textwrap.dedent(
            """\
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ remoteA                                                                    │
            ╰────────────────────────────────────────────────────────────────────────────╯
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ remoteB                                                                    │
            ╰────────────────────────────────────────────────────────────────────────────╯
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ remoteC                                                                    │
            ╰────────────────────────────────────────────────────────────────────────────╯
            """,
        )


# ----------------------------------------------------------------------
async def test_Focus1():
    async with _GeneratePilot(None) as pilot:
        assert pilot.app._data_table.has_focus
        assert pilot.app._git_log.has_focus is False
        assert pilot.app._working_log.has_focus is False
        assert pilot.app._local_log.has_focus is False
        assert pilot.app._remote_log.has_focus is False

    async with _GeneratePilot(["2", "1"]) as pilot:
        assert pilot.app._data_table.has_focus
        assert pilot.app._git_log.has_focus is False
        assert pilot.app._working_log.has_focus is False
        assert pilot.app._local_log.has_focus is False
        assert pilot.app._remote_log.has_focus is False


# ----------------------------------------------------------------------
async def test_Focus2():
    async with _GeneratePilot(["2"]) as pilot:
        assert pilot.app._data_table.has_focus is False
        assert pilot.app._git_log.has_focus
        assert pilot.app._working_log.has_focus is False
        assert pilot.app._local_log.has_focus is False
        assert pilot.app._remote_log.has_focus is False


# ----------------------------------------------------------------------
async def test_Focus3():
    async with _GeneratePilot(["3"]) as pilot:
        assert pilot.app._data_table.has_focus is False
        assert pilot.app._git_log.has_focus is False
        assert pilot.app._working_log.has_focus
        assert pilot.app._local_log.has_focus is False
        assert pilot.app._remote_log.has_focus is False


# ----------------------------------------------------------------------
async def test_Focus4():
    async with _GeneratePilot(["4"]) as pilot:
        assert pilot.app._data_table.has_focus is False
        assert pilot.app._git_log.has_focus is False
        assert pilot.app._working_log.has_focus is False
        assert pilot.app._local_log.has_focus
        assert pilot.app._remote_log.has_focus is False


# ----------------------------------------------------------------------
async def test_Focus5():
    async with _GeneratePilot(["5"]) as pilot:
        assert pilot.app._data_table.has_focus is False
        assert pilot.app._git_log.has_focus is False
        assert pilot.app._working_log.has_focus is False
        assert pilot.app._local_log.has_focus is False
        assert pilot.app._remote_log.has_focus


# ----------------------------------------------------------------------
async def test_RefreshAll():
    async with _GeneratePilot(["R"]) as pilot:
        await pilot.pause()

        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["repo1", "branch1", "Δ2"],
            ["repo2", "branch2", "↑2"],
            ["repo3", "branch3", "↓2"],
            ["repo4", "branch4", "Δ3 ↑3 ↓3"],
        ]

        assert pilot.app._data_table.cursor_row == 0

        assert _GetRichLogContent(pilot.app._git_log) == ""
        assert _GetRichLogContent(pilot.app._working_log) == textwrap.dedent(
            """\
            working1
            working2
            """,
        )

        assert _GetRichLogContent(pilot.app._local_log) == ""
        assert _GetRichLogContent(pilot.app._remote_log) == ""


# ----------------------------------------------------------------------
async def test_Refresh():
    async with _GeneratePilot(["r"]) as pilot:
        await pilot.pause()

        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["repo1", "branch1", "Δ2"],
            ["repo2", "branch2", "↑2"],
            ["repo3", "branch3", "↓2"],
            ["repo4", "branch4", "Δ3 ↑3 ↓3"],
        ]

        assert pilot.app._data_table.cursor_row == 0

        assert _GetRichLogContent(pilot.app._git_log) == ""
        assert _GetRichLogContent(pilot.app._working_log) == textwrap.dedent(
            """\
            working1
            working2
            """,
        )

        assert _GetRichLogContent(pilot.app._local_log) == ""
        assert _GetRichLogContent(pilot.app._remote_log) == ""


# ----------------------------------------------------------------------
async def test_InitialGitError():
    # ----------------------------------------------------------------------
    def GetRepositoryData(path: Path) -> RepositoryData:
        if path == Path("repo1"):
            raise GitError(path, "the_command", -123, "this is the error")

        return RepositoryData(path, "branch", [], [], [])

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1"],
        get_repository_data_func=GetRepositoryData,
    ) as pilot:
        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["!! repo1 !!", "", ""],
            ["repo2", "branch", ""],
            ["repo3", "branch", ""],
            ["repo4", "branch", ""],
        ]

        assert pilot.app._data_table.cursor_row == 0

        assert _GetRichLogContent(pilot.app._git_log) == textwrap.dedent(
            """\
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ repo1 (-123)                                                               │
            │ the_command                                                                │
            │                                                                            │
            │ this is the error                                                          │
            │                                                                            │
            ╰────────────────────────────────────────────────────────────────────────────╯
            """,
        )

        assert _GetRichLogContent(pilot.app._working_log) == ""
        assert _GetRichLogContent(pilot.app._local_log) == ""
        assert _GetRichLogContent(pilot.app._remote_log) == ""


# ----------------------------------------------------------------------
async def test_InitialGitErrorAndRecovery():
    first_pass = True

    # ----------------------------------------------------------------------
    def GetRepositoryData(path: Path) -> RepositoryData:
        if path == Path("repo1"):
            nonlocal first_pass

            if first_pass:
                first_pass = False
                raise GitError(path, "the_command", -123, "this is the error")

        return RepositoryData(path, "branch", [], [], [])

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1", "r"],
        get_repository_data_func=GetRepositoryData,
    ) as pilot:
        await pilot.pause()

        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["repo1", "branch", ""],
            ["repo2", "branch", ""],
            ["repo3", "branch", ""],
            ["repo4", "branch", ""],
        ]

        assert pilot.app._data_table.cursor_row == 0

        assert _GetRichLogContent(pilot.app._git_log) == textwrap.dedent(
            """\
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ repo1 (-123)                                                               │
            │ the_command                                                                │
            │                                                                            │
            │ this is the error                                                          │
            │                                                                            │
            ╰────────────────────────────────────────────────────────────────────────────╯
            """,
        )

        assert _GetRichLogContent(pilot.app._working_log) == ""
        assert _GetRichLogContent(pilot.app._local_log) == ""
        assert _GetRichLogContent(pilot.app._remote_log) == ""


# ----------------------------------------------------------------------
async def test_InitialGitErrorClearErrors():
    # ----------------------------------------------------------------------
    def GetRepositoryData(path: Path) -> RepositoryData:
        if path == Path("repo1"):
            raise GitError(path, "the_command", -123, "this is the error")

        return RepositoryData(path, "branch", [], [], [])

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1", "X"],
        get_repository_data_func=GetRepositoryData,
    ) as pilot:
        await pilot.pause()

        rows = _GetDataTableRowData(pilot)

        assert rows == [
            ["!! repo1 !!", "", ""],
            ["repo2", "branch", ""],
            ["repo3", "branch", ""],
            ["repo4", "branch", ""],
        ]

        assert pilot.app._data_table.cursor_row == 0

        assert _GetRichLogContent(pilot.app._git_log) == ""
        assert _GetRichLogContent(pilot.app._working_log) == ""
        assert _GetRichLogContent(pilot.app._local_log) == ""
        assert _GetRichLogContent(pilot.app._remote_log) == ""


# ----------------------------------------------------------------------
async def test_Pull():
    """Test pulling on a repo that has changes."""

    was_invoked = False

    # ----------------------------------------------------------------------
    def ExecuteGitCommand(command: str, repository_path: Path) -> None:
        assert command == "git pull"
        assert repository_path == Path("repo3")

        nonlocal was_invoked
        was_invoked = True

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1", "down", "down", "p"],
        execute_git_command_func=ExecuteGitCommand,
    ) as pilot:
        await pilot.pause()

        assert was_invoked


# ----------------------------------------------------------------------
async def test_PullNoChanges():
    """Test pulling on a repo that doesn't have changes."""

    # ----------------------------------------------------------------------
    def ExecuteGitCommand(command: str, repository_path: Path) -> None:
        assert False, repository_path

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1", "p"],
        execute_git_command_func=ExecuteGitCommand,
    ) as pilot:
        await pilot.pause()


# ----------------------------------------------------------------------
async def test_Push():
    """Test pushing on a repo that has changes."""

    was_invoked = False

    # ----------------------------------------------------------------------
    def ExecuteGitCommand(command: str, repository_path: Path) -> None:
        assert command == "git push"
        assert repository_path == Path("repo2")

        nonlocal was_invoked
        was_invoked = True

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1", "down", "P"],
        execute_git_command_func=ExecuteGitCommand,
    ) as pilot:
        await pilot.pause()

        assert was_invoked


# ----------------------------------------------------------------------
async def test_PushNoChanges():
    """Test pushing on a repo that doesn't have changes."""

    # ----------------------------------------------------------------------
    def ExecuteGitCommand(command: str, repository_path: Path) -> None:
        assert False, repository_path

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1", "P"],
        execute_git_command_func=ExecuteGitCommand,
    ) as pilot:
        await pilot.pause()


# ----------------------------------------------------------------------
async def test_PushError():
    was_invoked = False

    # ----------------------------------------------------------------------
    def ExecuteGitCommand(command: str, repository_path: Path) -> None:
        nonlocal was_invoked
        was_invoked = True

        raise GitError(repository_path, command, -123, "this is the error")

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        ["1", "down", "P"],
        execute_git_command_func=ExecuteGitCommand,
    ) as pilot:
        await pilot.pause()

        assert was_invoked

        assert _GetRichLogContent(pilot.app._git_log) == textwrap.dedent(
            """\
            ╭────────────────────────────────────────────────────────────────────────────╮
            │ repo2 (-123)                                                               │
            │ git push                                                                   │
            │                                                                            │
            │ this is the error                                                          │
            │                                                                            │
            ╰────────────────────────────────────────────────────────────────────────────╯
            """,
        )


# ----------------------------------------------------------------------
async def test_LaunchedFromRepositoryDir() -> None:
    """Ensure that the repository name is displayed when the app is run in a working directory that is a git repository."""

    path = Path(__file__).parent

    # ----------------------------------------------------------------------
    def GenerateRepos(root_path: Path) -> list[Path]:
        return [path]

    # ----------------------------------------------------------------------
    def GetRepositoryData(the_path: Path) -> RepositoryData:
        assert the_path == path
        return RepositoryData(the_path, "the mighty branch", [], [], [])

    # ----------------------------------------------------------------------

    async with _GeneratePilot(
        None,
        generate_repos_func=GenerateRepos,
        get_repository_data_func=GetRepositoryData,
        path_arg=path,
    ) as pilot:
        rows = _GetDataTableRowData(pilot)

        assert rows == [
            [path.name, "the mighty branch", ""],
        ]


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
@asynccontextmanager
async def _GeneratePilot(
    keys: list[str] | None,
    *,
    generate_repos_func: Callable[[Path], list[Path]] | None = None,
    get_repository_data_func: Callable[[Path], RepositoryData] | None = None,
    execute_git_command_func: Callable[[str, Path], None] | None = None,
    path_arg: Path | None = None,
) -> AsyncGenerator[Pilot]:
    with (
        patch("AllGitStatus.Impl.GetRepositoriesModal.GenerateRepos") as generate_repos_mock,
        patch("AllGitStatus.MainApp.GetRepositoryData") as get_repository_data_mock,
        patch("AllGitStatus.MainApp.ExecuteGitCommand") as execute_git_command_mock,
    ):
        repos = (
            generate_repos_func(path_arg or Path())
            if generate_repos_func
            else [Path("repo1"), Path("repo2"), Path("repo3"), Path("repo4")]
        )

        # ----------------------------------------------------------------------
        def GetRepositoryData(repository: Path) -> RepositoryData:
            if repository == repos[0]:
                return RepositoryData(repos[0], "branch1", ["working1", "working2"], [], [])

            if repository == repos[1]:
                return RepositoryData(repos[1], "branch2", [], ["local1", "local2"], [])

            if repository == repos[2]:
                return RepositoryData(repos[2], "branch3", [], [], ["remote1", "remote2"])

            if repository == repos[3]:
                return RepositoryData(
                    repos[3],
                    "branch4",
                    ["workingA", "workingB", "workingC"],
                    ["localA", "localB", "localC"],
                    ["remoteA", "remoteB", "remoteC"],
                )

            assert False, "Invalid repository"

        generate_repos_mock.side_effect = generate_repos_func or (lambda *args, **kwargs: repos)
        get_repository_data_mock.side_effect = get_repository_data_func or GetRepositoryData
        execute_git_command_mock.side_effect = execute_git_command_func or (lambda *args, **kwargs: None)

        async with MainApp(path_arg or Path()).run_test() as pilot:
            # Give the repos a chance to populate
            while get_repository_data_mock.call_count < len(repos):
                await asyncio.sleep(0.1)

            await pilot.press(*(keys or []))
            await pilot.pause()

            # This is a hack, but it seems like sometimes one pause isn't enough
            await pilot.pause()

            yield pilot


# ----------------------------------------------------------------------
def _GetDataTableRowData(pilot: Pilot) -> list[list[str]]:
    row_data: list[list[str]] = []

    for row_key in pilot.app._data_table.rows:
        this_row_data = pilot.app._data_table.get_row(row_key)
        row_data.append(this_row_data)

    return row_data


# ----------------------------------------------------------------------
def _GetRichLogContent(widget: RichLog) -> str:
    content: list[str] = []

    for line in widget.lines:
        content.append(line.text)

    result = "\n".join(content)
    if result:
        result += "\n"

    return result

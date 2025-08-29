import asyncio

from collections.abc import Callable
from unittest.mock import patch

from pathlib import Path

from AllGitStatus.Lib import RepositoryData
from AllGitStatus.MainApp import MainApp


# ----------------------------------------------------------------------
def _Execute(
    snap_compare,
    *,
    generate_repos_func: Callable[[], list[Path]] | None = None,
    get_repository_data_func: Callable[[Path], RepositoryData] | None = None,
    execute_git_command_func: Callable[[str, Path], None] | None = None,
    **kwargs,
) -> None:
    with (
        patch("AllGitStatus.Impl.GetRepositoriesModal.GenerateRepos") as generate_repos_mock,
        patch("AllGitStatus.MainApp.GetRepositoryData") as get_repository_data_mock,
        patch("AllGitStatus.MainApp.ExecuteGitCommand") as execute_git_command_mock,
    ):
        repos = [Path("repo1"), Path("repo2"), Path("repo3"), Path("repo4")]

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

        # ----------------------------------------------------------------------
        async def Initialize(pilot) -> None:
            # Give the repos a chance to populate
            while get_repository_data_mock.call_count < len(repos):
                await asyncio.sleep(0.1)

        # ----------------------------------------------------------------------

        get_repository_data_mock.side_effect = get_repository_data_func or GetRepositoryData
        generate_repos_mock.side_effect = generate_repos_func or (lambda *args, **kwargs: repos)
        execute_git_command_mock.side_effect = execute_git_command_func or (lambda *args, **kwargs: None)

        snap_compare(
            MainApp(Path()),
            run_before=Initialize,
            terminal_size=(100, 40),
            **kwargs,
        )


# ----------------------------------------------------------------------
def test_Startup(snap_compare):
    _Execute(snap_compare)


# ----------------------------------------------------------------------
def test_Startup2(snap_compare):
    _Execute(snap_compare, press=["down"])


# ----------------------------------------------------------------------
def test_Startup3(snap_compare):
    _Execute(snap_compare, press=["down", "down"])


# ----------------------------------------------------------------------
def test_Startup4(snap_compare):
    _Execute(snap_compare, press=["down", "down", "down"])


# ----------------------------------------------------------------------
def test_Focus1(snap_compare):
    _Execute(snap_compare, press=["2", "1"])


# ----------------------------------------------------------------------
def test_Focus2(snap_compare):
    _Execute(snap_compare, press=["2"])


# ----------------------------------------------------------------------
def test_Focus3(snap_compare):
    _Execute(snap_compare, press=["3"])


# ----------------------------------------------------------------------
def test_Focus4(snap_compare):
    _Execute(snap_compare, press=["4"])


# ----------------------------------------------------------------------
def test_Focus5(snap_compare):
    _Execute(snap_compare, press=["5"])

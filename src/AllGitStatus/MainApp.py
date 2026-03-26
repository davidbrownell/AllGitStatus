# noqa: D100
import contextlib
import textwrap

from dataclasses import dataclass
from pathlib import Path

import aiohttp
from rich.text import Text
from rich.traceback import Traceback
from textual.app import App, ComposeResult, ScreenStackError
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import ModalScreen
from textual.widgets import DataTable, Footer, Header, Label, RichLog

from AllGitStatus import __version__
from AllGitStatus.Repository import EnumerateRepositories, Repository
from AllGitStatus.Sources.GitHubSource import GitHubSource
from AllGitStatus.Sources.LocalGitSource import LocalGitSource
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Column:
    """Column displayed within a data table."""

    value: int
    name: str
    justify: str


# ----------------------------------------------------------------------
NameColumn = Column(0, "Name", "left")
BranchColumn = Column(1, "Branch", "center")
LocalColumn = Column(2, "Local", "center")
StashesColumn = Column(3, "Stashes", "center")
RemoteColumn = Column(4, "Remote", "center")
StarsColumn = Column(5, "Stars", "center")
ForksColumn = Column(6, "Forks", "center")
WatchersColumn = Column(7, "Watchers", "center")
IssuesColumn = Column(8, "Issues", "center")
PullRequestsColumn = Column(9, "PRs", "center")
SecurityAlertsColumn = Column(10, "Security", "center")

COLUMN_MAP: dict[
    tuple[
        str,  # source class name
        str | None,  # source key value
    ],
    Column,
] = {
    ("", ""): NameColumn,
    (LocalGitSource.__name__, "current_branch"): BranchColumn,
    (LocalGitSource.__name__, "local_status"): LocalColumn,
    (LocalGitSource.__name__, "stashes"): StashesColumn,
    (LocalGitSource.__name__, "remote_status"): RemoteColumn,
    (GitHubSource.__name__, "stars"): StarsColumn,
    (GitHubSource.__name__, "forks"): ForksColumn,
    (GitHubSource.__name__, "watchers"): WatchersColumn,
    (GitHubSource.__name__, "issues"): IssuesColumn,
    (GitHubSource.__name__, "pull_requests"): PullRequestsColumn,
    (GitHubSource.__name__, "security_alerts"): SecurityAlertsColumn,
}


# ----------------------------------------------------------------------
class MainApp(App):
    """Main application."""

    CSS_PATH = Path(__file__).with_suffix(".tcss")

    BINDINGS = [  # noqa: RUF012
        ("R", "RefreshAll", "Refresh All"),
        ("r", "RefreshSelected", "Refresh"),
        ("p", "PullSelected", "Pull"),
        ("P", "PushSelected", "Push"),
        ("q", "quit", "Quit"),
    ]

    # ----------------------------------------------------------------------
    def __init__(
        self,
        working_dir: Path,
        github_pat: str | None,
        *args,
        debug: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self._working_dir = working_dir
        self._github_pat = github_pat
        self._debug = debug

        self.title = "AllGitStatus{}".format(" [DEBUG]" if debug else "")

        self._data_table: DataTable = DataTable(
            cursor_type="cell",
            zebra_stripes=True,
            id="data_table",
        )

        self._data_table.border_title = "[1] Repositories"

        self._additional_info = RichLog(id="additional_info", auto_scroll=False)
        self._additional_info.border_title = "[2] Additional Info"

        self._repositories: list[Repository] | None = None

        self._additional_info_data: dict[
            int,  # row_index
            dict[
                int,  # column_index
                object,
            ],
        ] = {}

        self._state_data: dict[
            int,  # row_index
            dict[
                int,  # column_index
                object,
            ],
        ] = {}

        # The lifetime of this object is defined by `on_mount` and `on_unmount` as aiohttp.ClientSession
        # requires an active event loop
        self._github_session: aiohttp.ClientSession | None = None

    # ----------------------------------------------------------------------
    def compose(self) -> ComposeResult:  # noqa: D102
        yield Header()
        yield Vertical(
            self._data_table,
            self._additional_info,
            id="vertical_group",
        )
        yield Horizontal(Footer(), Label(__version__), id="footer")

    # ----------------------------------------------------------------------
    async def on_mount(self) -> None:  # noqa: D102
        assert self._github_session is None
        self._github_session = aiohttp.ClientSession(
            headers=GitHubSource.CreateGitHubHttpHeaders(self._github_pat)
        )

        for column in COLUMN_MAP.values():
            self._data_table.add_column(Text(column.name, justify=column.justify))  # ty: ignore[invalid-argument-type]

        await self._ResetAllRepositories()

    # ----------------------------------------------------------------------
    async def on_unmount(self) -> None:  # noqa: D102
        # Close the shared session when the app exits
        if self._github_session is not None:
            await self._github_session.close()
            self._github_session = None

    # ----------------------------------------------------------------------
    async def on_data_table_cell_highlighted(self, message: DataTable.ColumnSelected) -> None:  # noqa: ARG002, D102
        await self._OnSelectionChanged()

    # ----------------------------------------------------------------------
    async def action_RefreshAll(self) -> None:  # noqa: D102
        await self._ResetAllRepositories()

    # ----------------------------------------------------------------------
    async def action_RefreshSelected(self) -> None:  # noqa: D102
        assert self._repositories is not None

        await self._ResetRepository(
            self._repositories[self._data_table.cursor_coordinate.row],
            self._data_table.cursor_coordinate.row,
        )

    # ----------------------------------------------------------------------
    async def action_PullSelected(self) -> None:  # noqa: D102
        assert self._repositories is not None

        repository = self._repositories[self._data_table.cursor_coordinate.row]

        await LocalGitSource.Pull(repository)
        await self._ResetRepository(repository, self._data_table.cursor_coordinate.row)

    # ----------------------------------------------------------------------
    async def action_PushSelected(self) -> None:  # noqa: D102
        assert self._repositories is not None

        repository = self._repositories[self._data_table.cursor_coordinate.row]

        await LocalGitSource.Push(repository)
        await self._ResetRepository(repository, self._data_table.cursor_coordinate.row)

    # ----------------------------------------------------------------------
    def key_1(self) -> None:  # noqa: D102
        self._data_table.focus()

    # ----------------------------------------------------------------------
    def key_2(self) -> None:  # noqa: D102
        self._additional_info.focus()

    # ----------------------------------------------------------------------
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  # noqa: ARG002, D102
        if action == "RefreshAll":
            if self._repositories is not None:
                return True

            return None

        if action == "RefreshSelected":
            if self._repositories is not None:
                return True

            return None

        if action == "PullSelected":
            if self._repositories is not None:
                state_data = self._state_data.get(self._data_table.cursor_coordinate.row, {}).get(
                    RemoteColumn.value, {}
                )

                if state_data and state_data["has_remote_changes"]:  # ty: ignore[not-subscriptable]
                    return True

            return None

        if action == "PushSelected":
            if self._repositories is not None:
                state_data = self._state_data.get(self._data_table.cursor_coordinate.row, {}).get(
                    RemoteColumn.value, {}
                )

                if state_data and state_data["has_local_changes"]:  # ty: ignore[not-subscriptable]
                    return True

            return None

        return True

    # ----------------------------------------------------------------------
    # |
    # |  Private Methods
    # |
    # ----------------------------------------------------------------------
    async def _ResetAllRepositories(self) -> None:
        self._repositories = None
        self._additional_info_data.clear()
        self._state_data.clear()
        self._data_table.clear()
        await self._OnSelectionChanged(repopulate_changes=False)

        # Get the repositories

        # ----------------------------------------------------------------------
        async def OnRepositoriesComplete(repositories: list[Repository] | None) -> None:
            if repositories is None:
                return

            assert self._repositories is None
            self._repositories = repositories

            for repository_index, repository in enumerate(repositories):
                self._data_table.add_row()

                await self._ResetRepository(repository, repository_index)

        # ----------------------------------------------------------------------

        self.push_screen(_GetRepositoriesModal(self._working_dir), OnRepositoriesComplete)

    # ----------------------------------------------------------------------
    async def _ResetRepository(self, repository: Repository, repository_index: int) -> None:
        self._additional_info_data.pop(repository_index, None)
        self._state_data.pop(repository_index, None)

        for column in COLUMN_MAP.values():
            self._data_table.update_cell_at(
                Coordinate(repository_index, column.value),
                "",
            )

        if repository_index == self._data_table.cursor_coordinate.row:
            self._RefreshBindings()

        # Create the repo name
        if repository.path == self._working_dir:
            repo_name = repository.path.name
        else:
            repo_name = str(repository.path.relative_to(self._working_dir))

        self._data_table.update_cell_at(
            Coordinate(repository_index, NameColumn.value),
            Text(f"📂 {repo_name}", justify=NameColumn.justify),  # ty: ignore[invalid-argument-type]
            update_width=True,
        )

        self._additional_info_data.setdefault(repository_index, {})[NameColumn.value] = textwrap.dedent(
            f"""\
            Local:  {repository.path}
            Origin: {repository.remote_url or ""}
            """,
        )

        # Load the content

        # ----------------------------------------------------------------------
        async def LoadCells() -> None:
            assert self._github_session is not None

            for source in [
                LocalGitSource(),
                GitHubSource(self._github_session),
            ]:
                if not source.Applies(repository):
                    continue

                async for info in source.Query(repository):
                    self._PopulateCell(repository_index, info)

        # ----------------------------------------------------------------------

        self.run_worker(LoadCells())

    # ----------------------------------------------------------------------
    def _PopulateCell(self, repository_index: int, info: ResultInfo | ErrorInfo) -> None:
        column = COLUMN_MAP[info.key]

        if isinstance(info, ErrorInfo):
            display_value = "❌"
            additional_info = Traceback.from_exception(
                type(info.error),
                info.error,
                info.error.__traceback__ if self._debug else None,
            )

        elif isinstance(info, ResultInfo):
            display_value = info.display_value
            additional_info = info.additional_info

            if info.state_data is not None:
                self._state_data.setdefault(repository_index, {})[column.value] = info.state_data

                if repository_index == self._data_table.cursor_coordinate.row:
                    self._RefreshBindings()

        else:
            assert False, info  # noqa: B011, PT015  # pragma: no cover

        self._data_table.update_cell_at(
            Coordinate(repository_index, column.value),
            Text(display_value, justify=column.justify),  # ty: ignore[invalid-argument-type]
            update_width=True,
        )

        self._additional_info_data.setdefault(repository_index, {})[column.value] = additional_info

    # ----------------------------------------------------------------------
    async def _OnSelectionChanged(self, *, repopulate_changes: bool = True) -> None:
        self._additional_info.clear()
        self._RefreshBindings()

        if not repopulate_changes:
            return

        row_index = self._data_table.cursor_coordinate.row
        col_index = self._data_table.cursor_coordinate.column

        additional_info = self._additional_info_data.get(row_index, {}).get(col_index)

        if additional_info:
            self._additional_info.write(additional_info)

    # ----------------------------------------------------------------------
    def _RefreshBindings(self) -> None:
        # ScreenStackErrors are occasionally raised when testing
        with contextlib.suppress(ScreenStackError):
            self.refresh_bindings()


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
class _GetRepositoriesModal(ModalScreen[list[Repository]]):
    CSS = """
        #GetRepositoriesModal {
            background: $panel;
            padding: 1;
        }
    """

    # ----------------------------------------------------------------------
    def __init__(self, working_dir: Path, *args, **kwargs) -> None:
        self._working_dir = working_dir
        super().__init__(*args, **kwargs)

    # ----------------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Label(f"Searching for repositories in '{self._working_dir}'...", id="GetRepositoriesModal")

    # ----------------------------------------------------------------------
    async def on_mount(self) -> None:
        # ----------------------------------------------------------------------
        async def Execute() -> None:
            repos = [repository async for repository in EnumerateRepositories(self._working_dir)]
            self.dismiss(repos)

        # ----------------------------------------------------------------------

        self.run_worker(Execute())

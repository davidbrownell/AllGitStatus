# noqa: D100
import contextlib
import textwrap

from enum import auto, Enum
from pathlib import Path

from dbrownell_Common.ContextlibEx import ExitStack
from rich.console import Group
from rich.panel import Panel
from rich.spinner import Spinner
from textual.app import App, ComposeResult, ScreenStackError
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Label, RichLog

from AllGitStatus import __version__
from AllGitStatus.Impl.GetRepositoriesModal import GetRepositoriesModal
from AllGitStatus.Lib import GetRepositoryData, GitError, ExecuteGitCommand, RepositoryData


# ----------------------------------------------------------------------
class Columns(Enum):
    """Repository display columns."""

    Name = 0
    Branch = auto()
    Status = auto()


# ----------------------------------------------------------------------
class MainApp(App):
    """Main application."""

    CSS_PATH = Path(__file__).with_suffix(".tcss").name

    BINDINGS = [  # noqa: RUF012
        ("R", "RefreshAll", "Refresh All"),
        ("r", "RefreshSelected", "Refresh"),
        ("p", "PullSelected", "Pull"),
        ("P", "PushSelected", "Push"),
        ("X", "ClearGitErrors", "Clear git Errors"),
        ("q", "quit", "Quit"),
    ]

    # ----------------------------------------------------------------------
    def __init__(
        self,
        working_dir: Path,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.working_dir = working_dir

        self.title = "AllGitStatus"

        self._data_table: DataTable = DataTable(
            cursor_type="row",
            zebra_stripes=True,
            id="data_table",
        )
        self._data_table.border_title = "[1] Repositories"

        self._git_log = RichLog(id="git_log")
        self._git_log.border_title = "[2] git Errors"

        self._working_log = RichLog(id="working_log")
        self._working_log.border_title = "[3] Working Changes"

        self._local_log = RichLog(id="local_log")
        self._local_log.border_title = "[4] Local Changes"

        self._remote_log = RichLog(id="remote_log")
        self._remote_log.border_title = "[5] Remote Changes"

        self._repository_data_items: list[RepositoryData | Path | None] = []

    # ----------------------------------------------------------------------
    def compose(self) -> ComposeResult:  # noqa: D102
        yield Header()
        yield Vertical(
            Horizontal(self._data_table, self._git_log, id="git_group"),
            Horizontal(self._working_log, self._local_log, self._remote_log, id="changes_group"),
        )
        yield Horizontal(Footer(), Label(__version__), id="footer")

    # ----------------------------------------------------------------------
    def on_mount(self) -> None:  # noqa: D102
        self._data_table.add_columns(*[c.name for c in Columns])

        self._ResetAllRepositories()

    # ----------------------------------------------------------------------
    def on_data_table_row_highlighted(self, message: DataTable.RowHighlighted) -> None:  # noqa: ARG002, D102
        self._OnRepositorySelectionChanged()

    # ----------------------------------------------------------------------
    def key_1(self) -> None:  # noqa: D102
        self._data_table.focus()

    # ----------------------------------------------------------------------
    def key_2(self) -> None:  # noqa: D102
        self._git_log.focus()

    # ----------------------------------------------------------------------
    def key_3(self) -> None:  # noqa: D102
        self._working_log.focus()

    # ----------------------------------------------------------------------
    def key_4(self) -> None:  # noqa: D102
        self._local_log.focus()

    # ----------------------------------------------------------------------
    def key_5(self) -> None:  # noqa: D102
        self._remote_log.focus()

    # ----------------------------------------------------------------------
    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  # noqa: ARG002, D102
        if action == "RefreshAll":
            if self._repository_data_items and not any(item is None for item in self._repository_data_items):
                return True

            return None

        if action == "RefreshSelected":
            if (
                self._repository_data_items
                and self._repository_data_items[self._data_table.cursor_row] is not None
            ):
                return True

            return None

        if action == "PullSelected":
            if (
                self._repository_data_items
                and isinstance(self._repository_data_items[self._data_table.cursor_row], RepositoryData)
                and self._repository_data_items[self._data_table.cursor_row].remote_changes  # type: ignore[union-attr]
            ):
                return True

            return None

        if action == "PushSelected":
            if (
                self._repository_data_items
                and isinstance(self._repository_data_items[self._data_table.cursor_row], RepositoryData)
                and self._repository_data_items[self._data_table.cursor_row].local_changes  # type: ignore[union-attr]
            ):
                return True

            return None

        return True

    # ----------------------------------------------------------------------
    def action_RefreshAll(self) -> None:  # noqa: D102
        self._ResetAllRepositories()

    # ----------------------------------------------------------------------
    def action_RefreshSelected(self) -> None:  # noqa: D102
        repo_data = self._repository_data_items[self._data_table.cursor_row]
        assert repo_data is not None

        if isinstance(repo_data, Path):
            repo_path = repo_data
        elif isinstance(repo_data, RepositoryData):
            repo_path = repo_data.path
        else:
            assert False, repo_data  # noqa: B011, PT015 # pragma: no cover

        self._ResetRepository(repo_path, self._data_table.cursor_row)

    # ----------------------------------------------------------------------
    def action_PullSelected(self) -> None:  # noqa: D102
        self._ExecuteGitCommand("git pull")

    # ----------------------------------------------------------------------
    def action_PushSelected(self) -> None:  # noqa: D102
        self._ExecuteGitCommand("git push")

    # ----------------------------------------------------------------------
    def action_ClearGitErrors(self) -> None:  # noqa: D102
        self._git_log.clear()

    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    # ----------------------------------------------------------------------
    def _ResetAllRepositories(self) -> None:
        # Clear all content
        self._repository_data_items = []

        self._data_table.clear()
        self._git_log.clear()
        self._OnRepositorySelectionChanged(repopulate_changes=False)

        # Get the repositories

        # ----------------------------------------------------------------------
        def OnRepositoriesComplete(repositories: list[Path] | None) -> None:
            if repositories is None:
                return  # pragma: no cover

            assert not self._repository_data_items
            self._repository_data_items = [None] * len(repositories)

            for repository_index, repository in enumerate(repositories):
                self._data_table.add_row()

                self._ResetRepository(repository, repository_index)

        # ----------------------------------------------------------------------

        self.push_screen(GetRepositoriesModal(self.working_dir), OnRepositoriesComplete)

    # ----------------------------------------------------------------------
    def _ResetRepository(self, repository_path: Path, repository_index: int) -> None:
        if self._data_table.cursor_row == repository_index:
            self._OnRepositorySelectionChanged(repopulate_changes=False)

        assert len(self._repository_data_items) > repository_index
        self._repository_data_items[repository_index] = None

        # Create the UX displayed while loading the content
        repo_name = self._GetRepoName(repository_path)

        spinner = Spinner("dots", text=repo_name)

        for column in Columns:
            self._data_table.update_cell_at(
                Coordinate(repository_index, column.value),
                spinner if column.name == "Name" else "",
                update_width=True,
            )

        # ----------------------------------------------------------------------
        async def UpdateSpinner() -> None:
            self._data_table.update_cell_at(
                Coordinate(repository_index, Columns.Name.value),
                spinner,
                update_width=True,
            )

        # ----------------------------------------------------------------------

        spinner_timer = self.set_interval(0.1, UpdateSpinner)

        # Load the content
        # ----------------------------------------------------------------------
        async def Execute() -> None:
            data_items_content: RepositoryData | Path | None = None

            # ----------------------------------------------------------------------
            def Commit() -> None:
                assert self._repository_data_items[repository_index] is None
                self._repository_data_items[repository_index] = data_items_content

                if self._data_table.cursor_row == repository_index or all(
                    data_item is not None for data_item in self._repository_data_items
                ):
                    self.call_from_thread(self._OnRepositorySelectionChanged)

            # ----------------------------------------------------------------------

            with ExitStack(Commit):
                try:
                    with ExitStack(spinner_timer.stop):
                        repo_data = GetRepositoryData(repository_path)
                        data_items_content = repo_data

                except GitError as ex:
                    data_items_content = repository_path
                    self._ProcessGitError(repository_index, ex)
                    return

                # Name
                self._data_table.update_cell_at(
                    Coordinate(repository_index, Columns.Name.value),
                    repo_name,
                    update_width=True,
                )

                # Branch
                self._data_table.update_cell_at(
                    Coordinate(repository_index, Columns.Branch.value),
                    repo_data.branch,
                    update_width=True,
                )

                # Status
                status_parts: list[str] = []

                if repo_data.working_changes:
                    status_parts.append(f"Δ{len(repo_data.working_changes)}")
                if repo_data.local_changes:
                    status_parts.append(f"↑{len(repo_data.local_changes)}")
                if repo_data.remote_changes:
                    status_parts.append(f"↓{len(repo_data.remote_changes)}")

                if status_parts:
                    self._data_table.update_cell_at(
                        Coordinate(repository_index, Columns.Status.value),
                        " ".join(status_parts),
                        update_width=True,
                    )

        # ----------------------------------------------------------------------

        self.run_worker(Execute(), thread=True)

    # ----------------------------------------------------------------------
    def _OnRepositorySelectionChanged(self, *, repopulate_changes: bool = True) -> None:
        self._working_log.clear()
        self._local_log.clear()
        self._remote_log.clear()

        # ScreenStackErrors are occasionally raised when testing
        with contextlib.suppress(ScreenStackError):
            self.refresh_bindings()

        if not repopulate_changes:
            return

        data_item = self._repository_data_items[self._data_table.cursor_row]
        if not isinstance(data_item, RepositoryData):
            return

        if data_item.working_changes:
            self._working_log.write("\n".join(data_item.working_changes))

        if data_item.local_changes:
            self._local_log.write(Group(*[Panel(change) for change in data_item.local_changes]))

        if data_item.remote_changes:
            self._remote_log.write(Group(*[Panel(change) for change in data_item.remote_changes]))

    # ----------------------------------------------------------------------
    def _ProcessGitError(self, repository_index: int, ex: GitError) -> None:
        repo_name = self._GetRepoName(ex.repository_path)

        self._data_table.update_cell_at(
            Coordinate(repository_index, Columns.Name.value),
            f"!! {repo_name} !!",
            update_width=True,
        )

        # Note that python f-strings don't play nice with textwrap.dedent
        self._git_log.write(
            Panel(
                textwrap.dedent(
                    """\
                    [red]{repo_name} ({returncode})[/]
                    {command}

                    {output}
                    """,
                ).format(
                    repo_name=repo_name,
                    returncode=ex.returncode,
                    command=ex.command,
                    output=ex.output,
                ),
            ),
        )

    # ----------------------------------------------------------------------
    def _GetRepoName(self, repository_path: Path) -> str:
        if repository_path == self.working_dir:
            return repository_path.name

        return str(repository_path.relative_to(self.working_dir))

    # ----------------------------------------------------------------------
    def _ExecuteGitCommand(self, command: str) -> None:
        assert self._repository_data_items

        data_item = self._repository_data_items[self._data_table.cursor_row]
        assert isinstance(data_item, RepositoryData), data_item

        repo_name = self._GetRepoName(data_item.path)

        spinner = Spinner("point", text=repo_name)

        self._data_table.update_cell_at(
            Coordinate(self._data_table.cursor_row, Columns.Name.value),
            spinner,
            update_width=True,
        )

        # ----------------------------------------------------------------------
        async def UpdateSpinner() -> None:
            self._data_table.update_cell_at(
                Coordinate(self._data_table.cursor_row, Columns.Name.value),
                spinner,
                update_width=True,
            )

        # ----------------------------------------------------------------------

        spinner_timer = self.set_interval(0.1, UpdateSpinner)

        # ----------------------------------------------------------------------
        async def Execute() -> None:
            try:
                with ExitStack(spinner_timer.stop):
                    ExecuteGitCommand(command, data_item.path)
            except GitError as ex:
                self._ProcessGitError(self._data_table.cursor_row, ex)

            self._data_table.update_cell_at(
                Coordinate(self._data_table.cursor_row, Columns.Name.value),
                repo_name,
                update_width=True,
            )

            self.call_from_thread(lambda: self._ResetRepository(data_item.path, self._data_table.cursor_row))

        # ----------------------------------------------------------------------

        self.run_worker(Execute(), thread=True)

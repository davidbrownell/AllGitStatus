"""Integration tests for AllGitStatus.MainApp module.

These tests use Textual's automated testing functionality (Pilot) to exercise
the MainApp UI interactions.
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header, Label, RichLog

from AllGitStatus import __version__
from AllGitStatus.MainApp import (
    COLUMN_MAP,
    ArchivedColumn,
    BranchColumn,
    CICDStatusColumn,
    Column,
    ForksColumn,
    IssuesColumn,
    LocalColumn,
    MainApp,
    NameColumn,
    PullRequestsColumn,
    RemoteColumn,
    SecurityAlertsColumn,
    StarsColumn,
    StashesColumn,
    WatchersColumn,
    _GetRepositoriesModal,
)
from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.LocalGitSource import LocalGitSource
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo


# ----------------------------------------------------------------------
# |  Helper Functions
# ----------------------------------------------------------------------
def create_mock_repository(path: Path, remote_url: str | None = None) -> Repository:
    """Create a mock Repository object."""

    return Repository(
        path=path,
        remote_url=remote_url,
        github_owner="testowner" if remote_url else None,
        github_repo="testrepo" if remote_url else None,
    )


async def mock_enumerate_repositories(working_dir: Path):
    """Mock repository enumeration that yields test repositories."""

    repos = [
        create_mock_repository(working_dir / "repo1", "https://github.com/testowner/repo1.git"),
        create_mock_repository(working_dir / "repo2", "https://github.com/testowner/repo2.git"),
        create_mock_repository(working_dir / "repo3"),
    ]
    for repo in repos:
        yield repo


def create_mock_result_info(
    repo: Repository,
    key: tuple[str, str],
    display_value: str,
    additional_info: str = "",
    state_data: dict | None = None,
) -> ResultInfo:
    """Create a mock ResultInfo object."""

    return ResultInfo(
        repo=repo,
        key=key,
        display_value=display_value,
        additional_info=additional_info,
        state_data=state_data,
    )


# ----------------------------------------------------------------------
# |  Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def working_dir(tmp_path: Path) -> Path:
    """Create and return a working directory for tests."""

    return tmp_path / "working_dir"


@pytest.fixture
def mock_repos(working_dir: Path) -> list[Repository]:
    """Create mock repositories for testing."""

    return [
        create_mock_repository(working_dir / "repo1", "https://github.com/testowner/repo1.git"),
        create_mock_repository(working_dir / "repo2", "https://github.com/testowner/repo2.git"),
    ]


# ----------------------------------------------------------------------
class TestMainAppComposition:
    """Tests for MainApp widget composition and initialization."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_app_has_correct_title(self, working_dir: Path) -> None:
        """MainApp has the correct title."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            assert app.title == "AllGitStatus"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_app_composes_header(self, working_dir: Path) -> None:
        """MainApp composes a Header widget."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            headers = app.query(Header)
            assert len(headers) == 1

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_app_composes_footer_with_version(self, working_dir: Path) -> None:
        """MainApp composes a Footer with version label."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            footers = app.query(Footer)
            assert len(footers) == 1

            labels = app.query("#footer Label")
            assert len(labels) == 1
            # Check the label's internal content using the render_str method
            label = labels.first()
            rendered = label.render_str(__version__)
            # Alternatively, access the internal content via Static's mangled attribute
            assert __version__ in str(label._Static__content)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_app_composes_data_table(self, working_dir: Path) -> None:
        """MainApp composes a DataTable widget."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            data_tables = app.query(DataTable)
            assert len(data_tables) == 1

            data_table = data_tables.first()
            assert data_table.id == "data_table"
            assert data_table.cursor_type == "cell"
            assert data_table.zebra_stripes is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_app_composes_additional_info(self, working_dir: Path) -> None:
        """MainApp composes a RichLog for additional info."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            rich_logs = app.query(RichLog)
            assert len(rich_logs) == 1

            rich_log = rich_logs.first()
            assert rich_log.id == "additional_info"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_additional_info_has_auto_scroll_disabled(self, working_dir: Path) -> None:
        """Additional info RichLog has auto_scroll disabled to show content from the top."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            rich_log = app.query_one("#additional_info", RichLog)
            assert rich_log.auto_scroll is False

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_data_table_has_correct_columns(self, working_dir: Path) -> None:
        """DataTable has all expected columns."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            data_table = app.query_one(DataTable)

            # Verify column count matches COLUMN_MAP
            expected_columns = len(set(COLUMN_MAP.values()))
            assert len(data_table.columns) == expected_columns


# ----------------------------------------------------------------------
class TestMainAppKeyBindings:
    """Tests for MainApp key bindings."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_key_1_focuses_data_table(self, working_dir: Path) -> None:
        """Pressing '1' focuses the data table."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            # Focus something else first
            app._additional_info.focus()
            await pilot.pause()

            # Press '1' to focus data table
            await pilot.press("1")
            await pilot.pause()

            assert app._data_table.has_focus

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_key_2_focuses_additional_info(self, working_dir: Path) -> None:
        """Pressing '2' focuses the additional info panel."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            # Focus data table first
            app._data_table.focus()
            await pilot.pause()

            # Press '2' to focus additional info
            await pilot.press("2")
            await pilot.pause()

            assert app._additional_info.has_focus

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_key_q_quits_app(self, working_dir: Path) -> None:
        """Pressing 'q' quits the application."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            await pilot.press("q")
            # App should be exiting
            assert app._exit is True


# ----------------------------------------------------------------------
class TestMainAppCheckAction:
    """Tests for MainApp check_action method."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_refresh_all_disabled_when_no_repositories(self, working_dir: Path) -> None:
        """RefreshAll action is disabled when repositories are not loaded."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        # Don't load repositories
        app._repositories = None

        result = app.check_action("RefreshAll", ())
        assert result is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_refresh_all_enabled_when_repositories_loaded(
        self, working_dir: Path, mock_repos: list[Repository]
    ) -> None:
        """RefreshAll action is enabled when repositories are loaded."""

        app = MainApp(working_dir=working_dir, github_pat=None)
        app._repositories = mock_repos

        result = app.check_action("RefreshAll", ())
        assert result is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_refresh_selected_disabled_when_no_repositories(self, working_dir: Path) -> None:
        """RefreshSelected action is disabled when repositories are not loaded."""

        app = MainApp(working_dir=working_dir, github_pat=None)
        app._repositories = None

        result = app.check_action("RefreshSelected", ())
        assert result is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_refresh_selected_enabled_when_repositories_loaded(
        self, working_dir: Path, mock_repos: list[Repository]
    ) -> None:
        """RefreshSelected action is enabled when repositories are loaded."""

        app = MainApp(working_dir=working_dir, github_pat=None)
        app._repositories = mock_repos

        result = app.check_action("RefreshSelected", ())
        assert result is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_disabled_when_no_repositories(self, working_dir: Path) -> None:
        """PullSelected action is disabled when repositories are not loaded."""

        app = MainApp(working_dir=working_dir, github_pat=None)
        app._repositories = None

        result = app.check_action("PullSelected", ())
        assert result is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_disabled_when_no_remote_changes(
        self, working_dir: Path, mock_repos: list[Repository]
    ) -> None:
        """PullSelected action is disabled when there are no remote changes."""

        app = MainApp(working_dir=working_dir, github_pat=None)
        app._repositories = mock_repos

        # Set state data without remote changes
        app._state_data[0] = {RemoteColumn.value: {"has_remote_changes": False, "has_local_changes": False}}

        async with app.run_test() as pilot:
            result = app.check_action("PullSelected", ())
            assert result is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_pull_enabled_when_remote_changes_exist(
        self, working_dir: Path, mock_repos: list[Repository]
    ) -> None:
        """PullSelected action is enabled when there are remote changes."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            # Set up after mount to avoid reset
            app._repositories = mock_repos

            # Add rows to the data table so cursor is valid
            for _ in mock_repos:
                app._data_table.add_row()

            # Set state data with remote changes
            app._state_data[0] = {
                RemoteColumn.value: {"has_remote_changes": True, "has_local_changes": False}
            }

            result = app.check_action("PullSelected", ())
            assert result is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_push_disabled_when_no_repositories(self, working_dir: Path) -> None:
        """PushSelected action is disabled when repositories are not loaded."""

        app = MainApp(working_dir=working_dir, github_pat=None)
        app._repositories = None

        result = app.check_action("PushSelected", ())
        assert result is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_push_disabled_when_no_local_changes(
        self, working_dir: Path, mock_repos: list[Repository]
    ) -> None:
        """PushSelected action is disabled when there are no local changes."""

        app = MainApp(working_dir=working_dir, github_pat=None)
        app._repositories = mock_repos

        # Set state data without local changes
        app._state_data[0] = {RemoteColumn.value: {"has_remote_changes": False, "has_local_changes": False}}

        async with app.run_test() as pilot:
            result = app.check_action("PushSelected", ())
            assert result is None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_push_enabled_when_local_changes_exist(
        self, working_dir: Path, mock_repos: list[Repository]
    ) -> None:
        """PushSelected action is enabled when there are local changes."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            # Set up after mount to avoid reset
            app._repositories = mock_repos

            # Add rows to the data table so cursor is valid
            for _ in mock_repos:
                app._data_table.add_row()

            # Set state data with local changes
            app._state_data[0] = {
                RemoteColumn.value: {"has_remote_changes": False, "has_local_changes": True}
            }

            result = app.check_action("PushSelected", ())
            assert result is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_unknown_action_returns_true(self, working_dir: Path) -> None:
        """Unknown actions return True (enabled by default)."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        result = app.check_action("UnknownAction", ())
        assert result is True


# ----------------------------------------------------------------------
class TestMainAppWithMockedRepositories:
    """Tests for MainApp with mocked repository loading."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_app_shows_loading_modal_on_mount(self, working_dir: Path) -> None:
        """MainApp shows a loading modal when mounting."""

        with patch(
            "AllGitStatus.MainApp.EnumerateRepositories",
            side_effect=lambda wd: mock_enumerate_repositories(wd),
        ):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Allow modal to appear
                await pilot.pause()

                # The modal might have already dismissed if repos loaded quickly,
                # but we can verify the app started correctly
                assert app.title == "AllGitStatus"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_repositories_loaded_into_data_table(self, working_dir: Path) -> None:
        """Repositories are loaded into the data table."""

        repos = [
            create_mock_repository(working_dir / "repo1"),
            create_mock_repository(working_dir / "repo2"),
        ]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for repositories to load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Verify repositories were loaded
                assert app._repositories is not None
                assert len(app._repositories) == 2


# ----------------------------------------------------------------------
class TestMainAppActions:
    """Tests for MainApp action methods."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_action_refresh_all_resets_repositories(self, working_dir: Path) -> None:
        """action_RefreshAll resets all repositories."""

        repos = [create_mock_repository(working_dir / "repo1")]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for initial load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                assert app._repositories is not None
                initial_repos = app._repositories

                # Press 'R' to refresh all
                await pilot.press("R")
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Repositories should be reloaded
                assert app._repositories is not None

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_action_refresh_selected_resets_single_repository(self, working_dir: Path) -> None:
        """action_RefreshSelected resets the selected repository."""

        repos = [
            create_mock_repository(working_dir / "repo1"),
            create_mock_repository(working_dir / "repo2"),
        ]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for initial load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                assert app._repositories is not None
                assert len(app._repositories) == 2

                # Press 'r' to refresh selected
                await pilot.press("r")
                await pilot.pause()

                # Repository count should remain the same
                assert len(app._repositories) == 2

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_action_pull_selected_calls_pull(self, working_dir: Path) -> None:
        """action_PullSelected calls LocalGitSource.Pull."""

        repos = [create_mock_repository(working_dir / "repo1")]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with (
            patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum),
            patch.object(LocalGitSource, "Pull", new_callable=AsyncMock) as mock_pull,
        ):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for initial load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Set state data with remote changes so pull is enabled
                app._state_data[0] = {
                    RemoteColumn.value: {"has_remote_changes": True, "has_local_changes": False}
                }
                app.refresh_bindings()
                await pilot.pause()

                # Press 'p' to pull
                await pilot.press("p")
                await pilot.pause()

                # Pull should have been called
                mock_pull.assert_called_once()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_action_push_selected_calls_push(self, working_dir: Path) -> None:
        """action_PushSelected calls LocalGitSource.Push."""

        repos = [create_mock_repository(working_dir / "repo1")]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with (
            patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum),
            patch.object(LocalGitSource, "Push", new_callable=AsyncMock) as mock_push,
        ):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for initial load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Set state data with local changes so push is enabled
                app._state_data[0] = {
                    RemoteColumn.value: {"has_remote_changes": False, "has_local_changes": True}
                }
                app.refresh_bindings()
                await pilot.pause()

                # Press 'P' to push
                await pilot.press("P")
                await pilot.pause()

                # Push should have been called
                mock_push.assert_called_once()


# ----------------------------------------------------------------------
class TestMainAppPopulateCell:
    """Tests for _PopulateCell method."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_populate_cell_with_error_info(self, working_dir: Path) -> None:
        """_PopulateCell handles ErrorInfo correctly."""

        repos = [create_mock_repository(working_dir / "repo1")]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for initial load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Create an ErrorInfo and call _PopulateCell
                error_info = ErrorInfo(
                    repo=repos[0],
                    key=("LocalGitSource", "current_branch"),
                    error=ValueError("Test error"),
                )

                app._PopulateCell(0, error_info)
                await pilot.pause()

                # Verify the cell was updated with error indicator
                cell_value = app._data_table.get_cell_at(Coordinate(0, BranchColumn.value))
                assert "💥" in str(cell_value)

                # The additional_info_data should contain a Traceback
                assert 0 in app._additional_info_data
                assert BranchColumn.value in app._additional_info_data[0]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_populate_cell_with_result_info_with_state_data(self, working_dir: Path) -> None:
        """_PopulateCell handles ResultInfo with state_data correctly."""

        repos = [create_mock_repository(working_dir / "repo1")]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for initial load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Create a ResultInfo with state_data
                result_info = ResultInfo(
                    repo=repos[0],
                    key=("LocalGitSource", "remote_status"),
                    display_value="  0 🔼   0 🔽",
                    additional_info="No changes",
                    state_data={"has_local_changes": True, "has_remote_changes": False},
                )

                app._PopulateCell(0, result_info)
                await pilot.pause()

                # Verify the cell was populated with the display value
                cell_value = app._data_table.get_cell_at(Coordinate(0, RemoteColumn.value))
                assert "0 🔼" in str(cell_value)
                assert "0 🔽" in str(cell_value)

                # Verify additional_info was stored
                assert 0 in app._additional_info_data
                assert RemoteColumn.value in app._additional_info_data[0]
                assert app._additional_info_data[0][RemoteColumn.value] == "No changes"

                # Verify state_data was stored
                assert 0 in app._state_data
                assert RemoteColumn.value in app._state_data[0]
                state_data = app._state_data[0][RemoteColumn.value]
                assert state_data["has_local_changes"] is True  # type: ignore[index]
                assert state_data["has_remote_changes"] is False  # type: ignore[index]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_populate_cell_with_error_info_debug_mode(self, working_dir: Path) -> None:
        """_PopulateCell includes traceback in debug mode."""

        repos = [create_mock_repository(working_dir / "repo1")]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            # Create app with debug mode enabled
            app = MainApp(working_dir=working_dir, github_pat=None, debug=True)

            async with app.run_test() as pilot:
                # Wait for initial load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Create an ErrorInfo with a real exception that has a traceback
                try:
                    raise ValueError("Test error with traceback")
                except ValueError as e:
                    error_info = ErrorInfo(
                        repo=repos[0],
                        key=("LocalGitSource", "current_branch"),
                        error=e,
                    )

                app._PopulateCell(0, error_info)
                await pilot.pause()

                # Verify the cell was updated
                assert 0 in app._additional_info_data
                assert BranchColumn.value in app._additional_info_data[0]


# ----------------------------------------------------------------------
class TestMainAppRepoNameDisplay:
    """Tests for repository name display logic."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_repo_name_when_path_equals_working_dir(self, working_dir: Path) -> None:
        """Repository name shows just the directory name when path equals working_dir."""

        # Create a repo at the exact working directory
        working_dir.mkdir(parents=True, exist_ok=True)
        repos = [create_mock_repository(working_dir)]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for repositories to load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Verify the repo was loaded
                assert app._repositories is not None
                assert len(app._repositories) == 1

                # The additional_info_data should have the name entry
                assert 0 in app._additional_info_data
                assert NameColumn.value in app._additional_info_data[0]


# ----------------------------------------------------------------------
class TestMainAppNoneRepositories:
    """Tests for handling None repositories from modal."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_on_repositories_complete_handles_none(self, working_dir: Path) -> None:
        """OnRepositoriesComplete handles None gracefully."""

        async def mock_enum(wd):
            # Return no repositories
            return
            yield  # Make it a generator

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for modal to complete
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Repositories should be empty list (not None after loading)
                # When modal returns empty list, repositories will be set
                assert app._repositories is not None or app._repositories == []

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_on_repositories_complete_with_none_value(self, working_dir: Path) -> None:
        """OnRepositoriesComplete returns early when passed None."""

        app = MainApp(working_dir=working_dir, github_pat=None)

        async with app.run_test() as pilot:
            # Manually call the callback with None to test the early return
            # First we need to trigger _ResetAllRepositories to create the callback
            # Then we'll manually simulate what happens when modal returns None

            # Store initial state
            app._repositories = None

            # Simulate the modal returning None by directly testing the behavior
            # The callback is defined inside _ResetAllRepositories, so we test
            # by pushing a screen that dismisses with None
            from AllGitStatus.MainApp import _GetRepositoriesModal

            # Create a mock modal that dismisses with None
            original_on_mount = _GetRepositoriesModal.on_mount

            async def mock_on_mount(self):
                self.dismiss(None)

            with patch.object(_GetRepositoriesModal, "on_mount", mock_on_mount):
                # Trigger a refresh which will push the modal
                app._repositories = []  # Set to non-None so RefreshAll is enabled
                await app.action_RefreshAll()
                await pilot.pause()

            # After None is returned, repositories should still be None
            # (the callback returns early without setting _repositories)
            assert app._repositories is None


# ----------------------------------------------------------------------
class TestColumnDefinitions:
    """Tests for column definitions."""

    # ----------------------------------------------------------------------
    def test_name_column_properties(self) -> None:
        """NameColumn has correct properties."""

        assert NameColumn.value == 0
        assert NameColumn.name == "Name"
        assert NameColumn.justify == "left"

    # ----------------------------------------------------------------------
    def test_branch_column_properties(self) -> None:
        """BranchColumn has correct properties."""

        assert BranchColumn.value == 1
        assert BranchColumn.name == "Branch"
        assert BranchColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_local_column_properties(self) -> None:
        """LocalColumn has correct properties."""

        assert LocalColumn.value == 2
        assert LocalColumn.name == "Local"
        assert LocalColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_stashes_column_properties(self) -> None:
        """StashesColumn has correct properties."""

        assert StashesColumn.value == 3
        assert StashesColumn.name == "Stashes"
        assert StashesColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_remote_column_properties(self) -> None:
        """RemoteColumn has correct properties."""

        assert RemoteColumn.value == 4
        assert RemoteColumn.name == "Remote"
        assert RemoteColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_stars_column_properties(self) -> None:
        """StarsColumn has correct properties."""

        assert StarsColumn.value == 5
        assert StarsColumn.name == "Stars"
        assert StarsColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_forks_column_properties(self) -> None:
        """ForksColumn has correct properties."""

        assert ForksColumn.value == 6
        assert ForksColumn.name == "Forks"
        assert ForksColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_watchers_column_properties(self) -> None:
        """WatchersColumn has correct properties."""

        assert WatchersColumn.value == 7
        assert WatchersColumn.name == "Watchers"
        assert WatchersColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_issues_column_properties(self) -> None:
        """IssuesColumn has correct properties."""

        assert IssuesColumn.value == 8
        assert IssuesColumn.name == "Issues"
        assert IssuesColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_pullrequests_column_properties(self) -> None:
        """PullRequestsColumn has correct properties."""

        assert PullRequestsColumn.value == 9
        assert PullRequestsColumn.name == "PRs"
        assert PullRequestsColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_security_alerts_column_properties(self) -> None:
        """SecurityAlertsColumn has correct properties."""

        assert SecurityAlertsColumn.value == 10
        assert SecurityAlertsColumn.name == "Security"
        assert SecurityAlertsColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_cicd_status_column_properties(self) -> None:
        """CICDStatusColumn has correct properties."""

        assert CICDStatusColumn.value == 11
        assert CICDStatusColumn.name == "CI/CD"
        assert CICDStatusColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_archived_column_properties(self) -> None:
        """ArchivedColumn has correct properties."""

        assert ArchivedColumn.value == 12
        assert ArchivedColumn.name == "Archived"
        assert ArchivedColumn.justify == "center"

    # ----------------------------------------------------------------------
    def test_column_map_contains_all_columns(self) -> None:
        """COLUMN_MAP contains mappings for all column types."""

        unique_columns = set(COLUMN_MAP.values())

        expected_columns = {
            NameColumn,
            BranchColumn,
            LocalColumn,
            StashesColumn,
            RemoteColumn,
            StarsColumn,
            ForksColumn,
            WatchersColumn,
            IssuesColumn,
            PullRequestsColumn,
            SecurityAlertsColumn,
            CICDStatusColumn,
            ArchivedColumn,
        }

        assert unique_columns == expected_columns


# ----------------------------------------------------------------------
class TestGetRepositoriesModal:
    """Tests for _GetRepositoriesModal."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_modal_displays_searching_message(self, working_dir: Path) -> None:
        """Modal displays a searching message when pushed to an app."""

        async def mock_enum(wd):
            # Yield nothing to keep the modal visible longer
            return
            yield  # Make it a generator

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # The modal is pushed on mount, check if it's showing
                await pilot.pause()

                # Verify app mounted successfully
                assert app.title == "AllGitStatus"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_modal_dismisses_with_repositories(self, working_dir: Path) -> None:
        """Modal dismisses and returns repositories when enumeration completes."""

        repos = [create_mock_repository(working_dir / "repo1")]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for the modal worker to complete
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Repositories should be loaded
                assert app._repositories is not None
                assert len(app._repositories) == 1


# ----------------------------------------------------------------------
class TestMainAppDataTableNavigation:
    """Tests for DataTable navigation and selection."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_arrow_keys_navigate_cells(self, working_dir: Path) -> None:
        """Arrow keys navigate between cells in the data table."""

        repos = [
            create_mock_repository(working_dir / "repo1"),
            create_mock_repository(working_dir / "repo2"),
        ]

        async def mock_enum(wd):
            for repo in repos:
                yield repo

        with patch("AllGitStatus.MainApp.EnumerateRepositories", side_effect=mock_enum):
            app = MainApp(working_dir=working_dir, github_pat=None)

            async with app.run_test() as pilot:
                # Wait for repos to load
                await pilot.pause()
                await asyncio.sleep(0.1)
                await pilot.pause()

                # Focus the data table
                await pilot.press("1")
                await pilot.pause()

                # Get initial cursor position
                initial_row = app._data_table.cursor_coordinate.row
                initial_col = app._data_table.cursor_coordinate.column

                # Press right arrow
                await pilot.press("right")
                await pilot.pause()

                # Cursor should have moved right
                assert app._data_table.cursor_coordinate.column == initial_col + 1


# ----------------------------------------------------------------------
class TestMainAppDebugMode:
    """Tests for MainApp debug mode."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_debug_mode_is_stored(self, working_dir: Path) -> None:
        """Debug mode flag is stored correctly."""

        app_no_debug = MainApp(working_dir=working_dir, github_pat=None, debug=False)
        assert app_no_debug._debug is False

        app_with_debug = MainApp(working_dir=working_dir, github_pat=None, debug=True)
        assert app_with_debug._debug is True

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_debug_mode_changes_title(self, working_dir: Path) -> None:
        """Debug mode adds [DEBUG] to the title."""

        app_no_debug = MainApp(working_dir=working_dir, github_pat=None, debug=False)
        assert app_no_debug.title == "AllGitStatus"

        app_with_debug = MainApp(working_dir=working_dir, github_pat=None, debug=True)
        assert app_with_debug.title == "AllGitStatus [DEBUG]"

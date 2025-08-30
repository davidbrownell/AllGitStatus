# noqa: D100
from pathlib import Path

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Label

from AllGitStatus.Lib import GenerateRepos


# ----------------------------------------------------------------------
class GetRepositoriesModal(ModalScreen[list[Path]]):
    """Modal dialog displayed when getting a list of all repositories."""

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
    def compose(self) -> ComposeResult:  # noqa: D102
        yield Label(f"Searching for repositories in '{self._working_dir}'...", id="GetRepositoriesModal")

    # ----------------------------------------------------------------------
    async def on_mount(self) -> None:  # noqa: D102
        # ----------------------------------------------------------------------
        async def Execute() -> None:
            repos = list(GenerateRepos(self._working_dir))
            self.app.call_from_thread(lambda: self.dismiss(repos))

        # ----------------------------------------------------------------------

        self.run_worker(Execute(), thread=True)

# noqa: D100
from pathlib import Path
from typing import Annotated

import typer

from typer.core import TyperGroup

from AllGitStatus import __version__
from AllGitStatus.MainApp import MainApp


# ----------------------------------------------------------------------
class NaturalOrderGrouper(TyperGroup):  # noqa: D101
    # ----------------------------------------------------------------------
    def list_commands(self, *args, **kwargs) -> list[str]:  # noqa: ARG002, D102
        return list(self.commands.keys())  # pragma: no cover


# ----------------------------------------------------------------------
app = typer.Typer(
    cls=NaturalOrderGrouper,
    help=__doc__,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
)


# ----------------------------------------------------------------------
def _OnVersion(value: bool) -> None:  # noqa: FBT001
    if value:
        typer.echo(f"AllGitStatus v{__version__}")
        raise typer.Exit()


# ----------------------------------------------------------------------
@app.command("EntryPoint", no_args_is_help=False)
def EntryPoint(
    working_dir: Annotated[
        Path,
        typer.Argument(
            exists=True,
            resolve_path=True,
            file_okay=False,
            help="Working directory that contains one or more git repositories.",
        ),
    ] = Path.cwd(),  # noqa: B008
    pat_token_or_filename: Annotated[
        str | None,
        typer.Option(
            "--pat",
            envvar="ALLGITSTATUS_PAT",
            help="GitHub Personal Access Token (PAT) or filename that contains the PAT.",
        ),
    ] = None,
    version: Annotated[  # noqa: ARG001, FBT002
        bool,
        typer.Option(
            "--version",
            callback=_OnVersion,
            is_eager=True,
        ),
    ] = False,
    debug: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--debug", help="Write debug information to the terminal."),
    ] = False,
) -> None:
    """Display git status information for one or more git repositories under the specified directory."""

    max_filename_length = 1000

    if (
        pat_token_or_filename is not None
        and len(pat_token_or_filename) < max_filename_length
        and (pat_token_filename := Path(pat_token_or_filename)).is_file()
    ):
        pat_token_or_filename = pat_token_filename.read_text(encoding="utf-8").strip()

    MainApp(
        working_dir,
        pat_token_or_filename,
        debug=debug,
    ).run()


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()  # pragma: no cover

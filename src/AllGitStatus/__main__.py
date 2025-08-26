# noqa: D100
from pathlib import Path
from typing import Annotated

import typer

from typer.core import TyperGroup

from AllGitStatus.Impl.MainApp import MainApp


# ----------------------------------------------------------------------
class NaturalOrderGrouper(TyperGroup):  # noqa: D101
    # ----------------------------------------------------------------------
    def list_commands(self, *args, **kwargs) -> list[str]:  # noqa: ARG002, D102
        return list(self.commands.keys())


# ----------------------------------------------------------------------
app = typer.Typer(
    cls=NaturalOrderGrouper,
    help=__doc__,
    no_args_is_help=True,
    pretty_exceptions_show_locals=False,
    pretty_exceptions_enable=False,
)


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
) -> None:
    """Display git status information for one or more git repositories under the specified directory."""

    MainApp(working_dir).run()


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()

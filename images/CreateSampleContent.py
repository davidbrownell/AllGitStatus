# noqa: D100, INP001
import os
import shutil

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer

from dbrownell_Common.Streams.DoneManager import DoneManager, Flags as DoneManagerFlags
from dbrownell_Common import SubprocessEx

from typer.core import TyperGroup


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
@app.command("EntryPoint", no_args_is_help=True)
def EntryPoint(
    output_dir: Annotated[
        Path,
        typer.Argument(exists=False, file_okay=False, resolve_path=True, help="Output directory."),
    ],
    verbose: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--verbose", help="Write verbose information to the terminal."),
    ] = False,
    debug: Annotated[  # noqa: FBT002
        bool,
        typer.Option("--debug", help="Write debug information to the terminal."),
    ] = False,
) -> None:
    """Create repositories for sample content displayed in README.md."""

    with DoneManager.CreateCommandLine(
        flags=DoneManagerFlags.Create(verbose=verbose, debug=debug),
    ) as dm:
        if output_dir.is_dir():
            with dm.Nested(f"Removing '{output_dir}'..."):
                shutil.rmtree(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        # working changes (stage 1)
        with dm.Nested("Creating working changes (stage 1)...", suffix="\n") as this_dm:
            working_changes_dir = output_dir / "WorkingChanges"
            working_changes_dir.mkdir(parents=True)

            with _ChangeDir(working_changes_dir):
                _Execute(this_dm, "git init")
                _Execute(this_dm, 'git config user.name "Working Changes User"')
                _Execute(this_dm, 'git config user.email "working@Changes.com"')

                (working_changes_dir / "file1.txt").write_text("This is file 1.")
                (working_changes_dir / "file2.txt").write_text("This is file 2.")

                _Execute(this_dm, "git add file1.txt file2.txt")
                _Execute(this_dm, 'git commit -m "Initial commit."')

        # Local Changes
        with (
            dm.Nested("Creating local changes...", suffix="\n") as this_dm,
            _ChangeDir(output_dir),
        ):
            local_changes_dir = output_dir / "LocalChanges"

            _Execute(this_dm, f'git clone "{working_changes_dir}" {local_changes_dir.name}')

            with _ChangeDir(local_changes_dir):
                _Execute(this_dm, 'git config user.name "Local Changes User"')
                _Execute(this_dm, 'git config user.email "local@Changes.com"')

                (local_changes_dir / "fileA.txt").write_text("This is file A.")
                (local_changes_dir / "fileB.txt").write_text("This is file B.")

                _Execute(this_dm, "git add fileA.txt fileB.txt")
                _Execute(this_dm, 'git commit -m "Added files A and B."')

                (local_changes_dir / "fileC.txt").write_text("This is file C.")
                (local_changes_dir / "fileD.txt").write_text("This is file D.")

                _Execute(this_dm, "git add fileC.txt fileD.txt")
                _Execute(this_dm, 'git commit -m "Added files C and D."')

                (local_changes_dir / "fileE.txt").write_text("This is file E.")
                (local_changes_dir / "fileF.txt").write_text("This is file F.")

                _Execute(this_dm, "git add fileE.txt fileF.txt")
                _Execute(this_dm, 'git commit -m "Added files E and F."')

        # Remote Changes
        with (
            dm.Nested("Creating remote changes...", suffix="\n") as this_dm,
            _ChangeDir(output_dir),
        ):
            remote_changes_dir = output_dir / "RemoteChanges"

            _Execute(this_dm, f'git clone "{working_changes_dir}" {remote_changes_dir.name}')

        # Working changes (stage 2)
        with (
            dm.Nested("Creating working changes (stage 2)...", suffix="\n") as this_dm,
            _ChangeDir(working_changes_dir),
        ):
            (working_changes_dir / "file3.txt").write_text("This is file 3.")
            (working_changes_dir / "file4.txt").write_text("This is file 4.")

            _Execute(this_dm, "git add file3.txt file4.txt")
            _Execute(this_dm, 'git commit -m "Added files 3 and 4."')

            (working_changes_dir / "file5.txt").write_text("This is file 5.")
            _Execute(this_dm, "git add file5.txt")

            (working_changes_dir / "file6.txt").write_text("This is file 6.")


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
@contextmanager
def _ChangeDir(path: Path) -> Iterator[None]:
    original_dir = Path.cwd()
    os.chdir(path)

    try:
        yield
    finally:
        os.chdir(original_dir)


# ----------------------------------------------------------------------
def _Execute(dm: DoneManager, command_line: str) -> None:
    with (
        dm.Nested(f"Executing '{command_line}'...") as this_dm,
        this_dm.YieldStream() as stdout,
    ):
        this_dm.result = SubprocessEx.Stream(command_line, stdout)


# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app()

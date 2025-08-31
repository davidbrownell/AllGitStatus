from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from AllGitStatus import __version__
from AllGitStatus.__main__ import app


# ----------------------------------------------------------------------
def test_Version() -> None:
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output.strip() == f"AllGitStatus v{__version__}"


# ----------------------------------------------------------------------
def test_NoCommandLine() -> None:
    with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
        result = CliRunner().invoke(app, [])

        assert result.exit_code == 0

        assert len(mock_main_app.mock_calls) == 2

        assert tuple(mock_main_app.mock_calls[0]) == ("", (Path.cwd(),), {})
        assert tuple(mock_main_app.mock_calls[1]) == ("().run", (), {})


# ----------------------------------------------------------------------
def test_CommandLine() -> None:
    path_arg = Path(__file__).parent

    with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
        result = CliRunner().invoke(app, [str(path_arg)])

        assert result.exit_code == 0

        assert len(mock_main_app.mock_calls) == 2

        assert tuple(mock_main_app.mock_calls[0]) == ("", (path_arg,), {})
        assert tuple(mock_main_app.mock_calls[1]) == ("().run", (), {})

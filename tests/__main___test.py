"""Unit tests for AllGitStatus.__main__ module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from AllGitStatus.__main__ import EntryPoint, NaturalOrderGrouper, _OnVersion, app


# ----------------------------------------------------------------------
class TestNaturalOrderGrouper:
    """Tests for the NaturalOrderGrouper class."""

    # ----------------------------------------------------------------------
    def test_list_commands_returns_commands_in_order(self) -> None:
        """Commands are returned in the order they were added."""

        grouper = NaturalOrderGrouper()
        grouper.commands = {"first": MagicMock(), "second": MagicMock(), "third": MagicMock()}

        result = grouper.list_commands(None)

        assert result == ["first", "second", "third"]

    # ----------------------------------------------------------------------
    def test_list_commands_empty(self) -> None:
        """Empty command list returns empty list."""

        grouper = NaturalOrderGrouper()
        grouper.commands = {}

        result = grouper.list_commands(None)

        assert result == []


# ----------------------------------------------------------------------
class TestEntryPoint:
    """Tests for the EntryPoint command function."""

    # ----------------------------------------------------------------------
    def test_default_working_dir(self, tmp_path: Path) -> None:
        """MainApp is called with the provided working directory."""

        with (
            patch("AllGitStatus.__main__.MainApp") as mock_main_app,
            patch.object(Path, "cwd", return_value=tmp_path),
        ):
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path)

            mock_main_app.assert_called_once_with(tmp_path, None, debug=False)
            mock_instance.run.assert_called_once()

    # ----------------------------------------------------------------------
    def test_with_pat_token_direct(self, tmp_path: Path) -> None:
        """PAT token is passed directly when it's not a file path."""

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path, pat_token_or_filename="ghp_my_token_12345")

            mock_main_app.assert_called_once_with(tmp_path, "ghp_my_token_12345", debug=False)

    # ----------------------------------------------------------------------
    def test_with_pat_from_file(self, tmp_path: Path) -> None:
        """PAT token is read from file when path points to existing file."""

        pat_file = tmp_path / "pat_token.txt"
        pat_file.write_text("ghp_token_from_file\n", encoding="utf-8")

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path, pat_token_or_filename=str(pat_file))

            mock_main_app.assert_called_once_with(tmp_path, "ghp_token_from_file", debug=False)

    # ----------------------------------------------------------------------
    def test_with_pat_from_file_strips_whitespace(self, tmp_path: Path) -> None:
        """PAT token read from file has whitespace stripped."""

        pat_file = tmp_path / "pat_token.txt"
        pat_file.write_text("  ghp_token_with_spaces  \n\n", encoding="utf-8")

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path, pat_token_or_filename=str(pat_file))

            mock_main_app.assert_called_once_with(tmp_path, "ghp_token_with_spaces", debug=False)

    # ----------------------------------------------------------------------
    def test_with_pat_nonexistent_file_used_as_token(self, tmp_path: Path) -> None:
        """When PAT looks like a path but file doesn't exist, it's used as token."""

        nonexistent_path = str(tmp_path / "nonexistent.txt")

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path, pat_token_or_filename=nonexistent_path)

            mock_main_app.assert_called_once_with(tmp_path, nonexistent_path, debug=False)

    # ----------------------------------------------------------------------
    def test_with_debug_true(self, tmp_path: Path) -> None:
        """Debug flag is passed to MainApp."""

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path, debug=True)

            mock_main_app.assert_called_once_with(tmp_path, None, debug=True)
            mock_instance.run.assert_called_once()

    # ----------------------------------------------------------------------
    def test_with_none_pat(self, tmp_path: Path) -> None:
        """None PAT is passed through correctly."""

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path, pat_token_or_filename=None)

            mock_main_app.assert_called_once_with(tmp_path, None, debug=False)

    # ----------------------------------------------------------------------
    def test_very_long_string_not_treated_as_filename(self, tmp_path: Path) -> None:
        """Very long strings (>1000 chars) are not treated as filenames."""

        long_token = "x" * 1001

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path, pat_token_or_filename=long_token)

            # Should pass the long string directly without trying to read as file
            mock_main_app.assert_called_once_with(tmp_path, long_token, debug=False)

    # ----------------------------------------------------------------------
    def test_mainapp_run_is_called(self, tmp_path: Path) -> None:
        """MainApp.run() is called after instantiation."""

        with patch("AllGitStatus.__main__.MainApp") as mock_main_app:
            mock_instance = MagicMock()
            mock_main_app.return_value = mock_instance

            EntryPoint(working_dir=tmp_path)

            mock_instance.run.assert_called_once_with()


# ----------------------------------------------------------------------
class TestCliVersion:
    """Tests for --version flag via CLI invocation."""

    # ----------------------------------------------------------------------
    def test_version_flag_displays_version_and_exits(self) -> None:
        """--version flag displays version string and exits successfully."""

        runner = CliRunner()

        result = runner.invoke(app, ["--version"])

        assert result.exit_code == 0
        assert "AllGitStatus v" in result.output

    # ----------------------------------------------------------------------
    def test_version_flag_uses_on_version_callback(self) -> None:
        """--version flag invokes _OnVersion callback via typer.echo mock."""

        runner = CliRunner()

        with patch("AllGitStatus.__main__.typer.echo") as mock_echo:
            result = runner.invoke(app, ["--version"])

            assert result.exit_code == 0
            mock_echo.assert_called_once()
            call_arg = mock_echo.call_args[0][0]
            assert call_arg.startswith("AllGitStatus v")

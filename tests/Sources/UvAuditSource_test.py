"""Unit tests for AllGitStatus.Sources.UvAuditSource module."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo
from AllGitStatus.Sources.UvAuditSource import UvAuditSource


# ----------------------------------------------------------------------
# |  Fixtures
# ----------------------------------------------------------------------
@pytest.fixture
def repo(tmp_path: Path) -> Repository:
    """Create a Repository object for the test repository."""

    return Repository(path=tmp_path)


@pytest.fixture
def python_repo(tmp_path: Path) -> Repository:
    """Create a Repository with a pyproject.toml file."""

    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text('[project]\nname = "test"\nversion = "0.1.0"\n')
    return Repository(path=tmp_path)


# ----------------------------------------------------------------------
class TestUvAuditSourceNonPythonRepo:
    """Tests for non-Python repositories (no pyproject.toml)."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_dash_for_non_python_repo(self, repo: Repository) -> None:
        """Returns '-' display value when pyproject.toml is missing."""

        source = UvAuditSource()
        results = [info async for info in source.Query(repo)]

        assert len(results) == 1
        assert isinstance(results[0], ResultInfo)
        assert results[0].display_value == "-"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_additional_info_explains_non_python(self, repo: Repository) -> None:
        """Additional info explains why repo is not a Python repository."""

        source = UvAuditSource()
        results = [info async for info in source.Query(repo)]

        assert len(results) == 1
        assert isinstance(results[0], ResultInfo)
        assert results[0].additional_info == "Not a Python repository (no pyproject.toml found at root)"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_key_is_correct_for_non_python_repo(self, repo: Repository) -> None:
        """Key is correctly set for non-Python repositories."""

        source = UvAuditSource()
        results = [info async for info in source.Query(repo)]

        assert len(results) == 1
        assert results[0].key == ("UvAuditSource", "uv_audit")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_repo_reference_is_correct(self, repo: Repository) -> None:
        """Result references the correct repository."""

        source = UvAuditSource()
        results = [info async for info in source.Query(repo)]

        assert len(results) == 1
        assert results[0].repo is repo


# ----------------------------------------------------------------------
class TestUvAuditSourcePythonRepo:
    """Tests for Python repositories with pyproject.toml."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_checkmark_when_no_vulnerabilities(self, python_repo: Repository) -> None:
        """Returns checkmark when uv audit finds no vulnerabilities."""

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"No known vulnerabilities found", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process) as mock_exec:
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ResultInfo)
            assert results[0].display_value == "✅"
            assert results[0].additional_info == "No vulnerabilities found"

            # Verify uv audit was called correctly
            mock_exec.assert_called_once_with(
                "uv",
                "audit",
                cwd=str(python_repo.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_warning_when_vulnerabilities_found(self, python_repo: Repository) -> None:
        """Returns warning when uv audit finds vulnerabilities."""

        vulnerability_output = (
            b"Found 2 vulnerabilities\nCVE-2024-1234: some package\nCVE-2024-5678: another package"
        )
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(vulnerability_output, b""))
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ResultInfo)
            assert results[0].display_value == "\u26a0\ufe0f"  # warning
            assert "Found 2 vulnerabilities" in results[0].additional_info  # ty: ignore[unsupported-operator]

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_additional_info_contains_vulnerability_output(self, python_repo: Repository) -> None:
        """Additional info contains the uv audit output when vulnerabilities are found."""

        audit_output = b"Found 1 vulnerability\nCVE-2024-1234: some package"
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(audit_output, b""))
        mock_process.returncode = 1

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ResultInfo)
            assert results[0].additional_info == "Found 1 vulnerability\nCVE-2024-1234: some package"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_empty_output_shows_default_message(self, python_repo: Repository) -> None:
        """Empty output shows default 'No vulnerabilities found' message."""

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ResultInfo)
            assert results[0].additional_info == "No vulnerabilities found"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_key_is_correct_for_python_repo(self, python_repo: Repository) -> None:
        """Key is correctly set for Python repositories."""

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert results[0].key == ("UvAuditSource", "uv_audit")


# ----------------------------------------------------------------------
class TestUvAuditSourceErrorHandling:
    """Tests for error handling in UvAuditSource."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_error_info_when_uv_not_found(self, python_repo: Repository) -> None:
        """Returns ErrorInfo when uv command is not found."""

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=FileNotFoundError("uv not found"),
        ):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ErrorInfo)
            assert isinstance(results[0].error, FileNotFoundError)

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_error_info_when_exception_occurs(self, python_repo: Repository) -> None:
        """Returns ErrorInfo when an unexpected exception occurs."""

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=RuntimeError("Unexpected error"),
        ):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ErrorInfo)
            assert isinstance(results[0].error, RuntimeError)
            assert str(results[0].error) == "Unexpected error"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_error_info_has_correct_key(self, python_repo: Repository) -> None:
        """ErrorInfo has the correct key when an error occurs."""

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=Exception("test error"),
        ):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ErrorInfo)
            assert results[0].key == ("UvAuditSource", "uv_audit")

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_error_info_references_correct_repo(self, python_repo: Repository) -> None:
        """ErrorInfo references the correct repository."""

        with patch(
            "asyncio.create_subprocess_exec",
            side_effect=Exception("test error"),
        ):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1
            assert isinstance(results[0], ErrorInfo)
            assert results[0].repo is python_repo


# ----------------------------------------------------------------------
class TestUvAuditSourceQueryStructure:
    """Tests for overall Query structure and behavior."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_returns_exactly_one_result(self, python_repo: Repository) -> None:
        """Query returns exactly one result."""

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            assert len(results) == 1

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_all_keys_have_correct_class_name(self, python_repo: Repository) -> None:
        """All result keys have UvAuditSource as the class name."""

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = 0

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            source = UvAuditSource()
            results = [info async for info in source.Query(python_repo)]

            for result in results:
                assert result.key[0] == "UvAuditSource"

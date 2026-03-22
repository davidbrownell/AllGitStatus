"""Unit tests for AllGitStatus.Auth module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from AllGitStatus.Auth import CreateAuthenticatedSession


# ----------------------------------------------------------------------
class TestCreateAuthenticatedSession:
    """Tests for the CreateAuthenticatedSession async context manager."""

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_creates_session_without_token(self) -> None:
        """Session is created with correct base headers when no token is provided."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            async with CreateAuthenticatedSession() as session:
                assert session is mock_session

            mock_session_cls.assert_called_once()
            call_kwargs = mock_session_cls.call_args[1]

            assert "headers" in call_kwargs
            headers = call_kwargs["headers"]

            assert headers["Accept"] == "application/vnd.github+json"
            assert headers["X-GitHub-Api-Version"] == "2022-11-28"
            assert "Authorization" not in headers

            mock_session.close.assert_awaited_once()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_creates_session_with_none_token(self) -> None:
        """Session is created without Authorization header when token is explicitly None."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            async with CreateAuthenticatedSession(github_token=None) as session:
                assert session is mock_session

            call_kwargs = mock_session_cls.call_args[1]
            headers = call_kwargs["headers"]

            assert "Authorization" not in headers
            mock_session.close.assert_awaited_once()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_creates_session_with_empty_string_token(self) -> None:
        """Session is created without Authorization header when token is empty string."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            async with CreateAuthenticatedSession(github_token="") as session:
                assert session is mock_session

            call_kwargs = mock_session_cls.call_args[1]
            headers = call_kwargs["headers"]

            assert "Authorization" not in headers
            mock_session.close.assert_awaited_once()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_creates_session_with_token(self) -> None:
        """Session is created with Authorization header when token is provided."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            test_token = "ghp_test_token_12345"

            async with CreateAuthenticatedSession(github_token=test_token) as session:
                assert session is mock_session

            mock_session_cls.assert_called_once()
            call_kwargs = mock_session_cls.call_args[1]
            headers = call_kwargs["headers"]

            assert headers["Accept"] == "application/vnd.github+json"
            assert headers["X-GitHub-Api-Version"] == "2022-11-28"
            assert headers["Authorization"] == f"Bearer {test_token}"

            mock_session.close.assert_awaited_once()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_session_closed_on_normal_exit(self) -> None:
        """Session is properly closed when context exits normally."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            async with CreateAuthenticatedSession():
                pass

            mock_session.close.assert_awaited_once()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_session_closed_on_exception(self) -> None:
        """Session is properly closed even when exception occurs inside context."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            with pytest.raises(ValueError, match="test exception"):
                async with CreateAuthenticatedSession():
                    raise ValueError("test exception")

            mock_session.close.assert_awaited_once()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_yields_correct_session_instance(self) -> None:
        """Context manager yields the created session instance."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            async with CreateAuthenticatedSession(github_token="token") as session:
                assert session is mock_session_cls.return_value

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_headers_are_correct_github_api_headers(self) -> None:
        """Verify the exact GitHub API headers are set correctly."""

        with patch("AllGitStatus.Auth.aiohttp.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session.close = AsyncMock()
            mock_session_cls.return_value = mock_session

            async with CreateAuthenticatedSession(github_token="my_token"):
                pass

            call_kwargs = mock_session_cls.call_args[1]
            headers = call_kwargs["headers"]

            expected_headers = {
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Authorization": "Bearer my_token",
            }

            assert headers == expected_headers

# noqa: D100
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import aiohttp


# ----------------------------------------------------------------------
@asynccontextmanager
async def CreateAuthenticatedSession(
    github_token: str | None = None,
) -> AsyncIterator[aiohttp.ClientSession]:
    """Create an authenticated aiohttp session for GitHub API access.

    Usage:
        async with CreateAuthenticatedSession(token) as session:
            async with session.get(url) as response:
                data = await response.json()
    """

    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if github_token:
        headers["Authorization"] = f"Bearer {github_token}"

    session = aiohttp.ClientSession(headers=headers)

    try:
        yield session
    finally:
        await session.close()

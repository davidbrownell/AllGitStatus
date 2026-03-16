# noqa: D100
import asyncio
import os
import re

from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path


# ----------------------------------------------------------------------
# |
# |  Public Types
# |
# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Repository:
    """Represents a local git repository."""

    # ----------------------------------------------------------------------
    path: Path
    remote_url: str | None = None
    github_owner: str | None = None
    github_repo: str | None = None

    # ----------------------------------------------------------------------
    @classmethod
    async def FromDirectory(cls, path: Path) -> "Repository":
        """Create a Repository object from a local directory containing a git repository."""

        remote_url: str | None = None
        github_owner: str | None = None
        github_repo: str | None = None

        # Get the remote url (if possible)
        try:
            proc = await asyncio.create_subprocess_exec(
                "git",
                "-C",
                str(path),
                "remote",
                "get-url",
                "origin",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            content, _ = await proc.communicate()
            content = content.decode().strip()

            if proc.returncode == 0:
                remote_url = content

        except Exception:  # noqa: S110
            pass

        # Extract the owner and repo from the remote url
        if remote_url is not None:
            for pattern in [
                r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$",
                r"github\.com/([^/]+)/([^/]+?)/?$",
            ]:
                match = re.search(pattern, remote_url)
                if match is not None:
                    github_owner = match.group(1)
                    github_repo = match.group(2)

                    break

        return cls(path, remote_url, github_owner, github_repo)


# ----------------------------------------------------------------------
# |
# |  Public Functions
# |
# ----------------------------------------------------------------------
async def EnumerateRepositories(root_path: Path) -> AsyncGenerator[Repository]:
    """Recursively enumerate all git repositories under the specified root path."""

    if not root_path.is_dir():  # noqa: ASYNC240
        return

    for this_root_str, directories, _ in os.walk(root_path):
        this_root = Path(this_root_str)

        if ".git" in directories:
            yield await Repository.FromDirectory(this_root)

            # Do not spend any more time searching this directory and its descendants
            directories[:] = []

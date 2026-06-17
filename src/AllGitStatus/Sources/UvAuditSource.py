# noqa: D100
import asyncio

from collections.abc import AsyncGenerator

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo, Source


# ----------------------------------------------------------------------
class UvAuditSource(Source):
    """Source of information about Python dependency vulnerabilities via uv audit."""

    # ----------------------------------------------------------------------
    async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # noqa: D102  # ty: ignore[invalid-method-override]
        pyproject_path = repo.path / "pyproject.toml"

        key = (self.__class__.__name__, "uv_audit")

        if not pyproject_path.is_file():
            yield ResultInfo(
                repo,
                key,
                "-",
                "Not a Python repository (no pyproject.toml found at root)",
            )
            return

        try:
            proc = await asyncio.create_subprocess_exec(
                "uv",
                "audit",
                cwd=str(repo.path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            stdout, _ = await proc.communicate()
            output = stdout.decode().rstrip()

            if proc.returncode == 0:
                yield ResultInfo(
                    repo,
                    key,
                    "✅",
                    "No vulnerabilities found",
                )
            else:
                yield ResultInfo(
                    repo,
                    key,
                    "⚠️",
                    output,
                )
        except Exception as ex:
            yield ErrorInfo(repo, key, ex)

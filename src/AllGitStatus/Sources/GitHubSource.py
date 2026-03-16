# noqa: D100
from collections.abc import AsyncGenerator

import aiohttp

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.Source import ErrorInfo, ResultInfo, Source


# ----------------------------------------------------------------------
class GitHubSource(Source):
    """Source for GitHub repository information (stars, forks, issues, etc.)."""

    # ----------------------------------------------------------------------
    def __init__(
        self,
        session: aiohttp.ClientSession,
    ) -> None:
        self._session = session

    # ----------------------------------------------------------------------
    def Applies(self, repo: Repository) -> bool:  # noqa: D102
        return bool(repo.github_owner and repo.github_repo)

    # ----------------------------------------------------------------------
    async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # noqa: D102  # ty: ignore[invalid-method-override]
        assert self.Applies(repo)
        assert repo.remote_url is not None

        async with self._session.get(
            f"https://api.github.com/repos/{repo.github_owner}/{repo.github_repo}"
        ) as response:
            try:
                response.raise_for_status()
                result = await response.json()
            except Exception as ex:
                yield ErrorInfo(
                    repo,
                    (self.__class__.__name__, "stars"),
                    ex,
                )
                return

            github_url = repo.remote_url.removesuffix(".git")

            yield ResultInfo(
                repo,
                (self.__class__.__name__, "stars"),
                f"{result.get('stargazers_count', 0):5} ⭐",
                f"{github_url}/stargazers",
            )

            yield ResultInfo(
                repo,
                (self.__class__.__name__, "forks"),
                f"{result.get('forks_count', 0):5} 🍴",
                f"{github_url}/forks",
            )

            yield ResultInfo(
                repo,
                (self.__class__.__name__, "issues"),
                f"{result.get('open_issues_count', 0):5} 🐛",
                f"{github_url}/issues",
            )

            yield ResultInfo(
                repo,
                (self.__class__.__name__, "watchers"),
                f"{result.get('subscribers_count', 0):5} 👀",
                f"{github_url}/watchers",
            )

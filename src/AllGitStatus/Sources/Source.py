# noqa: D100
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field

from AllGitStatus.Repository import Repository


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class Info:
    """Represents a single piece of information about a repository."""

    repo: Repository
    key: tuple[
        str,  # Derived Info class name
        str | None,  # Unique identifier for this piece of information (e.g. "default_branch")
    ]


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ResultInfo(Info):
    """Represents a successful result from an information source."""

    display_value: str
    additional_info: object | None = field(default=None)
    state_data: object | None = field(kw_only=True, default=None)


# ----------------------------------------------------------------------
@dataclass(frozen=True)
class ErrorInfo(Info):
    """Represents an error that occurred while querying information."""

    error: Exception


# ----------------------------------------------------------------------
class Source(ABC):
    """Abstract base class for all sources of information about git repositories."""

    # ----------------------------------------------------------------------
    def Applies(self, repo: Repository) -> bool:  # noqa: ARG002
        """Determine if this source applies to the given repository."""
        return True

    # ----------------------------------------------------------------------
    @abstractmethod
    async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:
        """Generate information about a repository."""

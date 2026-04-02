"""Unit tests for AllGitStatus.Sources.Source module."""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest

from AllGitStatus.Repository import Repository
from AllGitStatus.Sources.Source import ErrorInfo, Info, ResultInfo, Source


# ----------------------------------------------------------------------
class TestInfo:
    """Tests for the Info dataclass."""

    # ----------------------------------------------------------------------
    def test_creation_with_required_fields(self) -> None:
        """Info is created with repo and key fields."""

        repo = Repository(path=Path("/test/repo"))
        key = ("ClassName", "identifier")

        info = Info(repo=repo, key=key)

        assert info.repo is repo
        assert info.key == ("ClassName", "identifier")

    # ----------------------------------------------------------------------
    def test_key_with_none_identifier(self) -> None:
        """Info key can have None as the identifier."""

        repo = Repository(path=Path("/test/repo"))
        key = ("ClassName", None)

        info = Info(repo=repo, key=key)

        assert info.key == ("ClassName", None)

    # ----------------------------------------------------------------------
    def test_frozen_dataclass(self) -> None:
        """Info dataclass is immutable (frozen)."""

        repo = Repository(path=Path("/test/repo"))
        info = Info(repo=repo, key=("Test", "id"))

        with pytest.raises(AttributeError):
            info.key = ("Other", "value")  # ty: ignore[invalid-assignment]


# ----------------------------------------------------------------------
class TestResultInfo:
    """Tests for the ResultInfo dataclass."""

    # ----------------------------------------------------------------------
    def test_creation_with_required_fields(self) -> None:
        """ResultInfo is created with required fields."""

        repo = Repository(path=Path("/test/repo"))

        result = ResultInfo(
            repo=repo,
            key=("ResultClass", "key"),
            display_value="test value",
        )

        assert result.repo is repo
        assert result.key == ("ResultClass", "key")
        assert result.display_value == "test value"
        assert result.additional_info is None
        assert result.state_data is None

    # ----------------------------------------------------------------------
    def test_creation_with_all_fields(self) -> None:
        """ResultInfo is created with all fields including optional ones."""

        repo = Repository(path=Path("/test/repo"))
        additional = {"extra": "data"}
        state = {"state": "info"}

        result = ResultInfo(
            repo=repo,
            key=("ResultClass", "key"),
            display_value="value",
            additional_info=additional,
            state_data=state,
        )

        assert result.additional_info == {"extra": "data"}
        assert result.state_data == {"state": "info"}

    # ----------------------------------------------------------------------
    def test_inherits_from_info(self) -> None:
        """ResultInfo inherits from Info."""

        repo = Repository(path=Path("/test/repo"))
        result = ResultInfo(repo=repo, key=("Test", None), display_value="x")

        assert isinstance(result, Info)

    # ----------------------------------------------------------------------
    def test_frozen_dataclass(self) -> None:
        """ResultInfo dataclass is immutable (frozen)."""

        repo = Repository(path=Path("/test/repo"))
        result = ResultInfo(repo=repo, key=("Test", "id"), display_value="value")

        with pytest.raises(AttributeError):
            result.display_value = "new value"  # ty: ignore[invalid-assignment]

    # ----------------------------------------------------------------------
    def test_state_data_is_keyword_only(self) -> None:
        """state_data must be passed as keyword argument."""

        repo = Repository(path=Path("/test/repo"))

        # This should work with keyword argument
        result = ResultInfo(
            repo=repo,
            key=("Test", "id"),
            display_value="value",
            additional_info=None,
            state_data="state",
        )

        assert result.state_data == "state"


# ----------------------------------------------------------------------
class TestErrorInfo:
    """Tests for the ErrorInfo dataclass."""

    # ----------------------------------------------------------------------
    def test_creation_with_exception(self) -> None:
        """ErrorInfo is created with an exception."""

        repo = Repository(path=Path("/test/repo"))
        error = ValueError("test error")

        error_info = ErrorInfo(repo=repo, key=("ErrorClass", "key"), error=error)

        assert error_info.repo is repo
        assert error_info.key == ("ErrorClass", "key")
        assert error_info.error is error

    # ----------------------------------------------------------------------
    def test_inherits_from_info(self) -> None:
        """ErrorInfo inherits from Info."""

        repo = Repository(path=Path("/test/repo"))
        error_info = ErrorInfo(repo=repo, key=("Test", None), error=Exception())

        assert isinstance(error_info, Info)

    # ----------------------------------------------------------------------
    def test_frozen_dataclass(self) -> None:
        """ErrorInfo dataclass is immutable (frozen)."""

        repo = Repository(path=Path("/test/repo"))
        error_info = ErrorInfo(repo=repo, key=("Test", "id"), error=Exception())

        with pytest.raises(AttributeError):
            error_info.error = ValueError("new error")  # ty: ignore[invalid-assignment]

    # ----------------------------------------------------------------------
    def test_preserves_exception_details(self) -> None:
        """ErrorInfo preserves full exception details."""

        repo = Repository(path=Path("/test/repo"))

        try:
            raise RuntimeError("detailed error message")
        except RuntimeError as e:
            error_info = ErrorInfo(repo=repo, key=("Test", "id"), error=e)

        assert str(error_info.error) == "detailed error message"
        assert isinstance(error_info.error, RuntimeError)


# ----------------------------------------------------------------------
class TestSource:
    """Tests for the Source abstract base class."""

    # ----------------------------------------------------------------------
    def test_applies_returns_true_by_default(self) -> None:
        """Default Applies method returns True for any repository."""

        class ConcreteSource(Source):
            async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # ty: ignore[invalid-method-override]
                yield ResultInfo(repo=repo, key=("Test", None), display_value="x")

        repo = Repository(path=Path("/test/repo"))
        source = ConcreteSource()

        assert source.Applies(repo) is True

    # ----------------------------------------------------------------------
    def test_applies_returns_true_for_any_repo(self) -> None:
        """Default Applies method returns True regardless of repository properties."""

        class ConcreteSource(Source):
            async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # ty: ignore[invalid-method-override]
                yield ResultInfo(repo=repo, key=("Test", None), display_value="x")

        source = ConcreteSource()

        # Test with various repository configurations
        repo_minimal = Repository(path=Path("/minimal"))
        repo_github = Repository(
            path=Path("/github"),
            remote_url="https://github.com/owner/repo.git",
            github_owner="owner",
            github_repo="repo",
        )
        repo_no_remote = Repository(path=Path("/local"), remote_url=None)

        assert source.Applies(repo_minimal) is True
        assert source.Applies(repo_github) is True
        assert source.Applies(repo_no_remote) is True

    # ----------------------------------------------------------------------
    def test_is_abstract_base_class(self) -> None:
        """Source cannot be instantiated directly."""

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Source()

    # ----------------------------------------------------------------------
    def test_query_is_abstract_method(self) -> None:
        """Query method must be implemented by subclasses."""

        # This should fail because Query is not implemented
        class IncompleteSource(Source):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteSource()

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_concrete_source_can_yield_results(self) -> None:
        """Concrete source implementation can yield ResultInfo."""

        class ConcreteSource(Source):
            async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # ty: ignore[invalid-method-override]
                yield ResultInfo(repo=repo, key=("ConcreteSource", "test"), display_value="result")

        repo = Repository(path=Path("/test/repo"))
        source = ConcreteSource()

        results = [info async for info in source.Query(repo)]

        assert len(results) == 1
        assert isinstance(results[0], ResultInfo)
        assert results[0].display_value == "result"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_concrete_source_can_yield_errors(self) -> None:
        """Concrete source implementation can yield ErrorInfo."""

        class ConcreteSource(Source):
            async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # ty: ignore[invalid-method-override]
                yield ErrorInfo(repo=repo, key=("ConcreteSource", "error"), error=ValueError("fail"))

        repo = Repository(path=Path("/test/repo"))
        source = ConcreteSource()

        results = [info async for info in source.Query(repo)]

        assert len(results) == 1
        assert isinstance(results[0], ErrorInfo)
        assert str(results[0].error) == "fail"

    # ----------------------------------------------------------------------
    @pytest.mark.asyncio
    async def test_concrete_source_can_yield_multiple_items(self) -> None:
        """Concrete source implementation can yield multiple items."""

        class ConcreteSource(Source):
            async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # ty: ignore[invalid-method-override]
                yield ResultInfo(repo=repo, key=("ConcreteSource", "first"), display_value="one")
                yield ResultInfo(repo=repo, key=("ConcreteSource", "second"), display_value="two")
                yield ErrorInfo(repo=repo, key=("ConcreteSource", "error"), error=Exception("err"))

        repo = Repository(path=Path("/test/repo"))
        source = ConcreteSource()

        results = [info async for info in source.Query(repo)]

        assert len(results) == 3
        assert isinstance(results[0], ResultInfo)
        assert isinstance(results[1], ResultInfo)
        assert isinstance(results[2], ErrorInfo)

    # ----------------------------------------------------------------------
    def test_applies_can_be_overridden(self) -> None:
        """Subclasses can override Applies method."""

        class GitHubOnlySource(Source):
            def Applies(self, repo: Repository) -> bool:
                return repo.github_owner is not None

            async def Query(self, repo: Repository) -> AsyncGenerator[ResultInfo | ErrorInfo]:  # ty: ignore[invalid-method-override]
                yield ResultInfo(repo=repo, key=("Test", None), display_value="x")

        source = GitHubOnlySource()

        github_repo = Repository(
            path=Path("/github"),
            remote_url="https://github.com/owner/repo.git",
            github_owner="owner",
            github_repo="repo",
        )
        local_repo = Repository(path=Path("/local"))

        assert source.Applies(github_repo) is True
        assert source.Applies(local_repo) is False

from collections.abc import Callable, Set

import pytest

from app.core.project_types import StatementSource
from app.statement_extractors.registry import (
    allowed_content_types,
    allowed_file_extensions,
    get_extractor_fn,
)


@pytest.mark.parametrize("source", list(StatementSource))
def test_source_covered(source: StatementSource):
    assert isinstance(get_extractor_fn(source), Callable)
    assert isinstance(allowed_content_types(source), Set)
    assert isinstance(allowed_file_extensions(source), Set)


def test_no_extractor_fn():
    assert get_extractor_fn("random_value") is None


def no_alllowed_extensions():
    assert allowed_file_extensions("random_value") == []


def no_allowed_content_types():
    assert allowed_content_types("random_value") == []


def test_right_config_returned(monkeypatch):
    source = StatementSource.REVOLUT

    def extractor_fn():
        pass

    test_content_types = {"text/plain"}
    test_extensions = {".csv", ".pdf"}
    test_registry_config = {
        source: {
            "extractor_fn": extractor_fn,
            "allowed_extensions": test_extensions,
            "allowed_content_types": test_content_types,
        }
    }
    monkeypatch.setattr(
        "app.statement_extractors.registry._registry", test_registry_config
    )

    assert get_extractor_fn(source) == extractor_fn
    assert allowed_content_types(source) == test_content_types
    assert allowed_file_extensions(source) == test_extensions

from pathlib import Path

import pytest

from ainformer.config import load_sources
from ainformer.errors import ConfigurationError
from ainformer.types import AcquisitionMethod


def test_default_config_contains_all_registered_sources(config_path: Path) -> None:
    sources = load_sources(config_path)
    source_ids = {source.id for source in sources}
    assert "huggingface.papers" in source_ids
    assert "arxiv.ai" in source_ids
    assert "arxiv.ml" in source_ids
    assert "arxiv.nlp" in source_ids
    assert "arxiv.cv" in source_ids
    assert "openai.blog" in source_ids
    assert "openai.cookbook" in source_ids
    assert "openai.research" in source_ids
    assert "anthropic.blog" in source_ids
    assert "google.gemini_blog" in source_ids
    assert "qwen.blog" in source_ids
    assert "deeplearning.batch" in source_ids
    assert "deepseek.news" in source_ids
    assert "ollama.blog" in source_ids
    assert "ollama.library" in source_ids
    assert "juya.ai_daily" in source_ids
    assert "hackernews.best" in source_ids


def test_sectioned_sources_infer_method_and_defaults() -> None:
    config = Path("tests/fixtures/minimal_inline_sources.toml")
    sources = {source.id: source for source in load_sources(config)}

    rss_source = sources["demo.rss"]
    assert rss_source.name == "demo.rss"
    assert rss_source.description == "demo.rss"
    assert rss_source.selected_method == AcquisitionMethod.RSS
    assert rss_source.candidate_methods == [AcquisitionMethod.RSS]
    assert rss_source.rss is not None
    assert rss_source.rss.feed_url == "https://example.com/feed.xml"
    assert rss_source.rss.article_fetch_enabled is False

    api_source = sources["demo.api"]
    assert api_source.name == "Demo API"
    assert api_source.description == "Demo API"
    assert api_source.selected_method == AcquisitionMethod.API
    assert api_source.candidate_methods == [AcquisitionMethod.API]
    assert api_source.api is not None
    assert api_source.api.url == "https://example.com/api/posts"
    assert api_source.api.items_path == "$"


def test_unsupported_legacy_source_fields_fail_validation() -> None:
    config = Path("tests/fixtures/invalid_selected_method.toml")
    with pytest.raises(ConfigurationError):
        load_sources(config)


def test_duplicate_source_ids_fail_validation() -> None:
    config = Path("tests/fixtures/duplicate_sources.toml")
    with pytest.raises(ConfigurationError):
        load_sources(config)


def test_method_section_requires_required_config_fields() -> None:
    config = Path("tests/fixtures/missing_generic_config.toml")
    with pytest.raises(ConfigurationError):
        load_sources(config)

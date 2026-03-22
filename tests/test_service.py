import asyncio
from pathlib import Path

from ainformer.service import AInformerService
from ainformer.types import FetchRequest


def test_missing_source_is_rejected(service) -> None:
    result = asyncio.run(
        service.fetch(FetchRequest(source_ids=["missing.source"], limit=5, include_full_text=True))
    )

    assert not result.records
    assert result.errors[0].code == "source_not_found"


def test_fixture_fetch_returns_full_text_and_deduplicates(service) -> None:
    result = asyncio.run(
        service.fetch(FetchRequest(source_ids=["fixture.local_demo"], limit=10, include_full_text=True))
    )

    assert not result.errors
    assert result.total_records == 2
    assert result.deduped_records == 1
    first = result.records[0]
    assert first.source_id == "fixture.local_demo"
    assert first.content_complete is True
    assert first.content_text
    assert first.content_html


def test_fixture_fetch_without_full_text_omits_content(service) -> None:
    result = asyncio.run(
        service.fetch(FetchRequest(source_ids=["fixture.local_demo"], limit=10, include_full_text=False))
    )

    assert not result.errors
    assert result.records[0].content_text is None
    assert result.records[0].content_html is None
    assert result.records[0].content_complete is False


def test_excerpt_only_policy_omits_full_text_even_when_requested(tmp_path: Path) -> None:
    config = tmp_path / "sources.toml"
    config.write_text(
        """
        [fixture."fixture.excerpt_only"]
        name = "Fixture Excerpt Only"
        full_text_policy = "excerpt_only"
        """,
        encoding="utf-8",
    )
    service = AInformerService(config_path=config)

    result = asyncio.run(
        service.fetch(FetchRequest(source_ids=["fixture.excerpt_only"], limit=10, include_full_text=True))
    )

    assert not result.errors
    assert result.records[0].excerpt
    assert result.records[0].content_text is None
    assert result.records[0].content_html is None
    assert result.records[0].content_complete is False


def test_service_does_not_write_state_files() -> None:
    config = Path("tests/fixtures/fixture_only_sources.toml")
    service = AInformerService(config_path=config)
    before = sorted(path.name for path in Path.cwd().iterdir())
    first = asyncio.run(
        service.fetch(FetchRequest(source_ids=["fixture.local_demo"], limit=10, include_full_text=True))
    )
    second = asyncio.run(
        service.fetch(FetchRequest(source_ids=["fixture.local_demo"], limit=10, include_full_text=True))
    )
    after = sorted(path.name for path in Path.cwd().iterdir())

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert before == after

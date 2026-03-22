import pytest

from ainformer.sdk import AInformerClient
from ainformer.types import FetchRequest


def test_sdk_fetch_returns_fixture_records(fixture_config_path) -> None:
    client = AInformerClient(config_path=fixture_config_path)

    result = client.fetch(FetchRequest(source_ids=["fixture.local_demo"], limit=10, include_full_text=True))

    assert not result.errors
    assert result.total_records == 2
    assert result.deduped_records == 1


@pytest.mark.anyio
async def test_sdk_fetch_supports_running_event_loop(fixture_config_path) -> None:
    client = AInformerClient(config_path=fixture_config_path)

    result = client.fetch(FetchRequest(source_ids=["fixture.local_demo"], limit=10, include_full_text=False))

    assert not result.errors
    assert result.records[0].content_text is None


@pytest.mark.anyio
async def test_sdk_fetch_async_returns_fixture_records(fixture_config_path) -> None:
    client = AInformerClient(config_path=fixture_config_path)

    result = await client.fetch_async(
        FetchRequest(source_ids=["fixture.local_demo"], limit=10, include_full_text=True)
    )

    assert not result.errors
    assert result.total_records == 2

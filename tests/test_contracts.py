import asyncio

from ainformer.adapters import build_default_adapter_registry
from ainformer.types import FetchRequest


def test_fixture_adapter_contract(service) -> None:
    source = service.get_source("fixture.local_demo")
    adapter_registry = build_default_adapter_registry()
    adapters = adapter_registry.list_adapters()

    assert adapters, "Expected at least one adapter to be registered"
    for adapter in adapters:
        assert adapter.capabilities.stateless is True
        assert adapter.capabilities.supported_methods

    adapter = adapter_registry.get(source.adapter_key)
    items = asyncio.run(
        adapter.fetch_items(
            source,
            FetchRequest(source_ids=[source.id], limit=5, include_full_text=True),
        )
    )

    assert items
    assert items[0].title
    assert items[0].url
    assert items[0].raw_metadata

from __future__ import annotations

from pathlib import Path

from ainformer.config import load_sources
from ainformer.errors import SourceNotFoundError
from ainformer.types import SourceDefinition


class SourceRegistry:
    def __init__(self, sources: list[SourceDefinition]) -> None:
        self._sources = {source.id: source for source in sources}

    @classmethod
    def from_path(cls, path: Path | None = None) -> "SourceRegistry":
        return cls(load_sources(path))

    def list_sources(self) -> list[SourceDefinition]:
        return sorted(self._sources.values(), key=lambda source: source.id)

    def get_source(self, source_id: str) -> SourceDefinition:
        try:
            return self._sources[source_id]
        except KeyError as exc:
            raise SourceNotFoundError(f"Unknown source id: {source_id}") from exc


from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ainformer.errors import ConfigurationError
from ainformer.types import AcquisitionMethod, ApiSourceConfig, RssSourceConfig, ScrapeSourceConfig, SourceDefinition

_ALLOWED_TOP_LEVEL_KEYS = {"api", "rss", "scrape", "fixture", "version"}
_SOURCE_METADATA_FIELDS = {"name", "description", "enabled", "full_text_policy", "tags"}
_SECTION_MODELS = {
    "api": (AcquisitionMethod.API, "api", ApiSourceConfig),
    "rss": (AcquisitionMethod.RSS, "rss", RssSourceConfig),
    "scrape": (AcquisitionMethod.SCRAPE, "scrape", ScrapeSourceConfig),
}


def default_config_path() -> Path:
    configured = os.getenv("AINFORMER_SOURCES_CONFIG")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "config" / "sources.toml"


def _validate_top_level_payload(payload: dict[str, Any]) -> None:
    unknown_keys = sorted(key for key in payload if key not in _ALLOWED_TOP_LEVEL_KEYS)
    if unknown_keys:
        raise ConfigurationError(f"Unknown top-level config sections: {', '.join(unknown_keys)}")

    version = payload.get("version")
    if version is not None and not isinstance(version, int):
        raise ConfigurationError("Config key 'version' must be an integer")


def _metadata_payload(source_id: str, raw_source: dict[str, Any]) -> dict[str, Any]:
    name = raw_source.get("name", source_id)
    return {
        "id": source_id,
        "name": name,
        "description": raw_source.get("description", name),
        "enabled": raw_source.get("enabled", True),
        "full_text_policy": raw_source.get("full_text_policy", "prefer_full_text"),
        "tags": raw_source.get("tags", []),
    }


def _build_generic_source(section_name: str, source_id: str, raw_source: Any) -> SourceDefinition:
    if not isinstance(raw_source, dict):
        raise ConfigurationError(
            f"Section [{section_name}] must contain named source tables like "
            f'[{section_name}."source.id"]'
        )

    method, config_field, model = _SECTION_MODELS[section_name]
    allowed_fields = _SOURCE_METADATA_FIELDS | set(model.model_fields)
    unknown_fields = sorted(key for key in raw_source if key not in allowed_fields)
    if unknown_fields:
        raise ConfigurationError(
            f"Source {source_id} in [{section_name}] has unsupported fields: {', '.join(unknown_fields)}"
        )

    config_payload = {key: value for key, value in raw_source.items() if key in model.model_fields}
    source_payload = {
        **_metadata_payload(source_id, raw_source),
        "candidate_methods": [method.value],
        "selected_method": method.value,
        config_field: config_payload,
    }
    return SourceDefinition.model_validate(source_payload)


def _build_fixture_source(source_id: str, raw_source: Any) -> SourceDefinition:
    if not isinstance(raw_source, dict):
        raise ConfigurationError('Section [fixture] must contain named source tables like [fixture."source.id"]')

    unknown_fields = sorted(key for key in raw_source if key not in _SOURCE_METADATA_FIELDS)
    if unknown_fields:
        raise ConfigurationError(
            f"Source {source_id} in [fixture] has unsupported fields: {', '.join(unknown_fields)}"
        )

    source_payload = {
        **_metadata_payload(source_id, raw_source),
        "adapter_key": "fixture",
        "candidate_methods": [AcquisitionMethod.API.value],
        "selected_method": AcquisitionMethod.API.value,
    }
    return SourceDefinition.model_validate(source_payload)


def _load_section(payload: dict[str, Any], section_name: str) -> list[SourceDefinition]:
    section_payload = payload.get(section_name, {})
    if not isinstance(section_payload, dict):
        raise ConfigurationError(f"Top-level config section [{section_name}] must be a table")

    if section_name == "fixture":
        return [_build_fixture_source(source_id, raw_source) for source_id, raw_source in section_payload.items()]
    return [_build_generic_source(section_name, source_id, raw_source) for source_id, raw_source in section_payload.items()]


def load_sources(path: Path | None = None) -> list[SourceDefinition]:
    config_path = Path(path) if path else default_config_path()
    try:
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Source config file not found: {config_path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"Invalid TOML in source config: {config_path}") from exc

    _validate_top_level_payload(payload)

    try:
        sources: list[SourceDefinition] = []
        for section_name in ("fixture", "api", "rss", "scrape"):
            sources.extend(_load_section(payload, section_name))
    except ValidationError as exc:
        raise ConfigurationError(str(exc)) from exc

    seen_ids: set[str] = set()
    for source in sources:
        if source.id in seen_ids:
            raise ConfigurationError(f"Duplicate source id: {source.id}")
        seen_ids.add(source.id)

    return sources

from __future__ import annotations

import os
from pathlib import Path

from ainformer.adapters import AdapterRegistry, build_default_adapter_registry
from ainformer.errors import (
    AdapterMethodMismatchError,
    AdapterNotImplementedError,
    SourceDisabledError,
    SourceFetchError,
    SourceNotFoundError,
)
from ainformer.normalizer import normalize_raw_item
from ainformer.registry import SourceRegistry
from ainformer.types import FetchRequest, FetchResult, FullTextPolicy, SourceDefinition, SourceError, StandardizedRecord


def _find_dotenv(start_dir: Path) -> Path | None:
    for directory in (start_dir, *start_dir.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return candidate
    return None


def _dotenv_values(config_path: Path | None = None) -> dict[str, str]:
    search_roots: list[Path] = []
    if config_path is not None:
        search_roots.append(Path(config_path).resolve().parent)
    search_roots.append(Path.cwd().resolve())

    dotenv_path = None
    seen: set[Path] = set()
    for root in search_roots:
        if root in seen:
            continue
        seen.add(root)
        dotenv_path = _find_dotenv(root)
        if dotenv_path is not None:
            break

    if dotenv_path is None:
        return {}

    values: dict[str, str] = {}
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        if not key:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def _runtime_env(config_path: Path | None = None) -> dict[str, str]:
    env = _dotenv_values(config_path)
    env.update(os.environ)
    return env


class AInformerService:
    def __init__(
        self,
        *,
        config_path: Path | None = None,
        registry: SourceRegistry | None = None,
        adapter_registry: AdapterRegistry | None = None,
    ) -> None:
        self._env = _runtime_env(config_path)
        self._registry = registry or SourceRegistry.from_path(config_path)
        self._adapter_registry = adapter_registry or build_default_adapter_registry(env=self._env)

    def list_sources(self) -> list[SourceDefinition]:
        return self._registry.list_sources()

    def get_source(self, source_id: str) -> SourceDefinition:
        return self._registry.get_source(source_id)

    async def fetch(self, request: FetchRequest) -> FetchResult:
        errors: list[SourceError] = []
        records: list[StandardizedRecord] = []
        dedupe_keys: set[tuple[str, str]] = set()
        deduped_records = 0

        for source_id in request.source_ids:
            try:
                source = self._registry.get_source(source_id)
                self._ensure_source_fetchable(source)
                adapter = self._adapter_registry.get(source.adapter_key)
                if not adapter.supports_method(source.selected_method):
                    raise AdapterMethodMismatchError(
                        f"Source {source.id} selected method {source.selected_method} is not supported"
                    )

                effective_request = self._effective_request(source, request)
                raw_items = await adapter.fetch_items(source, effective_request)
                for item in raw_items[: effective_request.limit]:
                    record = normalize_raw_item(
                        source=source,
                        item=item,
                        include_full_text=effective_request.include_full_text,
                    )
                    dedupe_seed = record.canonical_url or record.external_id or record.url
                    dedupe_key = (record.source_id, dedupe_seed)
                    if dedupe_key in dedupe_keys:
                        deduped_records += 1
                        continue
                    dedupe_keys.add(dedupe_key)
                    records.append(record)
            except SourceNotFoundError as exc:
                errors.append(self._to_error(source_id, "source_not_found", str(exc)))
            except SourceDisabledError as exc:
                errors.append(self._to_error(source_id, "source_disabled", str(exc)))
            except AdapterMethodMismatchError as exc:
                errors.append(self._to_error(source_id, "adapter_method_mismatch", str(exc)))
            except AdapterNotImplementedError as exc:
                errors.append(self._to_error(source_id, "adapter_not_implemented", str(exc)))
            except SourceFetchError as exc:
                errors.append(self._to_error(source_id, "fetch_failed", str(exc)))

        return FetchResult(
            request=request,
            records=records,
            errors=errors,
            total_records=len(records),
            deduped_records=deduped_records,
        )

    def _ensure_source_fetchable(self, source: SourceDefinition) -> None:
        if not source.enabled:
            raise SourceDisabledError(f"Source {source.id} is disabled")

    @staticmethod
    def _effective_request(source: SourceDefinition, request: FetchRequest) -> FetchRequest:
        if source.full_text_policy == FullTextPolicy.EXCERPT_ONLY and request.include_full_text:
            return request.model_copy(update={"include_full_text": False})
        return request

    @staticmethod
    def _to_error(source_id: str, code: str, message: str) -> SourceError:
        return SourceError(source_id=source_id, code=code, message=message, retryable=False)

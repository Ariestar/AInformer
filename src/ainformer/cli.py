from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import typer

from ainformer.errors import SourceNotFoundError
from ainformer.service import AInformerService
from ainformer.types import FetchRequest


def _configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


_configure_stdio()

app = typer.Typer(help="Unified AI information ingestion foundation.")
sources_app = typer.Typer(help="Inspect configured sources.")
app.add_typer(sources_app, name="sources")


def _service(config: Path | None) -> AInformerService:
    return AInformerService(config_path=config)


def _dump(payload: object) -> None:
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


def _raw_payload(record_payload: dict) -> object:
    raw_metadata = record_payload.get("raw_metadata", {})
    return raw_metadata.get("source_payload", raw_metadata)


def _fetch_payload(
    *,
    service: AInformerService,
    source_ids: list[str],
    limit: int,
    include_full_text: bool,
    raw: bool,
) -> tuple[dict, bool]:
    request = FetchRequest(source_ids=source_ids, limit=limit, include_full_text=include_full_text)
    result = asyncio.run(service.fetch(request))
    payload = result.model_dump(mode="json")
    if raw:
        payload = {
            "request": payload["request"],
            "errors": payload["errors"],
            "total_records": payload["total_records"],
            "deduped_records": payload["deduped_records"],
            "raw_records": [_raw_payload(record) for record in payload["records"]],
        }
    return payload, bool(result.errors and not result.records)


@sources_app.command("list")
def list_sources(config: Path | None = typer.Option(default=None, exists=True, dir_okay=False)) -> None:
    service = _service(config)
    _dump([source.model_dump(mode="json") for source in service.list_sources()])


@sources_app.command("show")
def show_source(
    source_id: str,
    config: Path | None = typer.Option(default=None, exists=True, dir_okay=False),
) -> None:
    service = _service(config)
    try:
        source = service.get_source(source_id)
    except SourceNotFoundError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    _dump(source.model_dump(mode="json"))


@app.command("fetch")
def fetch(
    source_id: list[str] = typer.Option(..., "--source-id", help="Source id to fetch. Repeat for multiple sources."),
    limit: int = typer.Option(10, min=1, max=100),
    include_full_text: bool = typer.Option(True, "--include-full-text/--no-include-full-text"),
    raw: bool = typer.Option(False, "--raw", help="Print provider raw payloads instead of normalized records."),
    config: Path | None = typer.Option(default=None, exists=True, dir_okay=False),
) -> None:
    service = _service(config)
    payload, should_fail = _fetch_payload(
        service=service,
        source_ids=source_id,
        limit=limit,
        include_full_text=include_full_text,
        raw=raw,
    )
    _dump(payload)
    if should_fail:
        raise typer.Exit(code=1)


@app.command("fetch-all")
def fetch_all(
    limit: int = typer.Option(10, min=1, max=100),
    include_full_text: bool = typer.Option(True, "--include-full-text/--no-include-full-text"),
    raw: bool = typer.Option(False, "--raw", help="Print provider raw payloads instead of normalized records."),
    config: Path | None = typer.Option(default=None, exists=True, dir_okay=False),
) -> None:
    service = _service(config)
    source_ids = [source.id for source in service.list_sources()]
    payload, should_fail = _fetch_payload(
        service=service,
        source_ids=source_ids,
        limit=limit,
        include_full_text=include_full_text,
        raw=raw,
    )
    _dump(payload)
    if should_fail:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse

from ainformer.dashboard import dashboard_html
from ainformer.errors import SourceNotFoundError
from ainformer.service import AInformerService
from ainformer.types import FetchRequest, FetchResult, SourceDefinition


def create_app(config_path: Path | None = None) -> FastAPI:
    service = AInformerService(config_path=config_path)
    app = FastAPI(title="AInformer", version="0.1.0")
    app.state.service = service

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    @app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(dashboard_html())

    @app.get("/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/sources", response_model=list[SourceDefinition])
    async def list_sources() -> list[SourceDefinition]:
        return service.list_sources()

    @app.get("/v1/sources/{source_id}", response_model=SourceDefinition)
    async def get_source(source_id: str) -> SourceDefinition:
        try:
            return service.get_source(source_id)
        except SourceNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/v1/fetch", response_model=FetchResult)
    async def fetch(request: FetchRequest) -> FetchResult | JSONResponse:
        result = await service.fetch(request)
        if result.errors and not result.records:
            return JSONResponse(status_code=400, content=result.model_dump(mode="json"))
        return result

    return app

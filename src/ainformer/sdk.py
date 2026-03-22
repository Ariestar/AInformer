from __future__ import annotations

import asyncio
from pathlib import Path
from threading import Thread

from ainformer.service import AInformerService
from ainformer.types import FetchRequest, FetchResult, SourceDefinition


class AInformerClient:
    def __init__(self, config_path: Path | None = None) -> None:
        self._service = AInformerService(config_path=config_path)

    def list_sources(self) -> list[SourceDefinition]:
        return self._service.list_sources()

    def get_source(self, source_id: str) -> SourceDefinition:
        return self._service.get_source(source_id)

    def fetch(self, request: FetchRequest) -> FetchResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.fetch_async(request))
        return self._fetch_in_worker_thread(request)

    async def fetch_async(self, request: FetchRequest) -> FetchResult:
        return await self._service.fetch(request)

    def _fetch_in_worker_thread(self, request: FetchRequest) -> FetchResult:
        result: FetchResult | None = None
        error: BaseException | None = None

        def runner() -> None:
            nonlocal result, error
            try:
                result = asyncio.run(self.fetch_async(request))
            except BaseException as exc:  # pragma: no cover - exercised via raised exception
                error = exc

        # asyncio.run() cannot reuse an active loop, so the sync API falls back to a worker thread.
        thread = Thread(target=runner, daemon=True)
        thread.start()
        thread.join()

        if error is not None:
            raise error
        if result is None:
            raise RuntimeError("AInformerClient.fetch() did not produce a result.")
        return result

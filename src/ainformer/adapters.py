from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from email.utils import parsedate_to_datetime
from importlib import resources
from typing import Any, Mapping
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

import httpx
from bs4 import BeautifulSoup, Tag

from ainformer.errors import AdapterNotImplementedError, SourceFetchError
from ainformer.types import (
    AcquisitionMethod,
    AdapterCapabilities,
    ApiSourceConfig,
    FetchRequest,
    RawSourceItem,
    RssSourceConfig,
    ScrapeSourceConfig,
    SourceDefinition,
)

DEFAULT_RSSHUB_BASE_URL = "http://rsshub:1200"
DEFAULT_RSS_HEADERS = {
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/134.0.0.0 Safari/537.36"
    ),
}


def _tag_name(value: str) -> str:
    return value.rsplit("}", 1)[-1]


def _path_get(payload: Any, path: str | None) -> Any:
    if not path:
        return None
    if path in {"$", "@root", "__root__", "root"}:
        return payload

    current = payload
    for part in path.split("."):
        if current is None:
            return None
        if isinstance(current, dict):
            current = current.get(part)
            continue
        if isinstance(current, list):
            try:
                current = current[int(part)]
            except (ValueError, IndexError):
                return None
            continue
        return None
    return current


def _stringify(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    text = str(value).strip()
    return text or None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_string_list(item))
        return result
    if isinstance(value, dict):
        if "name" in value:
            return _string_list(value["name"])
        return []
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
        return [part for part in parts if part]
    text = _stringify(value)
    return [text] if text else []


def _absolute_url(base_url: str, maybe_relative: Any) -> str | None:
    text = _stringify(maybe_relative)
    if not text:
        return None
    return urljoin(base_url, text)


def _is_rsshub_url(value: str) -> bool:
    return value.startswith("rsshub://")


def _resolve_feed_url(
    feed_url: str,
    rsshub_base_url: str | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    if not _is_rsshub_url(feed_url):
        return feed_url

    runtime_env = env or os.environ
    base_url = rsshub_base_url or runtime_env.get("AINFORMER_RSSHUB_BASE_URL") or DEFAULT_RSSHUB_BASE_URL
    route = feed_url[len("rsshub://") :].lstrip("/")
    return urljoin(base_url.rstrip("/") + "/", route)


def _rss_request_headers(headers: dict[str, str]) -> dict[str, str]:
    return {**DEFAULT_RSS_HEADERS, **headers}


def _request_kwargs(headers: dict[str, str], params: dict[str, str | int | float | bool]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"headers": headers}
    if params:
        kwargs["params"] = params
    return kwargs


def _is_xml_feed_response(content_type: str | None, body: str) -> bool:
    normalized_type = (content_type or "").lower()
    if any(token in normalized_type for token in ("xml", "rss", "atom")):
        return True

    leading_text = body.lstrip()[:128].lower()
    return leading_text.startswith(("<?xml", "<rss", "<feed", "<rdf:rdf"))


def _is_cloudflare_challenge(response: httpx.Response) -> bool:
    return response.headers.get("Cf-Mitigated") == "challenge" or "__cf_chl_opt" in response.text


def _response_snippet(body: str, *, limit: int = 160) -> str:
    return re.sub(r"\s+", " ", body).strip()[:limit]


def _render_template(template: str | None, payload: Any) -> str | None:
    if not template:
        return None

    def replace(match: re.Match[str]) -> str:
        value = _path_get(payload, match.group(1))
        text = _stringify(value)
        return text or ""

    rendered = re.sub(r"\{([^{}]+)\}", replace, template)
    rendered = rendered.strip()
    return rendered or None


def _datetime_value(value: Any) -> datetime | None:
    text = _stringify(value)
    if not text:
        return None
    try:
        normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
        return datetime.fromisoformat(normalized)
    except ValueError:
        try:
            return parsedate_to_datetime(text)
        except (TypeError, ValueError):
            return None


def _node_text(node: Tag | None) -> str | None:
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def _select_text(node: Tag, selector: str | None) -> str | None:
    if not selector:
        return None
    return _node_text(node.select_one(selector))


def _select_many_text(node: Tag, selector: str | None) -> list[str]:
    if not selector:
        return []
    return [text for child in node.select(selector) if (text := _node_text(child))]


def _select_attr(node: Tag, selector: str | None, attr: str | None) -> str | None:
    if not selector:
        return None
    child = node.select_one(selector)
    if child is None:
        return None
    if attr:
        value = child.get(attr)
        return _stringify(value)
    return _node_text(child)


def _select_attr_or_text(node: Tag, selector: str | None, attr: str | None) -> str | None:
    return _select_attr(node, selector, attr) if attr else _select_text(node, selector)


def _first_child_text(node: ET.Element, names: set[str]) -> str | None:
    for child in node.iter():
        if _tag_name(child.tag) in names:
            text = _stringify(child.text)
            if text:
                return text
    return None


def _all_child_text(node: ET.Element, names: set[str]) -> list[str]:
    values: list[str] = []
    for child in node.iter():
        if _tag_name(child.tag) in names and (text := _stringify(child.text)):
            values.extend(_string_list(text))
    return values


def _rss_link(node: ET.Element, base_url: str) -> str | None:
    for child in node.iter():
        name = _tag_name(child.tag)
        if name != "link":
            continue
        href = child.attrib.get("href")
        if href:
            return _absolute_url(base_url, href)
        text = _stringify(child.text)
        if text:
            return _absolute_url(base_url, text)
    return None


class BaseSourceAdapter(ABC):
    adapter_key: str
    capabilities: AdapterCapabilities

    def supports_method(self, method: AcquisitionMethod | str) -> bool:
        method_value = method.value if isinstance(method, AcquisitionMethod) else method
        return method_value in {supported.value for supported in self.capabilities.supported_methods}

    @abstractmethod
    async def fetch_items(
        self,
        source: SourceDefinition,
        request: FetchRequest,
    ) -> list[RawSourceItem]:
        raise NotImplementedError


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, BaseSourceAdapter] = {}

    def register(self, adapter: BaseSourceAdapter) -> None:
        self._adapters[adapter.adapter_key] = adapter

    def get(self, adapter_key: str) -> BaseSourceAdapter:
        try:
            return self._adapters[adapter_key]
        except KeyError as exc:
            raise AdapterNotImplementedError(
                f"No adapter implementation registered for adapter_key={adapter_key!r}"
            ) from exc

    def list_adapters(self) -> list[BaseSourceAdapter]:
        return sorted(self._adapters.values(), key=lambda adapter: adapter.adapter_key)


class GenericSourceAdapter(BaseSourceAdapter):
    adapter_key = "generic"
    capabilities = AdapterCapabilities(
        supported_methods=[AcquisitionMethod.API, AcquisitionMethod.RSS, AcquisitionMethod.SCRAPE],
        supports_full_text=True,
        stateless=True,
    )

    def __init__(self, *, env: Mapping[str, str] | None = None) -> None:
        self._env = dict(env or os.environ)

    async def fetch_items(
        self,
        source: SourceDefinition,
        request: FetchRequest,
    ) -> list[RawSourceItem]:
        try:
            if source.selected_method == AcquisitionMethod.API:
                if source.api is None:
                    raise SourceFetchError(f"Source {source.id} is missing [api] configuration")
                return await self._fetch_api(source, source.api, request)
            if source.selected_method == AcquisitionMethod.RSS:
                if source.rss is None:
                    raise SourceFetchError(f"Source {source.id} is missing [rss] configuration")
                return await self._fetch_rss(source, source.rss, request)
            if source.selected_method == AcquisitionMethod.SCRAPE:
                if source.scrape is None:
                    raise SourceFetchError(f"Source {source.id} is missing [scrape] configuration")
                return await self._fetch_scrape(source, source.scrape, request)
            raise SourceFetchError(f"Source {source.id} does not have a supported selected_method")
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"HTTP failure while fetching {source.id}: {exc}") from exc

    async def _fetch_api(
        self,
        source: SourceDefinition,
        config: ApiSourceConfig,
        request: FetchRequest,
    ) -> list[RawSourceItem]:
        async with self._client(config.timeout_seconds) as client:
            response = await client.get(config.url, **_request_kwargs(config.headers, config.params))
            response.raise_for_status()
            payload = response.json()
            items = _path_get(payload, config.items_path)
            if not isinstance(items, list):
                raise SourceFetchError(
                    f"Source {source.id} expected a list at items_path={config.items_path!r}"
                )

            results: list[RawSourceItem] = []
            for entry in items[: request.limit]:
                title = _stringify(_path_get(entry, config.title_field))
                url = _absolute_url(config.url, _path_get(entry, config.url_field)) or _absolute_url(
                    config.url, _render_template(config.url_template, entry)
                )
                if not title or not url:
                    continue

                article_url = (
                    _absolute_url(config.url, _path_get(entry, config.article_url_field or config.url_field))
                    or _absolute_url(config.url, _render_template(config.url_template, entry))
                )
                article_html = None
                if request.include_full_text and config.article_fetch_enabled and article_url:
                    article_html = await self._fetch_article_html(client, article_url, config.headers)

                results.append(
                    RawSourceItem.model_validate(
                        {
                            "external_id": _stringify(_path_get(entry, config.external_id_field)),
                            "title": title,
                            "url": url,
                            "canonical_url": (
                                _absolute_url(config.url, _path_get(entry, config.canonical_url_field))
                                or _absolute_url(
                                    config.url, _render_template(config.canonical_url_template, entry)
                                )
                                or url
                            ),
                            "published_at": _datetime_value(_path_get(entry, config.published_at_field)),
                            "authors": _string_list(_path_get(entry, config.authors_field)),
                            "tags": _string_list(_path_get(entry, config.tags_field)),
                            "excerpt": _stringify(_path_get(entry, config.excerpt_field)),
                            "content_text": _stringify(_path_get(entry, config.content_text_field)),
                            "content_html": _stringify(_path_get(entry, config.content_html_field)),
                            "article_html": article_html,
                            "raw_metadata": {"source_payload": entry},
                        }
                    )
                )
            return results

    async def _fetch_rss(
        self,
        source: SourceDefinition,
        config: RssSourceConfig,
        request: FetchRequest,
    ) -> list[RawSourceItem]:
        feed_url = _resolve_feed_url(config.feed_url, config.rsshub_base_url, self._env)
        headers = _rss_request_headers(config.headers)
        async with self._client(config.timeout_seconds) as client:
            response = await client.get(feed_url, **_request_kwargs(headers, config.params))
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                if _is_rsshub_url(config.feed_url):
                    raise SourceFetchError(
                        "RSSHub request failed for "
                        f"{source.id} via {feed_url} with status {exc.response.status_code}."
                    ) from exc
                raise
            if _is_cloudflare_challenge(response):
                raise SourceFetchError(
                    f"RSS request for {source.id} via {feed_url} was blocked by Cloudflare "
                    "and returned a challenge page instead of XML."
                )
            if not _is_xml_feed_response(response.headers.get("Content-Type"), response.text):
                raise SourceFetchError(
                    f"Expected RSS/Atom XML for {source.id} via {feed_url}, "
                    f"got {response.headers.get('Content-Type') or 'unknown content type'} "
                    f"with body starting {_response_snippet(response.text)!r}."
                )
            try:
                root = ET.fromstring(response.text)
            except ET.ParseError as exc:
                raise SourceFetchError(f"Failed to parse RSS/Atom for {source.id} via {feed_url}: {exc}") from exc

            nodes = [node for node in root.iter() if _tag_name(node.tag) in {"item", "entry"}]
            results: list[RawSourceItem] = []
            for node in nodes[: request.limit]:
                title = _first_child_text(node, {"title"})
                url = _rss_link(node, feed_url)
                if not title or not url:
                    continue

                content_html = _first_child_text(node, {"encoded", "content"})
                excerpt = _first_child_text(node, {"description", "summary", "subtitle"})
                article_html = None
                if request.include_full_text and config.article_fetch_enabled and not content_html:
                    article_html = await self._fetch_article_html(client, url, headers)

                results.append(
                    RawSourceItem.model_validate(
                        {
                            "external_id": _first_child_text(node, {"guid", "id"}),
                            "title": title,
                            "url": url,
                            "canonical_url": url,
                            "published_at": _datetime_value(
                                _first_child_text(node, {"pubDate", "published", "updated"})
                            ),
                            "authors": _all_child_text(node, {"author", "creator", "name"}),
                            "tags": _all_child_text(node, {"category"}),
                            "excerpt": excerpt,
                            "content_html": content_html,
                            "article_html": article_html,
                            "raw_metadata": {
                                "feed_url": feed_url,
                                "configured_feed_url": config.feed_url,
                            },
                        }
                    )
                )
            return results

    async def _fetch_scrape(
        self,
        source: SourceDefinition,
        config: ScrapeSourceConfig,
        request: FetchRequest,
    ) -> list[RawSourceItem]:
        async with self._client(config.timeout_seconds) as client:
            response = await client.get(config.entry_url, **_request_kwargs(config.headers, config.params))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            nodes = soup.select(config.item_selector)

            results: list[RawSourceItem] = []
            for node in nodes[: request.limit]:
                link_url = _absolute_url(config.entry_url, _select_attr(node, config.link_selector, config.link_attr))
                title = _select_text(node, config.title_selector) or _select_text(node, config.link_selector)
                if not title or not link_url:
                    continue

                article_html = None
                if request.include_full_text and config.article_fetch_enabled:
                    article_html = await self._fetch_article_html(client, link_url, config.headers)

                results.append(
                    RawSourceItem.model_validate(
                        {
                            "external_id": _select_attr_or_text(
                                node, config.external_id_selector, config.external_id_attr
                            ),
                            "title": title,
                            "url": link_url,
                            "canonical_url": _absolute_url(
                                config.entry_url,
                                _select_attr(node, config.canonical_url_selector, config.canonical_url_attr),
                            )
                            or link_url,
                            "published_at": _datetime_value(
                                _select_attr_or_text(
                                    node,
                                    config.published_at_selector,
                                    config.published_at_attr,
                                )
                            ),
                            "authors": _select_many_text(node, config.author_selector),
                            "tags": _select_many_text(node, config.tag_selector),
                            "excerpt": _select_text(node, config.excerpt_selector),
                            "article_html": article_html,
                            "raw_metadata": {"entry_url": config.entry_url},
                        }
                    )
                )
            return results

    @staticmethod
    async def _fetch_article_html(
        client: httpx.AsyncClient,
        article_url: str,
        headers: dict[str, str],
    ) -> str:
        response = await client.get(article_url, headers=headers)
        response.raise_for_status()
        return response.text

    @staticmethod
    def _client(timeout_seconds: float) -> httpx.AsyncClient:
        return httpx.AsyncClient(follow_redirects=True, timeout=timeout_seconds)


class FixtureSourceAdapter(BaseSourceAdapter):
    adapter_key = "fixture"
    capabilities = AdapterCapabilities(
        supported_methods=[AcquisitionMethod.API],
        supports_full_text=True,
        stateless=True,
    )

    async def fetch_items(
        self,
        source: SourceDefinition,
        request: FetchRequest,
    ) -> list[RawSourceItem]:
        package_root = resources.files("ainformer.fixtures")
        items_payload = json.loads(package_root.joinpath("sample_items.json").read_text(encoding="utf-8"))
        article_html = package_root.joinpath("sample_article.html").read_text(encoding="utf-8")

        items: list[RawSourceItem] = []
        for payload in items_payload[: request.limit]:
            if payload["external_id"] in {"fixture-article-1", "fixture-article-duplicate"}:
                payload = {**payload, "article_html": article_html}
            items.append(RawSourceItem.model_validate(payload))
        return items


def build_default_adapter_registry(*, env: Mapping[str, str] | None = None) -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(GenericSourceAdapter(env=env))
    registry.register(FixtureSourceAdapter())
    return registry

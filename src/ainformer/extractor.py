from __future__ import annotations

from datetime import datetime
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from ainformer.types import ExtractedArticle


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None

    try:
        if cleaned.endswith("Z"):
            cleaned = cleaned[:-1] + "+00:00"
        return datetime.fromisoformat(cleaned)
    except ValueError:
        try:
            return parsedate_to_datetime(cleaned)
        except (TypeError, ValueError):
            return None


def _first_non_empty(values: list[str | None]) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def extract_article_from_html(html: str) -> ExtractedArticle:
    soup = BeautifulSoup(html, "html.parser")

    title = _first_non_empty(
        [
            soup.find("meta", attrs={"property": "og:title"}) and soup.find("meta", attrs={"property": "og:title"}).get("content"),
            soup.title.string if soup.title else None,
            soup.find("h1").get_text(" ", strip=True) if soup.find("h1") else None,
        ]
    )

    published_value = _first_non_empty(
        [
            soup.find("meta", attrs={"property": "article:published_time"})
            and soup.find("meta", attrs={"property": "article:published_time"}).get("content"),
            soup.find("meta", attrs={"name": "pubdate"}) and soup.find("meta", attrs={"name": "pubdate"}).get("content"),
            soup.find("time") and (soup.find("time").get("datetime") or soup.find("time").get_text(" ", strip=True)),
        ]
    )
    published_at = _parse_datetime(published_value)

    author_value = _first_non_empty(
        [
            soup.find("meta", attrs={"name": "author"}) and soup.find("meta", attrs={"name": "author"}).get("content"),
            soup.find("meta", attrs={"property": "article:author"})
            and soup.find("meta", attrs={"property": "article:author"}).get("content"),
        ]
    )
    authors = [part.strip() for part in author_value.split(",")] if author_value else []
    authors = [author for author in authors if author]

    main_node = soup.find("article") or soup.find("main") or soup.body
    paragraphs = []
    if main_node is not None:
        paragraphs = [node.get_text(" ", strip=True) for node in main_node.find_all("p")]
        paragraphs = [paragraph for paragraph in paragraphs if paragraph]

    excerpt = _first_non_empty(
        [
            soup.find("meta", attrs={"name": "description"}) and soup.find("meta", attrs={"name": "description"}).get("content"),
            paragraphs[0] if paragraphs else None,
        ]
    )

    if paragraphs:
        content_text = "\n\n".join(paragraphs)
    elif main_node is not None:
        fallback_text = main_node.get_text("\n", strip=True)
        content_text = fallback_text or None
    else:
        content_text = None

    if main_node is None:
        content_html = None
    elif main_node.name == "article":
        content_html = str(main_node)
    else:
        article_node = main_node.find("article")
        content_html = str(article_node or main_node)

    return ExtractedArticle(
        title=title,
        published_at=published_at,
        authors=authors,
        excerpt=excerpt,
        content_text=content_text,
        content_html=content_html,
        content_complete=bool(content_text and content_html),
    )


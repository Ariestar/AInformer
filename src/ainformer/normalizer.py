from __future__ import annotations

from hashlib import sha1

from ainformer.extractor import extract_article_from_html
from ainformer.types import RawSourceItem, SourceDefinition, StandardizedRecord


def _compute_record_id(source_id: str, seed: str) -> str:
    digest = sha1(f"{source_id}:{seed}".encode("utf-8"), usedforsecurity=False)
    return digest.hexdigest()


def normalize_raw_item(
    *,
    source: SourceDefinition,
    item: RawSourceItem,
    include_full_text: bool,
) -> StandardizedRecord:
    extracted = None
    if include_full_text and item.article_html:
        extracted = extract_article_from_html(item.article_html)

    content_text = item.content_text
    content_html = item.content_html
    excerpt = item.excerpt
    title = item.title
    published_at = item.published_at
    authors = item.authors

    if extracted:
        title = title or extracted.title
        published_at = published_at or extracted.published_at
        authors = authors or extracted.authors
        excerpt = excerpt or extracted.excerpt
        content_text = content_text or extracted.content_text
        content_html = content_html or extracted.content_html

    if not include_full_text:
        content_text = None
        content_html = None

    dedupe_seed = item.canonical_url or item.external_id or item.url or item.title
    content_complete = bool(include_full_text and content_text and content_html)

    return StandardizedRecord(
        record_id=_compute_record_id(source.id, dedupe_seed),
        source_id=source.id,
        acquisition_method=source.selected_method,
        external_id=item.external_id,
        title=title,
        url=item.url,
        canonical_url=item.canonical_url,
        published_at=published_at,
        authors=authors,
        tags=item.tags,
        excerpt=excerpt,
        content_text=content_text,
        content_html=content_html,
        content_complete=content_complete,
        raw_metadata=item.raw_metadata,
    )

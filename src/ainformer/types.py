from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AcquisitionMethod(StrEnum):
    API = "api"
    RSS = "rss"
    SCRAPE = "scrape"


class FullTextPolicy(StrEnum):
    PREFER_FULL_TEXT = "prefer_full_text"
    EXCERPT_ONLY = "excerpt_only"


class AdapterCapabilities(BaseModel):
    supported_methods: list[AcquisitionMethod]
    supports_full_text: bool = True
    stateless: bool = True


class ApiSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    items_path: str = "items"
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str | int | float | bool] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=20.0, gt=0)
    article_fetch_enabled: bool = False
    external_id_field: str | None = "id"
    title_field: str = "title"
    url_field: str = "url"
    url_template: str | None = None
    canonical_url_field: str | None = None
    canonical_url_template: str | None = None
    published_at_field: str | None = "published_at"
    authors_field: str | None = "authors"
    tags_field: str | None = "tags"
    excerpt_field: str | None = "excerpt"
    content_text_field: str | None = "content_text"
    content_html_field: str | None = "content_html"
    article_url_field: str | None = None


class RssSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feed_url: str
    rsshub_base_url: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str | int | float | bool] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=20.0, gt=0)
    article_fetch_enabled: bool = True


class ScrapeSourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_url: str
    item_selector: str
    link_selector: str
    link_attr: str = "href"
    title_selector: str | None = None
    published_at_selector: str | None = None
    published_at_attr: str | None = "datetime"
    author_selector: str | None = None
    excerpt_selector: str | None = None
    tag_selector: str | None = None
    canonical_url_selector: str | None = None
    canonical_url_attr: str = "href"
    external_id_selector: str | None = None
    external_id_attr: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    params: dict[str, str | int | float | bool] = Field(default_factory=dict)
    timeout_seconds: float = Field(default=20.0, gt=0)
    article_fetch_enabled: bool = True


class SourceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    adapter_key: str = "generic"
    candidate_methods: list[AcquisitionMethod]
    selected_method: AcquisitionMethod
    enabled: bool = True
    full_text_policy: FullTextPolicy = FullTextPolicy.PREFER_FULL_TEXT
    tags: list[str] = Field(default_factory=list)
    api: ApiSourceConfig | None = None
    rss: RssSourceConfig | None = None
    scrape: ScrapeSourceConfig | None = None

    @field_validator("candidate_methods")
    @classmethod
    def validate_candidate_methods(cls, value: list[AcquisitionMethod]) -> list[AcquisitionMethod]:
        if not value:
            raise ValueError("candidate_methods cannot be empty")

        order = {
            AcquisitionMethod.API: 0,
            AcquisitionMethod.RSS: 1,
            AcquisitionMethod.SCRAPE: 2,
        }
        if len(set(value)) != len(value):
            raise ValueError("candidate_methods cannot contain duplicates")
        if value != sorted(value, key=order.__getitem__):
            raise ValueError("candidate_methods must follow api > rss > scrape order")
        return value

    @model_validator(mode="after")
    def validate_source(self) -> "SourceDefinition":
        if self.selected_method not in self.candidate_methods:
            raise ValueError("selected_method must be one of candidate_methods")
        defined_configs = {
            AcquisitionMethod.API: self.api,
            AcquisitionMethod.RSS: self.rss,
            AcquisitionMethod.SCRAPE: self.scrape,
        }
        for method, config in defined_configs.items():
            if config is not None and method not in self.candidate_methods:
                raise ValueError(f"{method.value} config requires that method to exist in candidate_methods")
        if self.adapter_key == "generic" and defined_configs[self.selected_method] is None:
            raise ValueError(
                f"generic source selected for {self.selected_method.value} must define a matching config block"
            )
        return self


class SourceError(BaseModel):
    source_id: str
    code: str
    message: str
    retryable: bool = False


class FetchRequest(BaseModel):
    source_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=10, ge=1, le=100)
    include_full_text: bool = True

    @field_validator("source_ids")
    @classmethod
    def validate_source_ids(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("source_ids cannot be empty")
        if len(set(value)) != len(value):
            raise ValueError("source_ids cannot contain duplicates")
        return value


class RawSourceItem(BaseModel):
    external_id: str | None = None
    title: str
    url: str
    canonical_url: str | None = None
    published_at: datetime | None = None
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    content_text: str | None = None
    content_html: str | None = None
    article_html: str | None = None
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class StandardizedRecord(BaseModel):
    record_id: str
    source_id: str
    acquisition_method: AcquisitionMethod
    external_id: str | None = None
    title: str
    url: str
    canonical_url: str | None = None
    published_at: datetime | None = None
    authors: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    content_text: str | None = None
    content_html: str | None = None
    content_complete: bool = False
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class FetchResult(BaseModel):
    request: FetchRequest
    records: list[StandardizedRecord] = Field(default_factory=list)
    errors: list[SourceError] = Field(default_factory=list)
    total_records: int = 0
    deduped_records: int = 0


class ExtractedArticle(BaseModel):
    title: str | None = None
    published_at: datetime | None = None
    authors: list[str] = Field(default_factory=list)
    excerpt: str | None = None
    content_text: str | None = None
    content_html: str | None = None
    content_complete: bool = False

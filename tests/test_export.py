import json
from pathlib import Path

from export import cluster_id, item_id, to_export, validate

SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "pool.schema.json"
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

RAW = {
    "generated_at": "2026-10-28T00:00:00+00:00",
    "window_days": 7,
    "stats": {"sources_total": 1, "sources_ok": 1, "raw_items": 1, "after_dedup": 1},
    "items": [
        {
            "source_id": "s",
            "source_name": "Source",
            "tier": "media",
            "weight": 0.5,
            "title": "A title",
            "url": "https://a.com/1",
            "published": None,
            "summary": "",
            "fetched_at": "2026-10-28T00:00:00+00:00",
        }
    ],
}

EXPORT_FIELDS = {
    "id",
    "source_id",
    "source_name",
    "tier",
    "title",
    "url",
    "published",
    "summary",
    "cluster_id",
    "weight",
}


class TestItemId:
    def test_stable_for_same_url(self):
        assert item_id("https://a.com/1") == item_id("https://a.com/1")

    def test_is_12_chars(self):
        assert len(item_id("https://a.com/1")) == 12

    def test_differs_for_different_url(self):
        assert item_id("https://a.com/1") != item_id("https://a.com/2")


class TestClusterId:
    def test_same_title_clusters(self):
        assert cluster_id("Hello, World!") == cluster_id("hello world")

    def test_different_title_differs(self):
        assert cluster_id("Alpha") != cluster_id("Beta")


class TestToExport:
    def test_only_contract_fields(self):
        assert set(to_export(RAW)["items"][0]) == EXPORT_FIELDS

    def test_drops_fetch_time(self):
        assert "fetched_at" not in to_export(RAW)["items"][0]

    def test_keeps_missing_published_as_none(self):
        assert to_export(RAW)["items"][0]["published"] is None


class TestValidate:
    def test_accepts_generated_payload(self):
        assert validate(to_export(RAW), SCHEMA, SCHEMA) == []

    def test_rejects_missing_required_field(self):
        payload = to_export(RAW)
        del payload["items"][0]["title"]
        assert any("title" in error for error in validate(payload, SCHEMA, SCHEMA))

    def test_rejects_unknown_tier(self):
        payload = to_export(RAW)
        payload["items"][0]["tier"] = "unknown"
        assert validate(payload, SCHEMA, SCHEMA)

    def test_rejects_extra_field(self):
        payload = to_export(RAW)
        payload["items"][0]["extra"] = 1
        assert any("契约外字段" in error for error in validate(payload, SCHEMA, SCHEMA))

    def test_rejects_bad_timestamp(self):
        payload = to_export(RAW)
        payload["generated_at"] = "2026/10/28"
        assert validate(payload, SCHEMA, SCHEMA)

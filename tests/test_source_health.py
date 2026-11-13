from datetime import UTC, datetime, timedelta

from source_health import summarize

NOW = datetime(2026, 11, 13, tzinfo=UTC)


def source(**over):
    row = {"id": "s1", "name": "Source", "ok": True, "kept": 1, "error": None}
    row.update(over)
    return row


def item(published, source_id="s1"):
    return {"source_id": source_id, "published": published}


class TestSummarize:
    def test_ok_source(self):
        result = summarize([source()], [item(NOW.isoformat())], NOW, 60)
        assert result["rows"][0]["state"] == "ok"
        assert result["problemCount"] == 0

    def test_error_source(self):
        result = summarize([source(ok=False, error="boom")], [], NOW, 60)
        assert result["rows"][0]["state"] == "error"
        assert result["alerts"] == ["Source 本轮抓取失败"]

    def test_empty_source_uses_window(self):
        result = summarize([source(kept=0)], [], NOW, 30)
        assert result["rows"][0]["state"] == "empty"
        assert result["alerts"] == ["Source 30 天内零新增"]

    def test_stale_source(self):
        old = (NOW - timedelta(days=40)).isoformat()
        result = summarize([source()], [item(old)], NOW, 60)
        assert result["rows"][0]["state"] == "stale"
        assert result["alerts"] == ["Source 已 40 天未更新"]

    def test_problems_sort_before_ok(self):
        result = summarize(
            [source(id="ok", name="OK"), source(id="bad", name="Bad", ok=False)],
            [item(NOW.isoformat(), source_id="ok")],
            NOW,
            60,
        )
        assert [row["id"] for row in result["rows"]] == ["bad", "ok"]

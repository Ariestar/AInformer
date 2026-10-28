from datetime import UTC, datetime

import pytest

from fetch import canon_url, parse_date, parse_feed, strip_html, title_key


class TestParseDate:
    def test_rfc2822(self):
        dt = parse_date("Wed, 28 Oct 2026 06:15:43 GMT")
        assert dt == datetime(2026, 10, 28, 6, 15, 43, tzinfo=UTC)

    def test_iso8601_with_offset(self):
        dt = parse_date("2026-10-28T06:15:43+08:00")
        assert dt == datetime(2026, 10, 27, 22, 15, 43, tzinfo=UTC)

    def test_naive_datetime_is_utc(self):
        assert parse_date("2026-10-28T06:15:43") == datetime(2026, 10, 28, 6, 15, 43, tzinfo=UTC)

    @pytest.mark.parametrize("raw", [None, "", "not a date"])
    def test_unparseable_returns_none(self, raw):
        assert parse_date(raw) is None


class TestCanonUrl:
    def test_strips_tracking_params(self):
        assert canon_url("https://a.com/x?utm_source=rss&ref=t") == "https://a.com/x"

    def test_strips_fragment(self):
        assert canon_url("https://a.com/x#top") == "https://a.com/x"

    def test_strips_trailing_slash(self):
        assert canon_url("https://a.com/x/") == "https://a.com/x"

    def test_keeps_meaningful_query(self):
        assert canon_url("https://a.com/x?id=7") == "https://a.com/x?id=7"


class TestTitleKey:
    def test_ignores_case_and_punctuation(self):
        assert title_key("Hello, World!") == title_key("hello world")

    def test_truncates_to_40_chars(self):
        assert len(title_key("x" * 100)) == 40


class TestStripHtml:
    def test_removes_tags(self):
        assert strip_html("<p>hi</p>") == "hi"

    def test_drops_script_body(self):
        assert "bad" not in strip_html("<p>hi</p><script>bad()</script>")

    def test_unescapes_entities(self):
        assert strip_html("a &amp; b") == "a & b"


class TestParseFeed:
    def test_atom_entry(self):
        xml = b"""<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <title>Atom title</title>
            <link rel="alternate" href="https://a.com/1"/>
            <published>2026-10-28T00:00:00Z</published>
            <summary>Atom summary</summary>
          </entry>
        </feed>"""
        items = parse_feed(xml)
        assert items == [
            {
                "title": "Atom title",
                "url": "https://a.com/1",
                "published": datetime(2026, 10, 28, tzinfo=UTC),
                "summary": "Atom summary",
            }
        ]

    def test_rss_item(self):
        xml = b"""<?xml version="1.0"?>
        <rss version="2.0"><channel><item>
          <title>RSS title</title>
          <link>https://a.com/2</link>
          <pubDate>Wed, 28 Oct 2026 00:00:00 GMT</pubDate>
          <description>RSS summary</description>
        </item></channel></rss>"""
        items = parse_feed(xml)
        assert items[0]["url"] == "https://a.com/2"
        assert items[0]["summary"] == "RSS summary"

    def test_malformed_xml_raises_value_error(self):
        with pytest.raises(ValueError):
            parse_feed(b"<not-xml")

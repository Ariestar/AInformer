import asyncio
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import ainformer.adapters as adapters
from ainformer.service import AInformerService
from ainformer.types import FetchRequest


@contextmanager
def static_site_server(directory: Path):
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def build_rsshub_fixture_site(directory: Path) -> None:
    fixture_dir = Path("tests/fixtures/site").resolve()
    (directory / "anthropic").mkdir(parents=True, exist_ok=True)
    (directory / "article.html").write_text(
        fixture_dir.joinpath("article.html").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (directory / "anthropic" / "news").write_text(
        fixture_dir.joinpath("rss.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )


def test_generic_scrape_source_runs_from_config_only(tmp_path: Path) -> None:
    site_dir = Path("tests/fixtures/site").resolve()
    with static_site_server(site_dir) as base_url:
        config = tmp_path / "sources.toml"
        config.write_text(
            f"""
            [scrape."demo.scrape"]
            name = "Demo Scrape"
            tags = ["demo"]
            entry_url = "{base_url}/list.html"
            item_selector = ".story"
            title_selector = ".story-title"
            link_selector = ".story-link"
            link_attr = "href"
            published_at_selector = ".story-time"
            published_at_attr = "datetime"
            author_selector = ".story-author"
            excerpt_selector = ".story-excerpt"
            tag_selector = ".story-tag"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.scrape"], limit=10, include_full_text=True))
        )

    assert not result.errors
    assert result.total_records == 1
    record = result.records[0]
    assert record.title == "Config Driven Scrape Story"
    assert record.authors == ["Alice"]
    assert record.tags == ["ai", "crawler"]
    assert "only a source config entry" in record.content_text


def test_generic_api_source_runs_from_config_only(tmp_path: Path) -> None:
    site_dir = Path("tests/fixtures/site").resolve()
    with static_site_server(site_dir) as base_url:
        config = tmp_path / "sources.toml"
        config.write_text(
            f"""
            [api."demo.api"]
            name = "Demo API"
            tags = ["demo"]
            url = "{base_url}/api.json"
            items_path = "items"
            article_fetch_enabled = true
            external_id_field = "id"
            title_field = "title"
            url_field = "url"
            published_at_field = "published_at"
            authors_field = "authors"
            tags_field = "tags"
            excerpt_field = "excerpt"
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(service.fetch(FetchRequest(source_ids=["demo.api"], limit=10, include_full_text=True)))

    assert not result.errors
    assert result.total_records == 1
    record = result.records[0]
    assert record.external_id == "api-story-1"
    assert record.title == "Config Driven API Story"
    assert record.authors == ["API Bot"]
    assert "No platform-specific Python adapter was required." in record.content_text


def test_generic_api_source_supports_root_array_and_templates(tmp_path: Path) -> None:
    site_dir = Path("tests/fixtures/site").resolve()
    with static_site_server(site_dir) as base_url:
        config = tmp_path / "sources.toml"
        config.write_text(
            f"""
            [api."demo.api.root_array"]
            name = "Demo API Root Array"
            tags = ["demo"]
            url = "{base_url}/root_api.json"
            items_path = "$"
            article_fetch_enabled = false
            external_id_field = "paper.id"
            title_field = "title"
            url_template = "https://huggingface.co/papers/{{paper.id}}"
            canonical_url_template = "https://huggingface.co/papers/{{paper.id}}"
            published_at_field = "publishedAt"
            authors_field = "paper.authors"
            tags_field = "paper.ai_keywords"
            excerpt_field = "summary"
            content_text_field = "summary"
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.api.root_array"], limit=10, include_full_text=True))
        )

    assert not result.errors
    assert result.total_records == 1
    record = result.records[0]
    assert record.external_id == "2603.02510"
    assert record.title == "Root Array API Story"
    assert record.url == "https://huggingface.co/papers/2603.02510"
    assert record.authors == ["Liu Yang", "Zeyu Nie"]
    assert record.tags == ["llm", "parallelism"]
    assert record.content_text == "Root array API item excerpt."


def test_generic_rss_source_runs_from_config_only(tmp_path: Path) -> None:
    site_dir = Path("tests/fixtures/site").resolve()
    with static_site_server(site_dir) as base_url:
        config = tmp_path / "sources.toml"
        config.write_text(
            f"""
            [rss."demo.rss"]
            name = "Demo RSS"
            tags = ["demo"]
            feed_url = "{base_url}/rss.xml"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(service.fetch(FetchRequest(source_ids=["demo.rss"], limit=10, include_full_text=True)))

    assert not result.errors
    assert result.total_records == 1
    record = result.records[0]
    assert record.external_id == "rss-story-1"
    assert record.title == "Config Driven RSS Story"
    assert "only a source config entry" in record.content_text


def test_generic_rss_source_preserves_query_string_in_feed_url(tmp_path: Path) -> None:
    site_dir = Path("tests/fixtures/site").resolve()
    with static_site_server(site_dir) as base_url:
        config = tmp_path / "sources.toml"
        config.write_text(
            f"""
            [rss."demo.rss.query"]
            name = "Demo RSS Query"
            feed_url = "{base_url}/rss.xml?category=ai&limit=5"
            article_fetch_enabled = false
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.rss.query"], limit=10, include_full_text=False))
        )

    assert not result.errors
    assert result.total_records == 1
    assert result.records[0].raw_metadata["feed_url"].endswith("category=ai&limit=5")


def test_generic_rsshub_source_uses_default_self_hosted_base_url(tmp_path: Path, monkeypatch) -> None:
    site_dir = tmp_path / "rsshub-site"
    build_rsshub_fixture_site(site_dir)
    with static_site_server(site_dir) as base_url:
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("AINFORMER_RSSHUB_BASE_URL", raising=False)
        monkeypatch.setattr(adapters, "DEFAULT_RSSHUB_BASE_URL", base_url)
        config = tmp_path / "sources.toml"
        config.write_text(
            """
            [rss."demo.rsshub"]
            name = "Demo RSSHub"
            tags = ["demo", "rsshub"]
            feed_url = "rsshub://anthropic/news"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.rsshub"], limit=10, include_full_text=True))
        )

    assert not result.errors
    assert result.total_records == 1
    record = result.records[0]
    assert record.title == "Config Driven RSS Story"
    assert record.raw_metadata["configured_feed_url"] == "rsshub://anthropic/news"
    assert record.raw_metadata["feed_url"].startswith(base_url)
    assert "only a source config entry" in record.content_text


def test_generic_rsshub_source_uses_env_base_url(tmp_path: Path, monkeypatch) -> None:
    site_dir = tmp_path / "rsshub-site"
    build_rsshub_fixture_site(site_dir)
    with static_site_server(site_dir) as base_url:
        monkeypatch.setenv("AINFORMER_RSSHUB_BASE_URL", base_url)
        config = tmp_path / "sources.toml"
        config.write_text(
            """
            [rss."demo.rsshub.env"]
            name = "Demo RSSHub Env"
            tags = ["demo", "rsshub"]
            feed_url = "rsshub://anthropic/news"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.rsshub.env"], limit=10, include_full_text=True))
        )

    assert not result.errors
    assert result.total_records == 1
    assert result.records[0].raw_metadata["feed_url"].startswith(base_url)


def test_generic_rsshub_source_prefers_config_base_url_over_env(tmp_path: Path, monkeypatch) -> None:
    site_dir = tmp_path / "rsshub-site"
    build_rsshub_fixture_site(site_dir)
    with static_site_server(site_dir) as base_url:
        monkeypatch.setenv("AINFORMER_RSSHUB_BASE_URL", "http://127.0.0.1:9")
        config = tmp_path / "sources.toml"
        config.write_text(
            f"""
            [rss."demo.rsshub.config"]
            name = "Demo RSSHub Config"
            tags = ["demo", "rsshub"]
            feed_url = "rsshub://anthropic/news"
            rsshub_base_url = "{base_url}"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.rsshub.config"], limit=10, include_full_text=True))
        )

    assert not result.errors
    assert result.total_records == 1
    assert result.records[0].raw_metadata["feed_url"].startswith(base_url)


def test_service_loads_rsshub_base_url_from_dotenv(tmp_path: Path, monkeypatch) -> None:
    site_dir = tmp_path / "rsshub-site"
    build_rsshub_fixture_site(site_dir)
    with static_site_server(site_dir) as base_url:
        monkeypatch.delenv("AINFORMER_RSSHUB_BASE_URL", raising=False)
        monkeypatch.chdir(tmp_path)
        config = tmp_path / "sources.toml"
        dotenv_path = tmp_path / ".env"
        dotenv_path.write_text(f"AINFORMER_RSSHUB_BASE_URL={base_url}\n", encoding="utf-8")
        config.write_text(
            """
            [rss."demo.rsshub.dotenv"]
            name = "Demo RSSHub Dotenv"
            tags = ["demo", "rsshub"]
            feed_url = "rsshub://anthropic/news"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.rsshub.dotenv"], limit=10, include_full_text=True))
        )

    assert not result.errors
    assert result.total_records == 1
    assert result.records[0].raw_metadata["feed_url"].startswith(base_url)


def test_services_isolate_dotenv_overrides_per_config(tmp_path: Path, monkeypatch) -> None:
    first_site_dir = tmp_path / "rsshub-site-one"
    second_site_dir = tmp_path / "rsshub-site-two"
    build_rsshub_fixture_site(first_site_dir)
    build_rsshub_fixture_site(second_site_dir)

    with static_site_server(first_site_dir) as first_base_url, static_site_server(second_site_dir) as second_base_url:
        monkeypatch.delenv("AINFORMER_RSSHUB_BASE_URL", raising=False)

        first_config_dir = tmp_path / "config-one"
        second_config_dir = tmp_path / "config-two"
        first_config_dir.mkdir()
        second_config_dir.mkdir()

        (first_config_dir / ".env").write_text(
            f"AINFORMER_RSSHUB_BASE_URL={first_base_url}\n",
            encoding="utf-8",
        )
        (second_config_dir / ".env").write_text(
            f"AINFORMER_RSSHUB_BASE_URL={second_base_url}\n",
            encoding="utf-8",
        )
        (first_config_dir / "sources.toml").write_text(
            """
            [rss."demo.rsshub.first"]
            name = "Demo RSSHub First"
            feed_url = "rsshub://anthropic/news"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )
        (second_config_dir / "sources.toml").write_text(
            """
            [rss."demo.rsshub.second"]
            name = "Demo RSSHub Second"
            feed_url = "rsshub://anthropic/news"
            article_fetch_enabled = true
            """,
            encoding="utf-8",
        )

        first_service = AInformerService(config_path=first_config_dir / "sources.toml")
        first_result = asyncio.run(
            first_service.fetch(FetchRequest(source_ids=["demo.rsshub.first"], limit=10, include_full_text=True))
        )

        second_service = AInformerService(config_path=second_config_dir / "sources.toml")
        second_result = asyncio.run(
            second_service.fetch(FetchRequest(source_ids=["demo.rsshub.second"], limit=10, include_full_text=True))
        )

    assert not first_result.errors
    assert not second_result.errors
    assert first_result.records[0].raw_metadata["feed_url"].startswith(first_base_url)
    assert second_result.records[0].raw_metadata["feed_url"].startswith(second_base_url)


def test_generic_rss_source_rejects_non_xml_response(tmp_path: Path) -> None:
    site_dir = Path("tests/fixtures/site").resolve()
    with static_site_server(site_dir) as base_url:
        config = tmp_path / "sources.toml"
        config.write_text(
            f"""
            [rss."demo.rss.invalid"]
            name = "Demo RSS Invalid"
            tags = ["demo", "rss"]
            feed_url = "{base_url}/list.html"
            article_fetch_enabled = false
            """,
            encoding="utf-8",
        )

        service = AInformerService(config_path=config)
        result = asyncio.run(
            service.fetch(FetchRequest(source_ids=["demo.rss.invalid"], limit=10, include_full_text=True))
        )

    assert not result.records
    assert result.errors[0].code == "fetch_failed"
    assert "Expected RSS/Atom XML" in result.errors[0].message

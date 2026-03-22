def test_dashboard_page_returns_html(api_client) -> None:
    response = api_client.get("/")

    assert response.status_code == 200
    assert "AInformer Feedboard" in response.text
    assert '<div id="records-root"></div>' in response.text


def test_health_endpoint(api_client) -> None:
    response = api_client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_sources_endpoint(api_client) -> None:
    response = api_client.get("/v1/sources")

    assert response.status_code == 200
    source_ids = {item["id"] for item in response.json()}
    assert "arxiv.ai" in source_ids
    assert "arxiv.ml" in source_ids
    assert "arxiv.nlp" in source_ids
    assert "arxiv.cv" in source_ids
    assert "openai.blog" in source_ids
    assert "openai.cookbook" in source_ids
    assert "openai.research" in source_ids
    assert "ollama.library" in source_ids


def test_get_source_endpoint(fixture_api_client) -> None:
    response = fixture_api_client.get("/v1/sources/fixture.local_demo")

    assert response.status_code == 200
    assert response.json()["id"] == "fixture.local_demo"


def test_fetch_endpoint_returns_fixture_records(fixture_api_client) -> None:
    response = fixture_api_client.post(
        "/v1/fetch",
        json={
            "source_ids": ["fixture.local_demo"],
            "limit": 10,
            "include_full_text": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_records"] == 2
    assert payload["deduped_records"] == 1


def test_fetch_endpoint_rejects_missing_source(api_client) -> None:
    response = api_client.post(
        "/v1/fetch",
        json={
            "source_ids": ["missing.source"],
            "limit": 10,
            "include_full_text": True,
        },
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["errors"][0]["code"] == "source_not_found"

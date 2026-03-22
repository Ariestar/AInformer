import json

from typer.testing import CliRunner

from ainformer.cli import app

runner = CliRunner()


def test_sources_list_command(config_path) -> None:
    result = runner.invoke(app, ["sources", "list", "--config", str(config_path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    source_ids = {item["id"] for item in payload}
    assert "arxiv.ai" in source_ids
    assert "arxiv.ml" in source_ids
    assert "arxiv.nlp" in source_ids
    assert "arxiv.cv" in source_ids
    assert "openai.blog" in source_ids
    assert "openai.cookbook" in source_ids
    assert "openai.research" in source_ids
    assert "ollama.library" in source_ids


def test_fetch_command_for_fixture_source(fixture_config_path) -> None:
    result = runner.invoke(
        app,
        [
            "fetch",
            "--config",
            str(fixture_config_path),
            "--source-id",
            "fixture.local_demo",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total_records"] == 2
    assert payload["deduped_records"] == 1


def test_fetch_command_raw_outputs_provider_payload(fixture_config_path) -> None:
    result = runner.invoke(
        app,
        [
            "fetch",
            "--config",
            str(fixture_config_path),
            "--source-id",
            "fixture.local_demo",
            "--raw",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total_records"] == 2
    assert len(payload["raw_records"]) == 2
    assert payload["raw_records"][0]["kind"] == "fixture_article"


def test_fetch_command_rejects_missing_source(config_path) -> None:
    result = runner.invoke(
        app,
        [
            "fetch",
            "--config",
            str(config_path),
            "--source-id",
            "missing.source",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["errors"][0]["code"] == "source_not_found"


def test_fetch_all_command_for_fixture_only_config() -> None:
    config_path = "tests/fixtures/fixture_only_sources.toml"
    result = runner.invoke(
        app,
        [
            "fetch-all",
            "--config",
            config_path,
            "--no-include-full-text",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["request"]["source_ids"] == ["fixture.local_demo"]
    assert payload["total_records"] == 2
    assert payload["deduped_records"] == 1


def test_fetch_all_command_raw_outputs_provider_payload() -> None:
    config_path = "tests/fixtures/fixture_only_sources.toml"
    result = runner.invoke(
        app,
        [
            "fetch-all",
            "--config",
            config_path,
            "--raw",
            "--no-include-full-text",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["request"]["source_ids"] == ["fixture.local_demo"]
    assert payload["total_records"] == 2
    assert len(payload["raw_records"]) == 2
    assert payload["raw_records"][0]["kind"] == "fixture_article"

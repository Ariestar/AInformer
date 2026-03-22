from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ainformer.api import create_app
from ainformer.config import default_config_path
from ainformer.sdk import AInformerClient
from ainformer.service import AInformerService


@pytest.fixture(scope="session")
def config_path() -> Path:
    return default_config_path()


@pytest.fixture(scope="session")
def fixture_config_path() -> Path:
    return Path("tests/fixtures/fixture_only_sources.toml")


@pytest.fixture()
def service(fixture_config_path: Path) -> AInformerService:
    return AInformerService(config_path=fixture_config_path)


@pytest.fixture()
def sdk_client(config_path: Path) -> AInformerClient:
    return AInformerClient(config_path=config_path)


@pytest.fixture()
def api_client(config_path: Path) -> TestClient:
    return TestClient(create_app(config_path=config_path))


@pytest.fixture()
def fixture_api_client(fixture_config_path: Path) -> TestClient:
    return TestClient(create_app(config_path=fixture_config_path))

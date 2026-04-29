from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import app.main as main_module


client = TestClient(main_module.app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_health_does_not_expose_secrets() -> None:
    response = client.get("/health/runtime")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "model_api_configured" in payload
    assert "model" in payload
    assert "api_key" not in payload
    assert "base_url" not in payload


def test_health_endpoint_stays_available_when_database_startup_fails(monkeypatch) -> None:
    def broken_init_db() -> None:
        raise RuntimeError("database expired")

    monkeypatch.setattr(main_module, "init_db", broken_init_db)

    with TestClient(main_module.app) as test_client:
        response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "database expired" in main_module.app.state.database_startup_error


def test_startup_uses_fallback_database_when_primary_fails(monkeypatch) -> None:
    init_calls = {"count": 0}
    configured_urls = []

    def flaky_init_db() -> None:
        init_calls["count"] += 1
        if init_calls["count"] == 1:
            raise RuntimeError("primary database expired")

    def record_configure_database(database_url: str) -> None:
        configured_urls.append(database_url)

    monkeypatch.setattr(main_module, "init_db", flaky_init_db)
    monkeypatch.setattr(main_module, "configure_database", record_configure_database)

    with TestClient(main_module.app) as test_client:
        response = test_client.get("/health")

    assert response.status_code == 200
    assert main_module.app.state.database_fallback_active is True
    assert configured_urls == [main_module.settings.database_fallback_url]


def test_root_returns_status_when_frontend_bundle_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main_module, "frontend_out_dir", tmp_path / "missing-frontend")

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["health"] == "/health"


def test_database_errors_return_service_unavailable() -> None:
    def broken_db():
        raise SQLAlchemyError("database expired")
        yield

    main_module.app.dependency_overrides[main_module.get_db] = broken_db
    try:
        response = client.get("/jobs")
    finally:
        main_module.app.dependency_overrides.clear()

    assert response.status_code == 503
    assert "Database is unavailable" in response.json()["detail"]

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

import app.main as main_module


client = TestClient(main_module.app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_stays_available_when_database_startup_fails(monkeypatch) -> None:
    def broken_init_db() -> None:
        raise RuntimeError("database expired")

    monkeypatch.setattr(main_module, "init_db", broken_init_db)

    with TestClient(main_module.app) as test_client:
        response = test_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert main_module.app.state.database_startup_error == "database expired"


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

from fastapi.testclient import TestClient

import app.main as main_module


client = TestClient(main_module.app)


def test_health_endpoint() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_returns_status_when_frontend_bundle_is_missing(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(main_module, "frontend_out_dir", tmp_path / "missing-frontend")

    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["health"] == "/health"

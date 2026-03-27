from __future__ import annotations

import sys
import types
from io import BytesIO
from pathlib import Path

from fastapi.datastructures import UploadFile

from app.config import Settings
from app.services.storage import LocalStorageService, OssStorageService, get_storage_service


def make_upload(filename: str, content: bytes, content_type: str = "text/plain") -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=filename, headers=None)


def test_settings_parse_database_url_and_cors_origins(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db.example.com:5432/screening")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com, https://admin.example.com")
    settings = Settings()

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.cors_origins == ["https://app.example.com", "https://admin.example.com"]


def test_local_storage_round_trip(tmp_path: Path) -> None:
    settings = Settings(storage_dir=tmp_path / "storage", storage_backend="local")
    service = LocalStorageService(settings)

    stored = service.save_bytes("resume.txt", b"hello world", "resumes", "text/plain")

    assert stored.backend == "local"
    assert stored.local_path is not None
    assert stored.local_path.read_bytes() == b"hello world"
    assert service.read_bytes(stored) == b"hello world"

    reference = service.build_reference(stored.key, stored.filename, stored.content_type)
    assert reference.backend == "local"
    assert reference.key == stored.key
    assert reference.local_path is not None

    service.delete(stored.key)
    assert not stored.local_path.exists()


def test_oss_storage_round_trip_with_fake_sdk(monkeypatch) -> None:
    uploaded: dict[str, dict] = {}

    class FakeObject:
        def __init__(self, payload: bytes) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return self._payload

    class FakeBucket:
        def __init__(self, auth, endpoint: str, bucket: str) -> None:
            self.auth = auth
            self.endpoint = endpoint
            self.bucket = bucket

        def put_object(self, key: str, content: bytes, headers=None):
            uploaded[key] = {"content": content, "headers": headers or {}}

        def get_object(self, key: str):
            return FakeObject(uploaded[key]["content"])

        def sign_url(self, method: str, key: str, expires: int) -> str:
            return f"signed://{method}/{key}?expires={expires}"

        def delete_object(self, key: str) -> None:
            uploaded.pop(key, None)

    fake_oss2 = types.SimpleNamespace(Auth=lambda ak, sk: {"ak": ak, "sk": sk}, Bucket=FakeBucket)
    monkeypatch.setitem(sys.modules, "oss2", fake_oss2)

    settings = Settings(
        storage_backend="oss",
        oss_bucket="bucket-a",
        oss_endpoint="https://oss-cn-hangzhou.aliyuncs.com",
        oss_access_key_id="ak",
        oss_access_key_secret="sk",
        oss_url_expires_seconds=60,
    )
    service = OssStorageService(settings)

    stored = service.save_bytes("candidate.pdf", b"pdf-bytes", "resumes", "application/pdf")

    assert stored.backend == "oss"
    assert stored.bucket == "bucket-a"
    assert stored.signed_url is not None
    assert service.read_bytes(stored) == b"pdf-bytes"
    assert uploaded[stored.key]["headers"]["Content-Type"] == "application/pdf"
    metadata = stored.to_metadata()
    assert metadata["backend"] == "oss"
    assert metadata["bucket"] == "bucket-a"

    service.delete(stored.key)
    assert stored.key not in uploaded


def test_get_storage_service_switches_backend(monkeypatch, tmp_path: Path) -> None:
    local = get_storage_service(Settings(storage_backend="local", storage_dir=tmp_path / "storage"))
    assert isinstance(local, LocalStorageService)

    fake_oss2 = types.SimpleNamespace(
        Auth=lambda ak, sk: {"ak": ak, "sk": sk},
        Bucket=lambda auth, endpoint, bucket: types.SimpleNamespace(
            put_object=lambda *args, **kwargs: None,
            get_object=lambda key: types.SimpleNamespace(read=lambda: b""),
            sign_url=lambda method, key, expires: "signed",
            delete_object=lambda key: None,
        ),
    )
    monkeypatch.setitem(sys.modules, "oss2", fake_oss2)

    oss = get_storage_service(
        Settings(
            storage_backend="oss",
            oss_bucket="bucket",
            oss_endpoint="https://oss-cn-hangzhou.aliyuncs.com",
            oss_access_key_id="ak",
            oss_access_key_secret="sk",
        )
    )
    assert isinstance(oss, OssStorageService)

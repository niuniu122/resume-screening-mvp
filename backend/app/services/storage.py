from __future__ import annotations

import mimetypes
import types
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from ..config import Settings, get_settings


@dataclass
class StoredObject:
    backend: str
    key: str
    filename: str
    content_type: str | None = None
    local_path: Path | None = None
    bucket: str | None = None
    signed_url: str | None = None

    def to_metadata(self) -> dict:
        return {
            "backend": self.backend,
            "key": self.key,
            "filename": self.filename,
            "content_type": self.content_type,
            "bucket": self.bucket,
            "signed_url": self.signed_url,
        }


class StorageService:
    def save_upload(self, upload: UploadFile, folder: str) -> StoredObject:
        upload.file.seek(0)
        payload = upload.file.read()
        upload.file.seek(0)
        return self.save_bytes(
            filename=upload.filename or f"{uuid.uuid4().hex}.bin",
            content=payload,
            folder=folder,
            content_type=upload.content_type,
        )

    def save_bytes(self, filename: str, content: bytes, folder: str, content_type: str | None = None) -> StoredObject:
        raise NotImplementedError

    def read_bytes(self, stored_object: StoredObject) -> bytes:
        raise NotImplementedError

    def build_reference(self, key: str, filename: str, content_type: str | None, metadata: dict | None = None) -> StoredObject:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError


class LocalStorageService(StorageService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_dir = Path(__file__).resolve().parents[2] / settings.storage_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_bytes(self, filename: str, content: bytes, folder: str, content_type: str | None = None) -> StoredObject:
        suffix = Path(filename).suffix.lower()
        safe_name = f"{folder}/{uuid.uuid4()}{suffix}"
        destination = self.base_dir / safe_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return StoredObject(
            backend="local",
            key=safe_name.replace("\\", "/"),
            filename=filename,
            content_type=content_type,
            local_path=destination,
        )

    def read_bytes(self, stored_object: StoredObject) -> bytes:
        path = stored_object.local_path or self.base_dir / stored_object.key
        return path.read_bytes()

    def build_reference(self, key: str, filename: str, content_type: str | None, metadata: dict | None = None) -> StoredObject:
        return StoredObject(
            backend="local",
            key=key,
            filename=filename,
            content_type=content_type,
            local_path=self.base_dir / key,
        )

    def delete(self, key: str) -> None:
        if not key:
            return
        path = self.base_dir / key
        if path.exists():
            path.unlink()


class DbStorageService(StorageService):
    """Store files as binary blobs in the database (PostgreSQL)."""

    def save_bytes(self, filename: str, content: bytes, folder: str, content_type: str | None = None) -> StoredObject:
        from ..db import SessionLocal
        from ..models import FileBlob

        suffix = Path(filename).suffix.lower()
        key = f"{folder}/{uuid.uuid4()}{suffix}"
        db = SessionLocal()
        try:
            blob = FileBlob(
                key=key,
                filename=filename,
                content_type=content_type,
                data=content,
                size=len(content),
            )
            db.add(blob)
            db.commit()
        finally:
            db.close()
        return StoredObject(backend="db", key=key, filename=filename, content_type=content_type)

    def read_bytes(self, stored_object: StoredObject) -> bytes:
        from ..db import SessionLocal
        from ..models import FileBlob
        from sqlalchemy import select

        db = SessionLocal()
        try:
            blob = db.scalars(select(FileBlob).where(FileBlob.key == stored_object.key)).first()
            if blob is None:
                raise FileNotFoundError(f"File not found in database: {stored_object.key}")
            return blob.data
        finally:
            db.close()

    def build_reference(self, key: str, filename: str, content_type: str | None, metadata: dict | None = None) -> StoredObject:
        return StoredObject(backend="db", key=key, filename=filename, content_type=content_type)

    def delete(self, key: str) -> None:
        from ..db import SessionLocal
        from ..models import FileBlob
        from sqlalchemy import select

        if not key:
            return
        db = SessionLocal()
        try:
            blob = db.scalars(select(FileBlob).where(FileBlob.key == key)).first()
            if blob:
                db.delete(blob)
                db.commit()
        finally:
            db.close()


class OssStorageService(StorageService):
    def __init__(self, settings: Settings) -> None:
        missing = [
            name
            for name, value in {
                "oss_bucket": settings.oss_bucket,
                "oss_endpoint": settings.oss_endpoint,
                "oss_access_key_id": settings.oss_access_key_id,
                "oss_access_key_secret": settings.oss_access_key_secret,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing OSS settings: {', '.join(missing)}")

        self.settings = settings
        oss2 = self._import_oss2()
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        self.bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket)

    def save_bytes(self, filename: str, content: bytes, folder: str, content_type: str | None = None) -> StoredObject:
        suffix = Path(filename).suffix.lower()
        key = f"{folder}/{uuid.uuid4()}{suffix}"
        headers = {}
        resolved_content_type = content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        headers["Content-Type"] = resolved_content_type
        self.bucket.put_object(key, content, headers=headers)
        return StoredObject(
            backend="oss",
            key=key,
            filename=filename,
            content_type=resolved_content_type,
            bucket=self.settings.oss_bucket,
            signed_url=self.bucket.sign_url("GET", key, self.settings.oss_url_expires_seconds),
        )

    def read_bytes(self, stored_object: StoredObject) -> bytes:
        return self.bucket.get_object(stored_object.key).read()

    def build_reference(self, key: str, filename: str, content_type: str | None, metadata: dict | None = None) -> StoredObject:
        signed_url = None
        if key:
            signed_url = self.bucket.sign_url("GET", key, self.settings.oss_url_expires_seconds)
        return StoredObject(
            backend="oss",
            key=key,
            filename=filename,
            content_type=content_type,
            bucket=(metadata or {}).get("bucket", self.settings.oss_bucket),
            signed_url=signed_url,
        )

    def delete(self, key: str) -> None:
        if not key:
            return
        self.bucket.delete_object(key)

    @staticmethod
    def _import_oss2() -> types.ModuleType:
        try:
            import oss2  # type: ignore
        except ImportError as exc:  # pragma: no cover - exercised in deployment, not local tests
            raise RuntimeError("oss2 is required when storage_backend=oss.") from exc
        return oss2


def get_storage_service(settings: Settings | None = None) -> StorageService:
    settings = settings or get_settings()
    if settings.storage_backend == "local":
        return LocalStorageService(settings)
    if settings.storage_backend == "db":
        return DbStorageService()
    if settings.storage_backend == "oss":
        return OssStorageService(settings)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unsupported storage backend.")

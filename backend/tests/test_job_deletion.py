from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.config import Settings
from app.db import SessionLocal, init_db
from app.main import app
from app.models import (
    AuditLog,
    CandidateProfile,
    EvaluationResult,
    Job,
    RecruiterInterviewSession,
    ResumeSubmission,
    ReviewDecision,
    ScreeningProfileVersion,
)
from app.services.storage import LocalStorageService


client = TestClient(app)


def reset_database() -> None:
    init_db()
    db = SessionLocal()
    try:
        db.execute(delete(ReviewDecision))
        db.execute(delete(EvaluationResult))
        db.execute(delete(CandidateProfile))
        db.execute(delete(ResumeSubmission))
        db.execute(delete(ScreeningProfileVersion))
        db.execute(delete(RecruiterInterviewSession))
        db.execute(delete(Job))
        db.execute(delete(AuditLog))
        db.commit()
    finally:
        db.close()


def test_delete_job_removes_history_and_uploaded_files(tmp_path: Path) -> None:
    reset_database()

    from app import main as main_module

    original_storage_service = main_module.storage_service
    original_client = main_module.recruiting_engine.client
    main_module.storage_service = LocalStorageService(Settings(storage_backend="local", storage_dir=tmp_path / "storage"))
    main_module.recruiting_engine.client = None

    try:
        jd_file = tmp_path / "job.txt"
        jd_file.write_text("Foreign trade manager, fluent English, 3+ years experience.", encoding="utf-8")
        with jd_file.open("rb") as file_handle:
            response = client.post("/jobs/import-jd", files={"file": ("job.txt", file_handle, "text/plain")})
        assert response.status_code == 200
        job_id = response.json()["job"]["id"]

        draft = client.post(
            f"/jobs/{job_id}/interview/answer",
            json={"answers": [{"question_id": "hard-rules", "answer": "3+ years experience and business English."}]},
        ).json()
        freeze = client.post(f"/jobs/{job_id}/freeze-profile", json={"profile": draft})
        assert freeze.status_code == 200

        resume_file = tmp_path / "candidate.txt"
        resume_file.write_text("Alice Zhang\n5 years foreign trade\nBusiness English", encoding="utf-8")
        with resume_file.open("rb") as file_handle:
            upload = client.post(
                f"/jobs/{job_id}/resumes",
                files={"files": ("candidate.txt", file_handle, "text/plain")},
            )
        assert upload.status_code == 200

        db = SessionLocal()
        try:
            job = db.get(Job, job_id)
            assert job is not None
            stored_paths = [job.jd_storage_path] + [submission.storage_path for submission in job.resume_submissions]
        finally:
            db.close()

        delete_response = client.delete(f"/jobs/{job_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted_job_id"] == job_id
        assert delete_response.json()["cleanup_warnings"] == []

        assert client.get(f"/jobs/{job_id}").status_code == 404
        assert client.get("/jobs").json()["items"] == []

        db = SessionLocal()
        try:
            assert db.query(Job).count() == 0
            assert db.query(RecruiterInterviewSession).count() == 0
            assert db.query(ScreeningProfileVersion).count() == 0
            assert db.query(ResumeSubmission).count() == 0
            assert db.query(CandidateProfile).count() == 0
            assert db.query(EvaluationResult).count() == 0
        finally:
            db.close()

        for key in stored_paths:
            if key:
                assert not (main_module.storage_service.base_dir / key).exists()
    finally:
        main_module.storage_service = original_storage_service
        main_module.recruiting_engine.client = original_client

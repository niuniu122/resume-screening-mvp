from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import SessionLocal, get_db, init_db
from .models import (
    AuditLog,
    CandidateProfile,
    EvaluationResult,
    Job,
    RecruiterInterviewSession,
    ResumeSubmission,
    ReviewDecision,
    ScreeningProfileVersion,
)
from .schemas import (
    AnswerRequest,
    DashboardEvaluationItem,
    DashboardResponse,
    DashboardStats,
    DeleteJobResponse,
    DecisionRequest,
    EvaluationDetail,
    FreezeProfileRequest,
    InterviewSessionView,
    JobDetail,
    JobListResponse,
    JobSetupResponse,
    JobSummary,
    ParsedJD,
    ProfileVersionView,
    QuestionAnswer,
    ResumeUploadResult,
    ScreeningProfileDraft,
)
from .services.document_parser import extract_text_from_bytes, normalize_text
from .services.recruiting_engine import RecruitingEngine
from .services.storage import StoredObject, get_storage_service

settings = get_settings()
logger = logging.getLogger(__name__)
recruiting_engine = RecruitingEngine()
storage_service = get_storage_service(settings)
frontend_out_dir = Path(__file__).resolve().parents[2] / "frontend" / "out"


@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.storage_backend == "local":
        Path(__file__).resolve().parents[1].joinpath(settings.storage_dir).mkdir(parents=True, exist_ok=True)
    application.state.database_startup_error = None
    try:
        await asyncio.wait_for(asyncio.to_thread(init_db), timeout=15)
    except Exception as exc:  # noqa: BLE001
        application.state.database_startup_error = str(exc)
        logger.exception("Database initialization failed during startup.")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def audit(db: Session, entity_type: str, entity_id: str, action: str, actor: str, payload: dict) -> None:
    db.add(
        AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            payload=payload,
        )
    )


def build_stored_object(key: str | None, filename: str, content_type: str | None, metadata: dict | None = None) -> StoredObject:
    if not key:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stored object reference is missing.")
    return storage_service.build_reference(key=key, filename=filename, content_type=content_type, metadata=metadata)


def profile_to_dict(profile: ScreeningProfileVersion) -> dict:
    return {
        "role_summary": profile.role_summary,
        "hard_constraints": profile.hard_constraints,
        "soft_constraints": profile.soft_constraints,
        "scoring_dimensions": profile.scoring_dimensions,
        "output_requirements": profile.output_requirements,
        "interview_focus": profile.interview_focus,
        "boundaries": profile.boundaries,
        "prompt_bundle": profile.prompt_bundle,
    }


def serialize_interview_session(session: RecruiterInterviewSession | None) -> InterviewSessionView | None:
    if session is None:
        return None
    return InterviewSessionView(
        id=session.id,
        questions=session.questions,
        answers=[QuestionAnswer(**item) for item in session.answers],
        draft_profile=ScreeningProfileDraft(**session.draft_profile) if session.draft_profile else None,
    )


def serialize_profile(profile: ScreeningProfileVersion | None) -> ProfileVersionView | None:
    if profile is None:
        return None
    return ProfileVersionView(
        id=profile.id,
        version=profile.version,
        status=profile.status,
        created_at=profile.created_at,
        role_summary=profile.role_summary,
        hard_constraints=profile.hard_constraints,
        soft_constraints=profile.soft_constraints,
        scoring_dimensions=profile.scoring_dimensions,
        output_requirements=profile.output_requirements,
        interview_focus=profile.interview_focus,
        boundaries=profile.boundaries,
        prompt_bundle=profile.prompt_bundle,
    )


def build_job_detail(db: Session, job: Job) -> JobDetail:
    current_profile = None
    current_profile_version = None
    if job.current_profile_version_id:
        current_profile = db.get(ScreeningProfileVersion, job.current_profile_version_id)
        current_profile_version = current_profile.version if current_profile else None

    return JobDetail(
        id=job.id,
        title=job.title,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        current_profile_version=current_profile_version,
        source_type=job.source_type,
        jd_text=job.jd_text,
        parsed_jd=ParsedJD(**job.parsed_jd),
        interview_session=serialize_interview_session(job.interview_session),
        current_profile=serialize_profile(current_profile),
    )


def collect_job_storage_keys(job: Job) -> list[str]:
    keys: list[str] = []
    if job.jd_storage_path:
        keys.append(job.jd_storage_path)
    for submission in job.resume_submissions:
        if submission.storage_path:
            keys.append(submission.storage_path)
    return list(dict.fromkeys(keys))


def cleanup_storage_keys(keys: list[str]) -> list[str]:
    warnings: list[str] = []
    for key in keys:
        try:
            storage_service.delete(key)
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{key}: {exc}")
    return warnings


def process_resume_submission(submission_id: str) -> None:
    db = SessionLocal()
    try:
        submission = db.get(ResumeSubmission, submission_id)
        if submission is None:
            return
        job = db.get(Job, submission.job_id)
        if job is None or not job.current_profile_version_id:
            submission.status = "failed"
            submission.error_message = "Job or frozen profile is missing."
            db.commit()
            return

        profile = db.get(ScreeningProfileVersion, job.current_profile_version_id)
        if profile is None:
            submission.status = "failed"
            submission.error_message = "Frozen profile not found."
            db.commit()
            return

        submission.status = "processing"
        db.commit()

        if not submission.extracted_text:
            storage_meta = submission.parse_meta.get("storage") if submission.parse_meta else {}
            stored_object = build_stored_object(
                key=submission.storage_path,
                filename=submission.filename,
                content_type=submission.content_type,
                metadata=storage_meta,
            )
            text, parse_meta = extract_text_from_bytes(submission.filename, storage_service.read_bytes(stored_object))
            submission.extracted_text = text
            submission.parse_meta = {**submission.parse_meta, **parse_meta, "storage": stored_object.to_metadata()}
            db.commit()

        filename_stem = Path(submission.filename).stem
        candidate_name_hint = submission.candidate_name or filename_stem
        result = recruiting_engine.evaluate_resume(
            profile_to_dict(profile),
            submission.extracted_text or "",
            candidate_name_hint,
        )
        submission.status = "completed"
        if not submission.candidate_name:
            submission.candidate_name = result.data["candidate_name"] or filename_stem

        candidate_profile = submission.candidate_profile or CandidateProfile(
            job_id=job.id,
            resume_submission_id=submission.id,
        )
        candidate_profile.extracted_facts = result.data["facts"]
        candidate_profile.summary = {
            "candidate_name": result.data["candidate_name"],
            "headline_metrics": result.data["facts"].get("headline_metrics", []),
        }
        db.add(candidate_profile)

        evaluation = submission.evaluation or EvaluationResult(
            job_id=job.id,
            resume_submission_id=submission.id,
            profile_version_id=profile.id,
        )
        evaluation.status = result.data["status"]
        evaluation.overall_score = result.data["overall_score"]
        evaluation.hard_rule_results = result.data["hard_rule_results"]
        evaluation.dimension_scores = result.data["dimension_scores"]
        evaluation.evidence = result.data["evidence"]
        evaluation.warnings = result.data["warnings"]
        evaluation.info_gaps = result.data["info_gaps"]
        evaluation.interview_questions = result.data["interview_questions"]
        evaluation.final_recommendation = result.data["final_recommendation"]
        evaluation.markdown_report = result.data["markdown_report"]
        evaluation.raw_json = result.data
        evaluation.model_version = result.model_version
        evaluation.prompt_bundle_version = profile.version
        evaluation.execution_state = "completed"
        db.add(evaluation)

        audit(
            db,
            entity_type="resume_submission",
            entity_id=submission.id,
            action="resume_evaluated",
            actor="system",
            payload={"status": evaluation.status, "score": evaluation.overall_score},
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        submission = db.get(ResumeSubmission, submission_id)
        if submission is not None:
            submission.status = "failed"
            submission.error_message = str(exc)
            db.commit()
    finally:
        db.close()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/jobs", response_model=JobListResponse)
def list_jobs(db: Session = Depends(get_db)) -> JobListResponse:
    jobs = db.scalars(select(Job).order_by(desc(Job.created_at))).all()
    items = []
    for job in jobs:
        current_profile = db.get(ScreeningProfileVersion, job.current_profile_version_id) if job.current_profile_version_id else None
        items.append(
            JobSummary(
                id=job.id,
                title=job.title,
                status=job.status,
                created_at=job.created_at,
                updated_at=job.updated_at,
                current_profile_version=current_profile.version if current_profile else None,
            )
        )
    return JobListResponse(items=items)


@app.get("/jobs/{job_id}", response_model=JobSetupResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobSetupResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    return JobSetupResponse(job=build_job_detail(db, job))


@app.delete("/jobs/{job_id}", response_model=DeleteJobResponse)
def delete_job(job_id: str, db: Session = Depends(get_db)) -> DeleteJobResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    title = job.title
    storage_keys = collect_job_storage_keys(job)
    submission_count = len(job.resume_submissions)

    job.current_profile_version_id = None
    db.flush()
    audit(
        db,
        "job",
        job.id,
        "job_deleted",
        settings.recruiter_default_name,
        {"title": title, "resume_count": submission_count},
    )
    db.delete(job)
    db.commit()

    cleanup_warnings = cleanup_storage_keys(storage_keys)
    return DeleteJobResponse(
        deleted_job_id=job_id,
        deleted_title=title,
        cleanup_warnings=cleanup_warnings,
    )


def _import_jd_background(job_id: str, clean_text: str) -> None:
    """Run JD parsing + question generation in background."""
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None:
            return
        heuristic_parsed = recruiting_engine._heuristic_parse_jd(clean_text)
        parse_result = recruiting_engine.parse_jd(clean_text)
        question_result = recruiting_engine.generate_follow_up_questions(heuristic_parsed, clean_text)

        job.title = parse_result.data["title"]
        job.parsed_jd = parse_result.data
        job.status = "interview_pending"
        session = RecruiterInterviewSession(
            job=job,
            questions=question_result.data["questions"],
            answers=[],
            draft_profile=None,
        )
        db.add(session)
        audit(db, "job", job.id, "job_imported", settings.recruiter_default_name,
              {"title": job.title, "source_type": job.source_type})
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job = db.get(Job, job_id)
        if job:
            job.status = "import_failed"
            db.commit()
    finally:
        db.close()


@app.post("/jobs/import-jd")
async def import_jd(
    background_tasks: BackgroundTasks,
    jd_text: Annotated[str | None, Form()] = None,
    file: UploadFile | None = File(None),
    db: Session = Depends(get_db),
) -> dict:
    if file is None and not jd_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide JD text or upload a file.")

    source_type = "text"
    stored_object = None
    if file is not None:
        stored_object = storage_service.save_upload(file, "jobs")
        jd_text, _ = extract_text_from_bytes(file.filename or stored_object.filename, storage_service.read_bytes(stored_object))
        source_type = "file"
    assert jd_text is not None
    clean_text = normalize_text(jd_text)
    heuristic_parsed = recruiting_engine._heuristic_parse_jd(clean_text)

    job = Job(
        title=heuristic_parsed["title"],
        status="importing",
        source_type=source_type,
        jd_text=clean_text,
        parsed_jd=heuristic_parsed,
        jd_storage_path=stored_object.key if stored_object else None,
    )
    db.add(job)
    db.flush()
    db.commit()
    db.refresh(job)

    background_tasks.add_task(_import_jd_background, job.id, clean_text)
    return {"status": "importing", "job_id": job.id}


@app.get("/jobs/{job_id}/import-status")
def get_import_status(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status == "importing":
        return {"status": "importing"}
    if job.status == "import_failed":
        return {"status": "failed"}
    return {"status": "done", "job_id": job.id}


def _compile_profile_background(job_id: str, answers: list[dict]) -> None:
    """Run compile_profile in background to avoid Render's 60s request timeout."""
    db = SessionLocal()
    try:
        job = db.get(Job, job_id)
        if job is None or job.interview_session is None:
            return
        draft = recruiting_engine.compile_profile(job.parsed_jd, job.jd_text, answers)
        job.interview_session.answers = answers
        job.interview_session.draft_profile = draft.data
        job.status = "profile_draft"
        audit(
            db,
            "job",
            job.id,
            "interview_answered",
            settings.recruiter_default_name,
            {"answers_count": len(answers)},
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        job = db.get(Job, job_id)
        if job and job.interview_session:
            job.interview_session.draft_profile = None
            job.status = "interview_pending"
            db.commit()
    finally:
        db.close()


@app.post("/jobs/{job_id}/interview/answer")
async def answer_interview(
    job_id: str,
    payload: AnswerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> dict:
    job = db.get(Job, job_id)
    if job is None or job.interview_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job or interview session not found.")

    answers = [item.model_dump() for item in payload.answers]
    job.interview_session.answers = answers
    job.status = "compiling_profile"
    db.commit()

    background_tasks.add_task(_compile_profile_background, job_id, answers)
    return {"status": "compiling", "job_id": job_id}


@app.get("/jobs/{job_id}/compile-status")
def get_compile_status(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status == "compiling_profile":
        return {"status": "compiling"}
    if job.interview_session and job.interview_session.draft_profile:
        return {"status": "done", "draft": job.interview_session.draft_profile}
    return {"status": "pending"}


@app.post("/jobs/{job_id}/freeze-profile", response_model=ProfileVersionView)
def freeze_profile(job_id: str, payload: FreezeProfileRequest, db: Session = Depends(get_db)) -> ProfileVersionView:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    prompt_bundle = recruiting_engine._build_prompt_bundle(
        title=job.parsed_jd.get("title", job.title),
        parsed_jd=job.parsed_jd,
        role_summary=payload.profile.role_summary,
        hard_constraints=[item.model_dump() for item in payload.profile.hard_constraints],
        scoring_dimensions=[item.model_dump() for item in payload.profile.scoring_dimensions],
        boundaries=payload.profile.boundaries,
        output_requirements=payload.profile.output_requirements,
    )

    latest_version = db.scalar(select(func.max(ScreeningProfileVersion.version)).where(ScreeningProfileVersion.job_id == job_id))
    version_number = int(latest_version or 0) + 1
    profile = ScreeningProfileVersion(
        job_id=job_id,
        version=version_number,
        status="frozen",
        role_summary=payload.profile.role_summary,
        hard_constraints=[item.model_dump() for item in payload.profile.hard_constraints],
        soft_constraints=[item.model_dump() for item in payload.profile.soft_constraints],
        scoring_dimensions=[item.model_dump() for item in payload.profile.scoring_dimensions],
        output_requirements=payload.profile.output_requirements,
        interview_focus=payload.profile.interview_focus,
        boundaries=payload.profile.boundaries,
        prompt_bundle=prompt_bundle,
    )
    db.add(profile)
    db.flush()
    job.current_profile_version_id = profile.id
    job.status = "screening_ready"
    audit(
        db,
        "job",
        job.id,
        "profile_frozen",
        settings.recruiter_default_name,
        {"version": version_number},
    )
    db.commit()
    db.refresh(profile)
    return serialize_profile(profile)


@app.post("/jobs/{job_id}/resumes", response_model=ResumeUploadResult)
async def upload_resumes(
    job_id: str,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
) -> ResumeUploadResult:
    job = db.get(Job, job_id)
    if job is None or not job.current_profile_version_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Freeze the screening profile before uploading resumes.")

    submission_ids = []
    for file in files:
        stored_object = storage_service.save_upload(file, "resumes")
        extracted_text, meta = extract_text_from_bytes(file.filename or stored_object.filename, storage_service.read_bytes(stored_object))
        submission = ResumeSubmission(
            job_id=job_id,
            filename=file.filename or stored_object.filename,
            content_type=file.content_type,
            storage_path=stored_object.key,
            extracted_text=extracted_text,
            parse_meta={**meta, "storage": stored_object.to_metadata()},
            status="uploaded",
        )
        db.add(submission)
        db.flush()
        submission_ids.append(submission.id)
        background_tasks.add_task(process_resume_submission, submission.id)
        audit(
            db,
            "resume_submission",
            submission.id,
            "resume_uploaded",
            settings.recruiter_default_name,
            {"filename": submission.filename},
        )

    job.status = "screening_in_progress"
    db.commit()
    return ResumeUploadResult(submission_ids=submission_ids)


@app.get("/jobs/{job_id}/dashboard", response_model=DashboardResponse)
def get_dashboard(job_id: str, db: Session = Depends(get_db)) -> DashboardResponse:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    submissions = db.scalars(
        select(ResumeSubmission).where(ResumeSubmission.job_id == job_id).order_by(desc(ResumeSubmission.updated_at))
    ).all()
    stats = DashboardStats(total=len(submissions))
    items = []
    for submission in submissions:
        evaluation = submission.evaluation
        if submission.status == "processing":
            stats.processing += 1
        if submission.status == "failed":
            stats.failed += 1
        if evaluation is not None:
            if hasattr(stats, evaluation.status):
                setattr(stats, evaluation.status, getattr(stats, evaluation.status) + 1)
            items.append(
                DashboardEvaluationItem(
                    evaluation_id=evaluation.id,
                    submission_id=submission.id,
                    candidate_name=submission.candidate_name,
                    filename=submission.filename,
                    submission_status=submission.status,
                    evaluation_status=evaluation.status,
                    overall_score=evaluation.overall_score,
                    manual_decision=evaluation.manual_decision,
                    updated_at=evaluation.updated_at,
                    risk_summary=evaluation.warnings[:2],
                )
            )
        else:
            items.append(
                DashboardEvaluationItem(
                    submission_id=submission.id,
                    candidate_name=submission.candidate_name,
                    filename=submission.filename,
                    submission_status=submission.status,
                    updated_at=submission.updated_at,
                    risk_summary=[],
                )
            )

    return DashboardResponse(job=build_job_detail(db, job), stats=stats, evaluations=items)


@app.get("/evaluations/{evaluation_id}", response_model=EvaluationDetail)
def get_evaluation(evaluation_id: str, db: Session = Depends(get_db)) -> EvaluationDetail:
    evaluation = db.get(EvaluationResult, evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found.")
    job = db.get(Job, evaluation.job_id)
    submission = db.get(ResumeSubmission, evaluation.resume_submission_id)
    return EvaluationDetail(
        id=evaluation.id,
        job_id=evaluation.job_id,
        job_title=job.title if job else "未知岗位",
        submission_id=evaluation.resume_submission_id,
        candidate_name=submission.candidate_name if submission else None,
        filename=submission.filename if submission else "未知文件",
        status=evaluation.status,
        overall_score=evaluation.overall_score,
        hard_rule_results=evaluation.hard_rule_results,
        dimension_scores=evaluation.dimension_scores,
        evidence=evaluation.evidence,
        warnings=evaluation.warnings,
        info_gaps=evaluation.info_gaps,
        interview_questions=evaluation.interview_questions,
        final_recommendation=evaluation.final_recommendation,
        markdown_report=evaluation.markdown_report,
        manual_decision=evaluation.manual_decision,
        manual_reason=evaluation.manual_reason,
        created_at=evaluation.created_at,
        updated_at=evaluation.updated_at,
    )


@app.post("/evaluations/{evaluation_id}/decision", response_model=EvaluationDetail)
def submit_decision(evaluation_id: str, payload: DecisionRequest, db: Session = Depends(get_db)) -> EvaluationDetail:
    evaluation = db.get(EvaluationResult, evaluation_id)
    if evaluation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found.")

    reviewer_name = payload.reviewer_name or settings.recruiter_default_name
    evaluation.manual_decision = payload.decision
    evaluation.manual_reason = payload.comment
    db.add(
        ReviewDecision(
            evaluation_id=evaluation_id,
            reviewer_name=reviewer_name,
            decision=payload.decision,
            comment=payload.comment,
        )
    )
    audit(
        db,
        "evaluation_result",
        evaluation_id,
        "manual_decision",
        reviewer_name,
        {"decision": payload.decision, "comment": payload.comment},
    )
    db.commit()
    return get_evaluation(evaluation_id, db)


@app.get("/", include_in_schema=False)
def serve_frontend_index() -> Response:
    candidate = frontend_out_dir / "index.html"
    if not candidate.exists():
        return JSONResponse({"status": "ok", "service": settings.app_name, "health": "/health"})
    return FileResponse(candidate)


@app.get("/{full_path:path}", include_in_schema=False)
def serve_frontend(full_path: str) -> FileResponse:
    if not frontend_out_dir.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontend bundle is not available.")

    requested_path = frontend_out_dir / full_path
    if full_path == "":
        candidate = frontend_out_dir / "index.html"
    elif requested_path.is_dir():
        candidate = requested_path / "index.html"
    elif requested_path.is_file():
        candidate = requested_path
    elif (frontend_out_dir / full_path / "index.html").is_file():
        candidate = frontend_out_dir / full_path / "index.html"
    else:
        candidate = frontend_out_dir / "index.html"

    if not candidate.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontend file not found.")
    return FileResponse(candidate)

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def uuid_str() -> str:
    return str(uuid.uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), default="text", nullable=False)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    parsed_jd: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    jd_storage_path: Mapped[str | None] = mapped_column(String(512))
    current_profile_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("screening_profile_versions.id"))

    interview_session: Mapped["RecruiterInterviewSession"] = relationship(
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="RecruiterInterviewSession.job_id",
    )
    profile_versions: Mapped[list["ScreeningProfileVersion"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        foreign_keys="ScreeningProfileVersion.job_id",
        order_by="ScreeningProfileVersion.version",
    )
    resume_submissions: Mapped[list["ResumeSubmission"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        foreign_keys="ResumeSubmission.job_id",
    )
    evaluations: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        foreign_keys="EvaluationResult.job_id",
    )


class RecruiterInterviewSession(TimestampMixin, Base):
    __tablename__ = "recruiter_interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), unique=True, nullable=False)
    questions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    answers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    draft_profile: Mapped[dict | None] = mapped_column(JSON)

    job: Mapped[Job] = relationship(back_populates="interview_session", foreign_keys=[job_id])


class ScreeningProfileVersion(TimestampMixin, Base):
    __tablename__ = "screening_profile_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="frozen", nullable=False)
    role_summary: Mapped[str] = mapped_column(Text, nullable=False)
    hard_constraints: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    soft_constraints: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    scoring_dimensions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    output_requirements: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    interview_focus: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    boundaries: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    prompt_bundle: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    job: Mapped[Job] = relationship(back_populates="profile_versions", foreign_keys=[job_id])
    evaluations: Mapped[list["EvaluationResult"]] = relationship(
        back_populates="profile_version",
        cascade="all, delete-orphan",
        foreign_keys="EvaluationResult.profile_version_id",
    )


class ResumeSubmission(TimestampMixin, Base):
    __tablename__ = "resume_submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100))
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="uploaded", nullable=False)
    candidate_name: Mapped[str | None] = mapped_column(String(255))
    file_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    parse_meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="resume_submissions", foreign_keys=[job_id])
    candidate_profile: Mapped["CandidateProfile"] = relationship(
        back_populates="resume_submission",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="CandidateProfile.resume_submission_id",
    )
    evaluation: Mapped["EvaluationResult"] = relationship(
        back_populates="resume_submission",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="EvaluationResult.resume_submission_id",
    )


class CandidateProfile(TimestampMixin, Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    resume_submission_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_submissions.id"), unique=True, nullable=False)
    extracted_facts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    resume_submission: Mapped[ResumeSubmission] = relationship(
        back_populates="candidate_profile",
        foreign_keys=[resume_submission_id],
    )


class EvaluationResult(TimestampMixin, Base):
    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id"), nullable=False)
    resume_submission_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_submissions.id"), unique=True, nullable=False)
    profile_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("screening_profile_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)
    hard_rule_results: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    dimension_scores: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    evidence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    info_gaps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    interview_questions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    final_recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    markdown_report: Mapped[str] = mapped_column(Text, nullable=False)
    raw_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_bundle_version: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_state: Mapped[str] = mapped_column(String(50), default="completed", nullable=False)
    manual_decision: Mapped[str | None] = mapped_column(String(50))
    manual_reason: Mapped[str | None] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="evaluations", foreign_keys=[job_id])
    resume_submission: Mapped[ResumeSubmission] = relationship(
        back_populates="evaluation",
        foreign_keys=[resume_submission_id],
    )
    profile_version: Mapped[ScreeningProfileVersion] = relationship(
        back_populates="evaluations",
        foreign_keys=[profile_version_id],
    )
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        foreign_keys="ReviewDecision.evaluation_id",
    )


class ReviewDecision(TimestampMixin, Base):
    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    evaluation_id: Mapped[str] = mapped_column(String(36), ForeignKey("evaluation_results.id"), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    evaluation: Mapped[EvaluationResult] = relationship(
        back_populates="review_decisions",
        foreign_keys=[evaluation_id],
    )


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid_str)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

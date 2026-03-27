from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ParsedJD(BaseModel):
    title: str
    seniority: str | None = None
    industry_tags: list[str] = Field(default_factory=list)
    language_requirements: list[str] = Field(default_factory=list)
    experience_years: int | None = None
    degree_requirement: str | None = None
    summary: str
    risk_flags: list[str] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    id: str
    title: str
    prompt: str
    category: str


class QuestionAnswer(BaseModel):
    question_id: str
    answer: str


class AnswerRequest(BaseModel):
    answers: list[QuestionAnswer]


class ConstraintRule(BaseModel):
    id: str
    label: str
    description: str
    field: str
    operator: str
    value: Any
    required: bool = True
    source: str = "ai-generated"
    keywords: list[str] = Field(default_factory=list)


class ScoringDimension(BaseModel):
    id: str
    name: str
    weight: int
    description: str
    keywords: list[str] = Field(default_factory=list)


class PromptBundle(BaseModel):
    role: str
    context: str
    goals: list[str]
    kill_switch: list[str]
    evaluation_dimensions: list[dict[str, Any]]
    boundaries: list[str]
    output_schema: dict[str, Any]
    rendered_prompt: str


class ScreeningProfileDraft(BaseModel):
    role_summary: str
    hard_constraints: list[ConstraintRule]
    soft_constraints: list[ConstraintRule]
    scoring_dimensions: list[ScoringDimension]
    output_requirements: list[str]
    interview_focus: list[str]
    boundaries: list[str]
    prompt_bundle: PromptBundle


class InterviewSessionView(BaseModel):
    id: str
    questions: list[GeneratedQuestion]
    answers: list[QuestionAnswer]
    draft_profile: ScreeningProfileDraft | None = None


class ProfileVersionView(ScreeningProfileDraft):
    id: str
    version: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class JobSummary(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    updated_at: datetime
    current_profile_version: int | None = None

    model_config = ConfigDict(from_attributes=True)


class JobDetail(JobSummary):
    source_type: str
    jd_text: str
    parsed_jd: ParsedJD
    interview_session: InterviewSessionView | None = None
    current_profile: ProfileVersionView | None = None


class JobSetupResponse(BaseModel):
    job: JobDetail


class DeleteJobResponse(BaseModel):
    deleted_job_id: str
    deleted_title: str
    cleanup_warnings: list[str] = Field(default_factory=list)


class FreezeProfileRequest(BaseModel):
    profile: ScreeningProfileDraft


class DecisionRequest(BaseModel):
    decision: str
    reviewer_name: str | None = None
    comment: str | None = None


class DashboardStats(BaseModel):
    total: int = 0
    auto_reject_review: int = 0
    manual_review: int = 0
    recommend_interview: int = 0
    recommend_reject: int = 0
    processing: int = 0
    failed: int = 0


class DashboardEvaluationItem(BaseModel):
    evaluation_id: str | None = None
    submission_id: str
    candidate_name: str | None = None
    filename: str
    submission_status: str
    evaluation_status: str | None = None
    overall_score: float | None = None
    manual_decision: str | None = None
    updated_at: datetime
    risk_summary: list[str] = Field(default_factory=list)


class DashboardResponse(BaseModel):
    job: JobDetail
    stats: DashboardStats
    evaluations: list[DashboardEvaluationItem]


class EvaluationDetail(BaseModel):
    id: str
    job_id: str
    job_title: str
    submission_id: str
    candidate_name: str | None = None
    filename: str
    status: str
    overall_score: float | None = None
    hard_rule_results: list[dict[str, Any]]
    dimension_scores: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    warnings: list[str]
    info_gaps: list[str]
    interview_questions: list[str]
    final_recommendation: str
    markdown_report: str
    manual_decision: str | None = None
    manual_reason: str | None = None
    created_at: datetime
    updated_at: datetime


class ResumeUploadResult(BaseModel):
    submission_ids: list[str]


class JobListResponse(BaseModel):
    items: list[JobSummary]

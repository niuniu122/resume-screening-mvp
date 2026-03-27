export type JobStatus =
  | "draft"
  | "interview_pending"
  | "profile_draft"
  | "screening_ready"
  | "screening_in_progress";

export type EvaluationStatus =
  | "auto_reject_review"
  | "manual_review"
  | "recommend_interview"
  | "recommend_reject";

export interface ParsedJD {
  title: string;
  seniority?: string | null;
  industry_tags: string[];
  language_requirements: string[];
  experience_years?: number | null;
  degree_requirement?: string | null;
  summary: string;
  risk_flags: string[];
}

export interface GeneratedQuestion {
  id: string;
  title: string;
  prompt: string;
  category: string;
}

export interface QuestionAnswer {
  question_id: string;
  answer: string;
}

export interface ConstraintRule {
  id: string;
  label: string;
  description: string;
  field: string;
  operator: string;
  value: string | number | string[] | Record<string, unknown>;
  required: boolean;
  source: string;
  keywords: string[];
}

export interface ScoringDimension {
  id: string;
  name: string;
  weight: number;
  description: string;
  keywords: string[];
}

export interface PromptBundle {
  role: string;
  context: string;
  goals: string[];
  kill_switch: string[];
  evaluation_dimensions: Array<Record<string, unknown>>;
  boundaries: string[];
  output_schema: Record<string, unknown>;
  rendered_prompt: string;
}

export interface ScreeningProfileDraft {
  role_summary: string;
  hard_constraints: ConstraintRule[];
  soft_constraints: ConstraintRule[];
  scoring_dimensions: ScoringDimension[];
  output_requirements: string[];
  interview_focus: string[];
  boundaries: string[];
  prompt_bundle: PromptBundle;
}

export interface InterviewSessionView {
  id: string;
  questions: GeneratedQuestion[];
  answers: QuestionAnswer[];
  draft_profile?: ScreeningProfileDraft | null;
}

export interface ProfileVersionView extends ScreeningProfileDraft {
  id: string;
  version: number;
  status: string;
  created_at: string;
}

export interface JobSummary {
  id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  current_profile_version?: number | null;
}

export interface JobDetail extends JobSummary {
  source_type: string;
  jd_text: string;
  parsed_jd: ParsedJD;
  interview_session?: InterviewSessionView | null;
  current_profile?: ProfileVersionView | null;
}

export interface JobSetupResponse {
  job: JobDetail;
}

export interface DeleteJobResponse {
  deleted_job_id: string;
  deleted_title: string;
  cleanup_warnings: string[];
}

export interface JobListResponse {
  items: JobSummary[];
}

export interface DashboardStats {
  total: number;
  auto_reject_review: number;
  manual_review: number;
  recommend_interview: number;
  recommend_reject: number;
  processing: number;
  failed: number;
}

export interface DashboardEvaluationItem {
  evaluation_id?: string | null;
  submission_id: string;
  candidate_name?: string | null;
  filename: string;
  submission_status: string;
  evaluation_status?: EvaluationStatus | null;
  overall_score?: number | null;
  manual_decision?: string | null;
  updated_at: string;
  risk_summary: string[];
}

export interface DashboardResponse {
  job: JobDetail;
  stats: DashboardStats;
  evaluations: DashboardEvaluationItem[];
}

export interface EvaluationDetail {
  id: string;
  job_id: string;
  job_title: string;
  submission_id: string;
  candidate_name?: string | null;
  filename: string;
  status: EvaluationStatus;
  overall_score?: number | null;
  hard_rule_results: Array<Record<string, unknown>>;
  dimension_scores: Array<Record<string, unknown>>;
  evidence: Array<Record<string, unknown>>;
  warnings: string[];
  info_gaps: string[];
  interview_questions: string[];
  final_recommendation: string;
  markdown_report: string;
  manual_decision?: string | null;
  manual_reason?: string | null;
  created_at: string;
  updated_at: string;
}

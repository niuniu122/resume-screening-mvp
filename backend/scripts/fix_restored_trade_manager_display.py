from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "screening.db"

JOB_ID_TO_KEEP = "9062bbe7-5f0b-4b5a-8541-5680bfe7f333"
BROKEN_JOB_ID_TO_DELETE = "7330e8bf-7116-4d22-ad58-5c00315af523"
BLUE_SUBMISSION_ID = "925af695-e957-479a-8706-5627c54827f4"


def delete_job(cur: sqlite3.Cursor, job_id: str) -> None:
    submission_ids = [row[0] for row in cur.execute("SELECT id FROM resume_submissions WHERE job_id = ?", (job_id,)).fetchall()]
    evaluation_ids = [row[0] for row in cur.execute("SELECT id FROM evaluation_results WHERE job_id = ?", (job_id,)).fetchall()]
    if evaluation_ids:
        cur.executemany("DELETE FROM review_decisions WHERE evaluation_id = ?", [(item,) for item in evaluation_ids])
    cur.execute("DELETE FROM evaluation_results WHERE job_id = ?", (job_id,))
    cur.execute("DELETE FROM candidate_profiles WHERE job_id = ?", (job_id,))
    cur.execute("DELETE FROM resume_submissions WHERE job_id = ?", (job_id,))
    cur.execute("DELETE FROM screening_profile_versions WHERE job_id = ?", (job_id,))
    cur.execute("DELETE FROM recruiter_interview_sessions WHERE job_id = ?", (job_id,))
    if submission_ids:
        cur.executemany("DELETE FROM audit_logs WHERE entity_id = ?", [(item,) for item in submission_ids])
    if evaluation_ids:
        cur.executemany("DELETE FROM audit_logs WHERE entity_id = ?", [(item,) for item in evaluation_ids])
    cur.execute("DELETE FROM audit_logs WHERE entity_id = ?", (job_id,))
    cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def load_json(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    delete_job(cur, BROKEN_JOB_ID_TO_DELETE)

    job_row = cur.execute("SELECT parsed_jd FROM jobs WHERE id = ?", (JOB_ID_TO_KEEP,)).fetchone()
    if not job_row:
        raise SystemExit(f"Job not found: {JOB_ID_TO_KEEP}")

    parsed_jd = load_json(job_row[0])
    parsed_jd["title"] = "外贸经理"
    parsed_jd["industry_tags"] = ["印刷", "包装", "造纸", "卡牌"]
    parsed_jd["language_requirements"] = ["英语", "CET4"]
    parsed_jd["summary"] = "广东望京卡牌科技外贸经理岗位，重点评估团队管理、跨部门协同、英语实战、平台运营、交付与回款闭环。"
    cur.execute(
        "UPDATE jobs SET title = ?, parsed_jd = ? WHERE id = ?",
        ("外贸经理", json.dumps(parsed_jd, ensure_ascii=False), JOB_ID_TO_KEEP),
    )

    profile_row = cur.execute(
        "SELECT id, prompt_bundle FROM screening_profile_versions WHERE job_id = ? ORDER BY version DESC LIMIT 1",
        (JOB_ID_TO_KEEP,),
    ).fetchone()
    if profile_row:
        profile_id, prompt_bundle_raw = profile_row
        prompt_bundle = load_json(prompt_bundle_raw)
        prompt_bundle["role"] = "外贸经理 AI 评估中枢"
        prompt_bundle["context"] = "广东望京卡牌科技外贸经理岗位，重点评估团队管理、英语谈判、跨部门推进、交付与回款风控。"
        cur.execute(
            "UPDATE screening_profile_versions SET role_summary = ?, prompt_bundle = ? WHERE id = ?",
            (
                "外贸经理岗位画像已按广东望京卡牌科技的筛选要求冻结，重点关注团队管理、跨部门协同、英语实战、平台体系与危机处理。",
                json.dumps(prompt_bundle, ensure_ascii=False),
                profile_id,
            ),
        )

    cur.execute("UPDATE resume_submissions SET candidate_name = ? WHERE id = ?", ("蓝小姐", BLUE_SUBMISSION_ID))

    candidate_row = cur.execute(
        "SELECT id, summary, extracted_facts FROM candidate_profiles WHERE resume_submission_id = ?",
        (BLUE_SUBMISSION_ID,),
    ).fetchone()
    if candidate_row:
        candidate_id, summary_raw, facts_raw = candidate_row
        summary = load_json(summary_raw)
        summary["candidate_name"] = "蓝小姐"
        facts = load_json(facts_raw)
        facts["candidate_name"] = "蓝小姐"
        cur.execute(
            "UPDATE candidate_profiles SET summary = ?, extracted_facts = ? WHERE id = ?",
            (
                json.dumps(summary, ensure_ascii=False),
                json.dumps(facts, ensure_ascii=False),
                candidate_id,
            ),
        )

    evaluation_row = cur.execute(
        "SELECT id, raw_json, markdown_report FROM evaluation_results WHERE resume_submission_id = ?",
        (BLUE_SUBMISSION_ID,),
    ).fetchone()
    if evaluation_row:
        evaluation_id, raw_json_raw, markdown_report = evaluation_row
        raw_json_data = load_json(raw_json_raw)
        raw_json_data["candidate_name"] = "蓝小姐"
        facts = raw_json_data.get("facts")
        if isinstance(facts, dict):
            facts["candidate_name"] = "蓝小姐"
        updated_markdown = re.sub(r"^- 候选人：.*$", "- 候选人：蓝小姐", markdown_report or "", flags=re.MULTILINE)
        cur.execute(
            "UPDATE evaluation_results SET raw_json = ?, markdown_report = ? WHERE id = ?",
            (
                json.dumps(raw_json_data, ensure_ascii=False),
                updated_markdown,
                evaluation_id,
            ),
        )

    conn.commit()
    conn.close()
    print("restored trade manager display fields fixed")


if __name__ == "__main__":
    main()

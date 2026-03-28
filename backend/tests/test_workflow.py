import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import SessionLocal, init_db
from app.main import app
from app.models import AuditLog, CandidateProfile, EvaluationResult, Job, RecruiterInterviewSession, ResumeSubmission, ReviewDecision, ScreeningProfileVersion


client = TestClient(app)


def import_jd_helper(data=None, files=None):
    """Import JD and handle both sync and async response formats."""
    response = client.post("/jobs/import-jd", data=data, files=files)
    assert response.status_code == 200
    resp_data = response.json()
    if "job_id" in resp_data:
        job_id = resp_data["job_id"]
        for _ in range(60):
            time.sleep(0.2)
            s = client.get(f"/jobs/{job_id}/import-status").json()
            if s.get("status") == "done":
                return client.get(f"/jobs/{job_id}").json()["job"]
        raise TimeoutError("Import JD timed out")
    return resp_data["job"]


def answer_interview_helper(job_id, answers_json):
    """Answer interview and handle both sync and async response formats."""
    resp = client.post(f"/jobs/{job_id}/interview/answer", json=answers_json)
    assert resp.status_code == 200
    data = resp.json()
    if data.get("status") == "compiling":
        for _ in range(60):
            time.sleep(0.2)
            s = client.get(f"/jobs/{job_id}/compile-status").json()
            if s.get("status") == "done":
                return s["draft"]
        raise TimeoutError("Compile profile timed out")
    return data


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


def test_end_to_end_screening_flow(tmp_path: Path) -> None:
    reset_database()
    jd_text = """
    外贸经理
    负责外贸团队管理，英语可作为工作语言，要求本科以上学历，3年以上外贸经验，至少管理过10人团队。
    熟悉阿里巴巴国际站、独立站以及客户谈判。
    """
    job = import_jd_helper(data={"jd_text": jd_text})
    assert job["parsed_jd"]["title"] == "外贸经理"

    answers = {
        "answers": [
            {"question_id": "hard-rules", "answer": "本科及以上，英语能直接谈客户，至少管理过10人团队。"},
            {"question_id": "soft-rules", "answer": "没有卡牌行业也可以，但最好做过制造业或包装。"},
            {"question_id": "top-abilities", "answer": "团队管理、客户谈判、平台打法"},
            {"question_id": "interview-focus", "answer": "货款延期、跨部门协调、客诉危机处理"},
        ]
    }
    draft = answer_interview_helper(job['id'], answers)
    assert draft["hard_constraints"]

    freeze_response = client.post(f"/jobs/{job['id']}/freeze-profile", json={"profile": draft})
    assert freeze_response.status_code == 200
    frozen = freeze_response.json()
    assert frozen["version"] == 1

    resume_text = """
    姓名：蓝小姐
    女 / 33岁
    本科
    8年外贸经验，带领12人团队，负责阿里巴巴国际站、独立站、海外客户谈判与回款。
    曾处理重大客诉、延期交付与供应链协同。
    """
    resume_file = tmp_path / "resume.txt"
    resume_file.write_text(resume_text, encoding="utf-8")
    with resume_file.open("rb") as file_handle:
        upload_response = client.post(
            f"/jobs/{job['id']}/resumes",
            files={"files": ("resume.txt", file_handle, "text/plain")},
        )
    assert upload_response.status_code == 200
    submission_ids = upload_response.json()["submission_ids"]
    assert submission_ids

    dashboard = client.get(f"/jobs/{job['id']}/dashboard")
    assert dashboard.status_code == 200
    evaluations = dashboard.json()["evaluations"]
    assert evaluations
    evaluation_id = next(item["evaluation_id"] for item in evaluations if item["evaluation_id"])
    detail = client.get(f"/evaluations/{evaluation_id}")
    assert detail.status_code == 200
    payload = detail.json()
    assert payload["markdown_report"]
    assert payload["hard_rule_results"]
    assert "met" not in payload["markdown_report"]
    assert "unmet" not in payload["markdown_report"]
    assert "unknown" not in payload["markdown_report"]


def test_manual_decision_is_persisted(tmp_path: Path) -> None:
    reset_database()
    jd_text = "外贸专员，需要英语与2年以上经验。"
    job = import_jd_helper(data={"jd_text": jd_text})
    job_id = job["id"]
    draft = answer_interview_helper(job_id, {"answers": [{"question_id": "hard-rules", "answer": "2年以上经验，英语能沟通"}]})
    client.post(f"/jobs/{job_id}/freeze-profile", json={"profile": draft})

    tmp_file = tmp_path / "candidate.txt"
    tmp_file.write_text("姓名：张三\n3年外贸经验\n英语六级", encoding="utf-8")
    with tmp_file.open("rb") as file_handle:
        upload = client.post(
            f"/jobs/{job_id}/resumes",
            files={"files": ("candidate.txt", file_handle, "text/plain")},
        )
    submission_id = upload.json()["submission_ids"][0]
    dashboard = client.get(f"/jobs/{job_id}/dashboard").json()
    evaluation_id = next(item["evaluation_id"] for item in dashboard["evaluations"] if item["submission_id"] == submission_id)

    decision = client.post(
        f"/evaluations/{evaluation_id}/decision",
        json={"decision": "进入面试", "reviewer_name": "Alice", "comment": "补充沟通后确认推进"},
    )
    assert decision.status_code == 200
    assert decision.json()["manual_decision"] == "进入面试"


def test_candidate_name_falls_back_to_filename_when_resume_text_has_no_name(tmp_path: Path) -> None:
    reset_database()
    job = import_jd_helper(data={"jd_text": "外贸专员，需要英语与2年以上经验。"})
    job_id = job["id"]
    draft = answer_interview_helper(job_id, {"answers": [{"question_id": "hard-rules", "answer": "2年以上经验，英语能沟通"}]})
    client.post(f"/jobs/{job_id}/freeze-profile", json={"profile": draft})

    tmp_file = tmp_path / "蓝小姐.txt"
    tmp_file.write_text("3年外贸经验\n英语六级\n阿里国际站", encoding="utf-8")
    with tmp_file.open("rb") as file_handle:
        upload = client.post(
            f"/jobs/{job_id}/resumes",
            files={"files": ("蓝小姐.txt", file_handle, "text/plain")},
        )

    submission_id = upload.json()["submission_ids"][0]
    dashboard = client.get(f"/jobs/{job_id}/dashboard").json()
    evaluation_id = next(item["evaluation_id"] for item in dashboard["evaluations"] if item["submission_id"] == submission_id)
    detail = client.get(f"/evaluations/{evaluation_id}")

    assert detail.status_code == 200
    assert detail.json()["candidate_name"] == "蓝小姐"

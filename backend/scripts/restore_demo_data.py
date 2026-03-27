from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from sqlalchemy import text


BACKEND_DIR = Path(__file__).resolve().parents[1]
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.db import SessionLocal, init_db  # noqa: E402
from app.models import (  # noqa: E402
    AuditLog,
    CandidateProfile,
    EvaluationResult,
    Job,
    RecruiterInterviewSession,
    ResumeSubmission,
    ScreeningProfileVersion,
)
from app.services.document_parser import normalize_text  # noqa: E402
from app.services.recruiting_engine import RecruitingEngine  # noqa: E402


JD_TEXT = normalize_text(
    """
    外贸经理
    公司：广东莞京卡牌科技
    行业：印刷、包装、造纸、卡牌工艺

    岗位职责：
    1. 负责外贸团队的日常管理，优化团队架构，提升团队业务能力和执行力。
    2. 梳理并优化外贸业务流程，提高团队运营效率，确保订单处理规范高效。
    3. 结合公司发展战略，制定外贸市场拓展计划，提升公司在国际市场的竞争力。
    4. 监控并分析业务数据，优化客户资源配置，提升转化率。
    5. 协调生产、财务等部门，确保订单交付、货款回收等环节顺畅。
    6. 协助团队处理重要客户沟通和谈判，推动长期合作。
    7. 熟悉阿里巴巴国际站、独立站等平台运营，并规划季度、月度策略。
    8. 能处理重大客诉、国际贸易纠纷、物流延期等突发情况。

    任职要求：
    1. 本科及以上学历，英语四级及以上，英语可作为工作语言。
    2. 5年以上外贸行业经验。
    3. 必须具备20人及以上团队管理经历。
    4. 具备跨部门协调交付、回款、风控能力。
    5. 有海外客户商务谈判和客诉处理经验。
    6. 男性年龄38岁以下，女性年龄35岁以下。
    """
)

PARSED_JD = {
    "title": "外贸经理",
    "seniority": "经理",
    "industry_tags": ["印刷", "包装", "造纸", "卡牌工艺", "外贸"],
    "language_requirements": ["英语", "CET4"],
    "experience_years": 5,
    "degree_requirement": "本科",
    "summary": "广东莞京卡牌科技需要一位能管理20人以上团队、统筹平台运营、跨部门推进交付与回款，并具备英语谈判和客诉危机处理能力的外贸经理。",
    "risk_flags": [
        "警惕把销售额包装成团队能力",
        "警惕将带徒弟等同于团队管理",
        "警惕只有英语证书没有真实谈判案例",
    ],
}

CANDIDATES = [
    (
        "蓝小姐.txt",
        """
        姓名：蓝小姐
        女 / 33岁
        本科
        8年外贸经验，带领12人团队，负责阿里巴巴国际站、独立站、海外客户谈判与回款。
        曾处理重大客诉、延期交付与供应链协同。
        """,
    ),
    (
        "张三_强匹配.txt",
        """
        姓名：张三
        外贸经理
        5年外贸经验，英语可作为工作语言。
        曾管理25人团队，负责跨部门协调、交付、回款与重大客诉处理。
        熟悉阿里巴巴国际站、独立站运营。
        有包装制造行业经验。
        """,
    ),
    (
        "张三_基础版.txt",
        """
        姓名：张三
        英语六级
        3年外贸经验
        管理团队5人
        熟悉阿里国际站和客诉处理。
        """,
    ),
]


def build_profile(engine: RecruitingEngine) -> tuple[list[dict], list[dict], list[dict], list[str], list[str], list[str], dict]:
    hard_constraints = [
        engine._rule("age-limit", "年龄红线", "age", "lte", 35, "年龄符合红线（男≤38，女≤35）。"),
        engine._rule("degree-min", "最低学历", "education_level", "gte", "本科", "本科及以上学历。"),
        engine._rule(
            "lang-english",
            "英语沟通",
            "english_level",
            "required",
            ["英语", "CET4"],
            "必须具备英语作为高频工作语言的实战经验。",
            keywords=["英语", "英文", "CET4", "四级", "谈判"],
        ),
        engine._rule("exp-min", "最低工作年限", "experience_years", "gte", 5, "至少5年外贸行业经验。"),
        engine._rule("team-size", "管理跨度", "management_team_size", "gte", 20, "必须明确管理过20人及以上团队。"),
    ]
    soft_constraints = [
        engine._rule(
            "industry-fit",
            "行业贴合度",
            "industry_keywords",
            "contains_any",
            ["印刷", "包装", "造纸", "卡牌工艺"],
            "优先考虑具备印刷、包装、造纸、卡牌工艺相关经验。",
            required=False,
            keywords=["印刷", "包装", "造纸", "卡牌工艺"],
        ),
        engine._rule(
            "platform-fit",
            "平台经验",
            "platform_keywords",
            "contains_any",
            ["阿里巴巴国际站", "独立站"],
            "优先考虑有阿里国际站或独立站运营经验。",
            required=False,
            keywords=["阿里巴巴国际站", "独立站"],
        ),
    ]
    scoring_dimensions = [
        {
            "id": "industry-moat",
            "name": "行业护城河",
            "weight": 30,
            "description": "关注印刷、包装、造纸、卡牌工艺等相关行业经验及迁移能力。",
            "keywords": ["印刷", "包装", "造纸", "卡牌工艺", "制造"],
        },
        {
            "id": "cross-functional",
            "name": "跨部门博弈与交付闭环",
            "weight": 30,
            "description": "关注与生产、财务等部门协调交付、回款和风控的闭环能力。",
            "keywords": ["生产", "财务", "交付", "回款", "风控", "客诉"],
        },
        {
            "id": "platform-system",
            "name": "平台运营与体系搭建",
            "weight": 20,
            "description": "关注阿里国际站、独立站运营与业务流程体系搭建。",
            "keywords": ["阿里巴巴国际站", "独立站", "运营", "流程"],
        },
        {
            "id": "crisis-risk",
            "name": "危机处理与风控",
            "weight": 20,
            "description": "关注重大客诉、贸易纠纷、物流延期等危机场景的处理能力。",
            "keywords": ["客诉", "纠纷", "物流", "延期", "风控"],
        },
    ]
    output_requirements = [
        "生存判定：PASS / KILL（附原因）",
        "硬规则命中/缺失：逐项列出证据或未找到证据",
        "维度评分：每个维度给出 1-5 星和简评",
        "履历伪装预警：指出夸大或逻辑真空地带",
        "信息缺口：缺失的关键信息与复核建议",
        "致命三问：输出 3 个高压面试题",
        "最终建议：建议面试 / 人工复核 / 建议淘汰",
    ]
    interview_focus = [
        "验证英语口语真实谈判能力",
        "验证跨部门撕扯与协同能力",
        "验证团队管理跨度与人员淘汰决策",
    ]
    boundaries = [
        "不能被单纯销售额数字迷惑，必须拆清个人贡献还是团队/流程带来的增长。",
        "所有结论必须绑定证据，找不到证据必须明确写未找到证据。",
        "关键硬规则无法确认时，必须降级到人工复核。",
    ]
    role_summary = "广东莞京卡牌科技正在寻找一位能带领20人以上团队、能用英语与海外客户谈判、能跨部门推进交付回款并具备危机处理能力的外贸经理。"
    prompt_bundle = engine._build_prompt_bundle(
        title="外贸经理",
        parsed_jd=PARSED_JD,
        role_summary=role_summary,
        hard_constraints=hard_constraints,
        scoring_dimensions=scoring_dimensions,
        boundaries=boundaries,
        output_requirements=output_requirements,
    )
    return (
        hard_constraints,
        soft_constraints,
        scoring_dimensions,
        output_requirements,
        interview_focus,
        boundaries,
        {
            "role_summary": role_summary,
            "prompt_bundle": prompt_bundle,
        },
    )


def build_questions(engine: RecruitingEngine) -> tuple[list[dict], list[dict]]:
    questions = engine._heuristic_generate_follow_up_questions(PARSED_JD, JD_TEXT)["questions"]
    answer_map = {
        "hard-rules": "年龄红线：男<=38，女<=35；本科及以上；英语四级及以上且必须能做商务沟通；必须有20人以上团队管理经历；必须有跨部门推进交付、回款或客诉处理经验。",
        "soft-rules": "没有卡牌工艺直接经验可以放宽，但至少要有包装、印刷、造纸、制造型外贸经验。平台不要求全做过，但阿里国际站或独立站至少熟悉其一。",
        "top-abilities": "最看重行业贴合度、跨部门协同与交付闭环、平台运营与体系搭建、危机处理与风控能力。",
        "fake-signals": "警惕只会讲销售额但说不清个人贡献与团队贡献的人；警惕把带徒弟包装成团队管理；警惕只写英语证书但没有真实谈判案例的人。",
        "interview-focus": "重点追问英语口语真实谈判、货款延期和交付危机、跨部门撕扯协调、团队管理跨度和淘汰低绩效成员。",
        "tradeoff": "行业细分可以适度放宽，但英语真实工作能力、团队管理真实性、跨部门交付闭环不能放松。",
        "hire-risk": "不要单干型销冠，不要传声筒型业务员，不要只有平台表层操作却没有体系能力的人。",
    }
    answers = [{"question_id": question["id"], "answer": answer_map.get(question["id"], "")} for question in questions]
    return questions, answers


def reset_database(db) -> None:
    for table in [
        "review_decisions",
        "evaluation_results",
        "candidate_profiles",
        "resume_submissions",
        "screening_profile_versions",
        "recruiter_interview_sessions",
        "jobs",
        "audit_logs",
    ]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def main() -> None:
    init_db()
    engine = RecruitingEngine()
    db = SessionLocal()
    try:
        reset_database(db)

        hard_constraints, soft_constraints, scoring_dimensions, output_requirements, interview_focus, boundaries, bundle = build_profile(engine)
        questions, answers = build_questions(engine)

        profile = {
            "role_summary": bundle["role_summary"],
            "hard_constraints": hard_constraints,
            "soft_constraints": soft_constraints,
            "scoring_dimensions": scoring_dimensions,
            "output_requirements": output_requirements,
            "interview_focus": interview_focus,
            "boundaries": boundaries,
            "prompt_bundle": bundle["prompt_bundle"],
        }

        job = Job(
            title="外贸经理",
            status="screening_in_progress",
            source_type="text",
            jd_text=JD_TEXT,
            parsed_jd=PARSED_JD,
        )
        db.add(job)
        db.flush()

        session = RecruiterInterviewSession(
            job_id=job.id,
            questions=questions,
            answers=answers,
            draft_profile=profile,
        )
        db.add(session)
        db.flush()

        profile_version = ScreeningProfileVersion(
            job_id=job.id,
            version=1,
            status="frozen",
            role_summary=profile["role_summary"],
            hard_constraints=profile["hard_constraints"],
            soft_constraints=profile["soft_constraints"],
            scoring_dimensions=profile["scoring_dimensions"],
            output_requirements=profile["output_requirements"],
            interview_focus=profile["interview_focus"],
            boundaries=profile["boundaries"],
            prompt_bundle=profile["prompt_bundle"],
        )
        db.add(profile_version)
        db.flush()
        job.current_profile_version_id = profile_version.id

        db.add(AuditLog(entity_type="job", entity_id=job.id, action="job_restored", actor="system", payload={"title": job.title}))
        db.add(
            AuditLog(
                entity_type="job",
                entity_id=job.id,
                action="profile_restored",
                actor="system",
                payload={"version": 1},
            )
        )

        storage_dir = BACKEND_DIR / "storage" / "resumes"
        storage_dir.mkdir(parents=True, exist_ok=True)

        for filename, raw_text in CANDIDATES:
            normalized_resume = normalize_text(raw_text)
            storage_name = f"restored-{uuid.uuid4()}.txt"
            file_path = storage_dir / storage_name
            file_path.write_text(raw_text.strip() + "\n", encoding="utf-8")

            result = engine.evaluate_resume(profile, normalized_resume, Path(filename).stem)
            candidate_name = result.data.get("candidate_name") or Path(filename).stem

            submission = ResumeSubmission(
                job_id=job.id,
                filename=filename,
                content_type="text/plain",
                storage_path=f"resumes/{storage_name}",
                extracted_text=normalized_resume,
                status="completed",
                candidate_name=candidate_name,
                parse_meta={
                    "suffix": ".txt",
                    "length": len(normalized_resume),
                    "storage": {
                        "backend": "local",
                        "key": f"resumes/{storage_name}",
                        "filename": filename,
                        "content_type": "text/plain",
                        "path": str(file_path),
                    },
                },
            )
            db.add(submission)
            db.flush()

            db.add(
                CandidateProfile(
                    job_id=job.id,
                    resume_submission_id=submission.id,
                    extracted_facts=result.data["facts"],
                    summary={
                        "candidate_name": candidate_name,
                        "headline_metrics": result.data["facts"].get("headline_metrics", []),
                    },
                )
            )

            db.add(
                EvaluationResult(
                    job_id=job.id,
                    resume_submission_id=submission.id,
                    profile_version_id=profile_version.id,
                    status=result.data["status"],
                    overall_score=result.data["overall_score"],
                    hard_rule_results=result.data["hard_rule_results"],
                    dimension_scores=result.data["dimension_scores"],
                    evidence=result.data["evidence"],
                    warnings=result.data["warnings"],
                    info_gaps=result.data["info_gaps"],
                    interview_questions=result.data["interview_questions"],
                    final_recommendation=result.data["final_recommendation"],
                    markdown_report=result.data["markdown_report"],
                    raw_json=result.data,
                    model_version=result.model_version,
                    prompt_bundle_version=1,
                    execution_state="completed",
                )
            )
            db.add(
                AuditLog(
                    entity_type="resume_submission",
                    entity_id=submission.id,
                    action="resume_restored",
                    actor="system",
                    payload={"filename": filename, "status": result.data["status"]},
                )
            )

        db.commit()
        print(job.id)
    finally:
        db.close()


if __name__ == "__main__":
    main()

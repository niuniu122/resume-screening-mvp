from app.services.recruiting_engine import RecruitingEngine


def test_profile_compilation_keeps_failure_profile_and_platform_requirements() -> None:
    engine = RecruitingEngine()
    parsed_jd = {
        "title": "外贸经理",
        "seniority": "经理",
        "industry_tags": ["包装", "印刷"],
        "language_requirements": ["英语"],
        "experience_years": 5,
        "degree_requirement": "本科",
        "summary": "需要英语、团队管理、平台运营与跨部门协同能力。",
        "risk_flags": [],
    }
    answers = [
        {"question_id": "hard-rules", "answer": "本科以上，至少20人团队管理经历，英语可以谈客户。"},
        {"question_id": "soft-rules", "answer": "没有卡牌经验但有包装印刷经验可以放宽。"},
        {"question_id": "top-abilities", "answer": "团队管理、平台运营、客户谈判。"},
        {"question_id": "interview-focus", "answer": "重点追问英语谈判和跨部门交付。"},
        {"question_id": "fake-signals", "answer": "警惕只讲销售额不讲团队贡献的人。"},
        {"question_id": "tradeoff", "answer": "行业细分可放宽，但英语和管理不能放。"},
        {"question_id": "hire-risk", "answer": "不要单干型销冠，不要传声筒型业务员。"},
        {"question_id": "platform-proof", "answer": "必须说清楚做过哪些平台动作、规则策略和流程优化成果。"},
    ]

    result = engine.compile_profile(parsed_jd, "外贸经理，需要平台运营和体系搭建能力。", answers)
    draft = result.data

    assert any(rule["label"] == "平台与体系要求" for rule in draft["soft_constraints"])
    assert any("平台与体系要求" in item for item in draft["output_requirements"])
    assert any("平台与体系要求" in item for item in draft["interview_focus"])
    assert any("失败画像" in item for item in draft["boundaries"])

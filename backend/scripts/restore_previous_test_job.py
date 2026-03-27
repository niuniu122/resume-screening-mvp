from __future__ import annotations

import json
import time
from pathlib import Path

import requests


BASE_URL = "http://127.0.0.1:8010"
ROOT = Path(__file__).resolve().parents[2]

JD_TEXT = """
外贸经理
公司：广东望京卡牌科技（100-499人，印刷 / 包装 / 造纸）

岗位职责：
1. 负责外贸团队的日常管理，优化团队架构，提升整体业务能力和执行力，激励团队成员达成目标；
2. 梳理并优化外贸业务流程，提升团队运营效率，确保订单处理规范且高效；
3. 结合公司发展战略，制定外贸市场拓展计划，提升公司在国际市场的竞争力；
4. 为团队成员提供业务指导和专业培训，帮助其提升国际贸易知识、谈判技巧及客户开发能力；
5. 监控分析外贸业务数据，及时调整销售策略，优化客户资源配置，提升转化率；
6. 协调公司内部生产、财务等部门，确保订单交付、货款回收等环节顺畅；
7. 协助团队处理重要客户的沟通和谈判，提升客户满意度，推动长期合作；
8. 熟悉阿里巴巴国际站、独立站等平台运营，了解平台规则与趋势。

任职要求：
1. 本科及以上学历，外语四级以上，英语可用于工作；
2. 3年以上外贸行业经验，至少1年以上团队管理经验；
3. 熟悉外贸业务流程，了解国际贸易规则，具备较强市场分析能力；
4. 具备良好的沟通协调能力，能激励团队；
5. 具有较好的英语沟通能力，能与国外客户顺畅交流；
6. 责任心强，抗压能力强，具备良好的团队合作精神；
7. 最好了解卡牌行业工艺，能快速上手；
8. 年龄要求：男性38岁以下，女性35岁以下。
""".strip()


def answer_for(question: dict[str, str]) -> str:
    text = " ".join(
        [
            question.get("id", ""),
            question.get("title", ""),
            question.get("category", ""),
            question.get("prompt", ""),
        ]
    )
    if "硬" in text or "红线" in text or "hard" in text:
        return (
            "硬性门槛：女性35岁以下、男性38岁以下；本科优先，最低大专；英语四级以上且必须有商务谈判、"
            "客诉处理等工作英语实战；必须明确带过20人及以上团队；必须有外贸流程、交付协调、回款闭环经验。"
        )
    if "放宽" in text or "soft" in text or "取舍" in text:
        return (
            "可放宽项：不一定非卡牌行业，但最好来自印刷、包装、造纸、文创、复杂制造业；"
            "如果没有卡牌经验，必须证明复杂工艺学习速度快、能快速理解生产与交付链路。"
        )
    if "能力" in text or "评分" in text or "top" in text:
        return (
            "最关键能力：1）行业护城河与复杂工艺理解；2）跨部门博弈与订单交付、回款风控；"
            "3）平台管理与业务体系搭建；4）危机处理与重大客诉、延期、物流异常处置。"
        )
    if "伪装" in text or "风险" in text or "fake" in text:
        return (
            "最容易包装的点：把个人销售额包装成团队管理成果；把带徒弟说成带团队；"
            "把英语证书包装成真实商务谈判能力；把平台获客包装成平台体系建设。"
        )
    if "面试" in text or "focus" in text:
        return (
            "面试必须深挖：英语真实口语谈判能力；卡牌印刷工艺理解；货款延期和交付异常场景下的跨部门推进；"
            "管理20人以上团队时的分工、考核和淘汰机制。"
        )
    if "平台" in text:
        return "平台方面重点看是否真正做过阿里国际站和独立站的规则研究、策略制定、月度季度运营计划，而不只是会发品和接询盘。"
    return "重点是制造型外贸经理，不只看拿单，还要看团队管理、跨部门协同、交付与回款风控。"


def main() -> None:
    response = requests.post(f"{BASE_URL}/jobs/import-jd", data={"jd_text": JD_TEXT}, timeout=180)
    response.raise_for_status()
    job = response.json()["job"]
    job_id = job["id"]

    answers = [{"question_id": question["id"], "answer": answer_for(question)} for question in job["interview_session"]["questions"]]
    draft = requests.post(
        f"{BASE_URL}/jobs/{job_id}/interview/answer",
        json={"answers": answers},
        timeout=300,
    )
    draft.raise_for_status()

    frozen = requests.post(
        f"{BASE_URL}/jobs/{job_id}/freeze-profile",
        json={"profile": draft.json()},
        timeout=300,
    )
    frozen.raise_for_status()

    blue_resume = ROOT / "backend" / "storage" / "resumes" / "8c97de02-41a4-4ad0-a638-8c62dbdf594f.pdf"
    compare_resume = ROOT / "backend" / "storage" / "resumes" / "e3cfb523-70fc-4171-985c-e4190d04cee2.txt"

    files = [
        ("files", ("蓝小姐_外贸经理.pdf", blue_resume.open("rb"), "application/pdf")),
        ("files", ("张三_对照样本.txt", compare_resume.open("rb"), "text/plain")),
    ]
    try:
        upload = requests.post(f"{BASE_URL}/jobs/{job_id}/resumes", files=files, timeout=300)
        upload.raise_for_status()
    finally:
        for _, file_tuple in files:
            file_tuple[1].close()

    dashboard_payload = None
    for _ in range(50):
        dashboard = requests.get(f"{BASE_URL}/jobs/{job_id}/dashboard", timeout=180)
        dashboard.raise_for_status()
        dashboard_payload = dashboard.json()
        if (
            dashboard_payload["stats"]["total"] >= 2
            and all(item.get("submission_status") in {"completed", "failed"} for item in dashboard_payload["evaluations"])
        ):
            break
        time.sleep(2)

    print(
        json.dumps(
            {
                "job_id": job_id,
                "job_title": dashboard_payload["job"]["title"],
                "stats": dashboard_payload["stats"],
                "evaluations": [
                    {
                        "candidate_name": item.get("candidate_name"),
                        "filename": item.get("filename"),
                        "submission_status": item.get("submission_status"),
                        "evaluation_status": item.get("evaluation_status"),
                        "overall_score": item.get("overall_score"),
                    }
                    for item in dashboard_payload["evaluations"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

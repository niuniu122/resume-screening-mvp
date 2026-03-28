from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from ..config import get_settings


INDUSTRY_KEYWORDS = [
    "印刷",
    "包装",
    "造纸",
    "卡牌",
    "玩具",
    "制造",
    "跨境电商",
    "消费品",
    "外贸",
]
PLATFORM_KEYWORDS = ["阿里巴巴国际站", "独立站", "亚马逊", "Shopify", "1688", "中国制造网"]
LANGUAGE_KEYWORDS = ["英语", "英文", "CET4", "CET6", "六级", "四级", "雅思", "BEC"]
DEGREE_ORDER = {
    "高中": 1,
    "中专": 1,
    "大专": 2,
    "本科": 3,
    "硕士": 4,
    "MBA": 4,
    "博士": 5,
}


@dataclass
class EngineResult:
    data: dict[str, Any]
    model_version: str


class RecruitingEngine:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = None
        if self.settings.openai_api_key:
            client_kwargs: dict[str, Any] = {
                "api_key": self.settings.openai_api_key,
                "timeout": self.settings.openai_timeout_seconds,
            }
            if self.settings.openai_base_url:
                client_kwargs["base_url"] = self.settings.openai_base_url
            self.client = OpenAI(**client_kwargs)

    @property
    def llm_enabled(self) -> bool:
        return self.client is not None

    @property
    def model_version(self) -> str:
        return self.settings.openai_model if self.client else "heuristic-v1"

    def parse_jd(self, jd_text: str) -> EngineResult:
        fallback = self._heuristic_parse_jd(jd_text)
        if not self.llm_enabled:
            return EngineResult(fallback, "heuristic-v1")
        try:
            payload = self._llm_parse_jd(jd_text)
            return EngineResult(self._merge_parsed_jd(payload, fallback), self.model_version)
        except Exception:
            return EngineResult(fallback, "heuristic-v1")

    def generate_follow_up_questions(self, parsed_jd: dict[str, Any], jd_text: str) -> EngineResult:
        fallback = self._heuristic_generate_follow_up_questions(parsed_jd, jd_text)
        if not self.llm_enabled:
            return EngineResult(fallback, "heuristic-v1")
        try:
            payload = self._llm_generate_follow_up_questions(parsed_jd, jd_text)
            return EngineResult(self._sanitize_questions(payload, fallback), self.model_version)
        except Exception:
            return EngineResult(fallback, "heuristic-v1")

    def compile_profile(
        self,
        parsed_jd: dict[str, Any],
        jd_text: str,
        answers: list[dict[str, Any]],
    ) -> EngineResult:
        fallback = self._heuristic_compile_profile(parsed_jd, jd_text, answers)
        if not self.llm_enabled:
            return EngineResult(fallback, "heuristic-v1")
        try:
            payload = self._llm_compile_profile(parsed_jd, jd_text, answers, fallback)
            return EngineResult(self._normalize_profile(payload, parsed_jd, answers, fallback), self.model_version)
        except Exception:
            return EngineResult(fallback, "heuristic-v1")

    def evaluate_resume(self, profile: dict[str, Any], resume_text: str, candidate_name_hint: str | None = None) -> EngineResult:
        fallback = self._heuristic_evaluate_resume(profile, resume_text, candidate_name_hint)
        if not self.llm_enabled:
            return EngineResult(fallback, "heuristic-v1")
        try:
            payload = self._llm_evaluate_resume(profile, resume_text, fallback)
            return EngineResult(
                self._normalize_evaluation(payload, profile, resume_text, fallback, candidate_name_hint),
                self.model_version,
            )
        except Exception:
            return EngineResult(fallback, "heuristic-v1")

    def _request_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        if not self.client:
            raise RuntimeError("Model client is not configured.")
        completion = self.client.chat.completions.create(
            model=self.settings.openai_model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = completion.choices[0].message.content or "{}"
        data = json.loads(content)
        if not isinstance(data, dict):
            raise ValueError("Model output must be a JSON object.")
        return data

    def _llm_parse_jd(self, jd_text: str) -> dict[str, Any]:
        return self._request_json(
            system_prompt="你是招聘分析师。请把岗位 JD 解析成结构化 JSON，只能依据输入内容，禁止脑补。",
            user_prompt=(
                "请输出一个 JSON 对象，包含这些字段："
                " title, seniority, industry_tags, language_requirements, experience_years, "
                "degree_requirement, summary, risk_flags。\n\n"
                f"JD:\n{jd_text}"
            ),
        )

    def _llm_generate_follow_up_questions(self, parsed_jd: dict[str, Any], jd_text: str) -> dict[str, Any]:
        return self._request_json(
            system_prompt="你是招聘顾问。请生成 6 到 8 个有杀伤力的招聘追问，帮助冻结岗位筛选标准。",
            user_prompt=(
                "请输出 JSON：{ \"questions\": [{\"id\":...,\"title\":...,\"prompt\":...,\"category\":...}] }。"
                " 问题要覆盖硬要求、可放宽项、风险点、面试追问和取舍边界。\n\n"
                f"parsed_jd={json.dumps(parsed_jd, ensure_ascii=False)}\n\n"
                f"jd_text={jd_text}"
            ),
        )

    def _llm_compile_profile(
        self,
        parsed_jd: dict[str, Any],
        jd_text: str,
        answers: list[dict[str, Any]],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request_json(
            system_prompt="你是岗位画像编译器。请将 JD 和招聘方回答整合成可冻结的筛选画像，输出必须是 JSON。",
            user_prompt=(
                "请输出 JSON，包含字段：role_summary, hard_constraints, soft_constraints, "
                "scoring_dimensions, output_requirements, interview_focus, boundaries。"
                " hard_constraints 和 soft_constraints 中的每一项都包含 id, label, description, field, operator, value, required, source, keywords。"
                " scoring_dimensions 中的每一项都包含 id, name, weight, description, keywords。\n\n"
                f"parsed_jd={json.dumps(parsed_jd, ensure_ascii=False)}\n\n"
                f"jd_text={jd_text}\n\n"
                f"answers={json.dumps(answers, ensure_ascii=False)}\n\n"
                f"heuristic_draft={json.dumps(fallback, ensure_ascii=False)}"
            ),
        )

    def _llm_evaluate_resume(self, profile: dict[str, Any], resume_text: str, fallback: dict[str, Any]) -> dict[str, Any]:
        return self._request_json(
            system_prompt=(
                "你是高压招聘筛选官。你必须根据岗位画像和候选人简历输出结构化评估。"
                " 所有结论要绑定证据，找不到证据就明确写未找到证据。"
            ),
            user_prompt=(
                "请输出 JSON，包含字段：candidate_name, facts, hard_rule_results, dimension_scores, warnings, "
                "info_gaps, interview_questions, final_recommendation。"
                " facts 至少包含 candidate_name, gender, age, experience_years, management_team_size, education_level, "
                "english_hits, industry_hits, platform_hits, risk_hits, headline_metrics。"
                " hard_rule_results 中每项包含 rule_id, label, required, status, expected, actual, evidence, description。"
                " dimension_scores 中每项包含 id, name, weight, normalized_score, stars, summary, evidence。\n\n"
                f"profile={json.dumps(profile, ensure_ascii=False)}\n\n"
                f"resume={resume_text}\n\n"
                f"heuristic_baseline={json.dumps(fallback, ensure_ascii=False)}"
            ),
        )

    def _merge_parsed_jd(self, payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": self._clean_text(payload.get("title")) or fallback["title"],
            "seniority": self._clean_text(payload.get("seniority")) or fallback.get("seniority"),
            "industry_tags": self._string_list(payload.get("industry_tags")) or fallback.get("industry_tags", []),
            "language_requirements": self._string_list(payload.get("language_requirements")) or fallback.get("language_requirements", []),
            "experience_years": self._to_int(payload.get("experience_years"), fallback.get("experience_years")),
            "degree_requirement": self._clean_text(payload.get("degree_requirement")) or fallback.get("degree_requirement"),
            "summary": self._clean_text(payload.get("summary")) or fallback["summary"],
            "risk_flags": self._string_list(payload.get("risk_flags")) or fallback.get("risk_flags", []),
        }

    def _sanitize_questions(self, payload: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
        questions = []
        for index, item in enumerate(payload.get("questions", []), start=1):
            if not isinstance(item, dict):
                continue
            title = self._clean_text(item.get("title"))
            prompt = self._clean_text(item.get("prompt"))
            category = self._clean_text(item.get("category")) or "补充判断"
            if not title or not prompt:
                continue
            questions.append(
                {
                    "id": self._identifier(item.get("id")) or f"question-{index}",
                    "title": title,
                    "prompt": prompt,
                    "category": category,
                }
            )
        return {"questions": questions[:8]} if len(questions) >= 6 else fallback

    def _normalize_profile(
        self,
        payload: dict[str, Any],
        parsed_jd: dict[str, Any],
        answers: list[dict[str, Any]],
        fallback: dict[str, Any],
    ) -> dict[str, Any]:
        role_summary = self._clean_text(payload.get("role_summary")) or fallback["role_summary"]
        hard_constraints = self._normalize_rules(payload.get("hard_constraints"), fallback["hard_constraints"], True)
        soft_constraints = self._normalize_rules(payload.get("soft_constraints"), fallback["soft_constraints"], False)
        scoring_dimensions = self._normalize_dimensions(payload.get("scoring_dimensions"), fallback["scoring_dimensions"])
        output_requirements = self._dedupe(self._string_list(payload.get("output_requirements")) + fallback["output_requirements"])
        interview_focus = self._dedupe(self._string_list(payload.get("interview_focus")) + fallback["interview_focus"])
        boundaries = self._dedupe(self._string_list(payload.get("boundaries")) + fallback["boundaries"])
        return {
            "role_summary": role_summary,
            "hard_constraints": hard_constraints,
            "soft_constraints": soft_constraints,
            "scoring_dimensions": scoring_dimensions,
            "output_requirements": output_requirements,
            "interview_focus": interview_focus,
            "boundaries": boundaries,
            "prompt_bundle": self._build_prompt_bundle(
                title=parsed_jd.get("title", "目标岗位"),
                parsed_jd=parsed_jd,
                role_summary=role_summary,
                hard_constraints=hard_constraints,
                scoring_dimensions=scoring_dimensions,
                boundaries=boundaries,
                output_requirements=output_requirements,
            ),
        }

    def _normalize_evaluation(
        self,
        payload: dict[str, Any],
        profile: dict[str, Any],
        resume_text: str,
        fallback: dict[str, Any],
        candidate_name_hint: str | None,
    ) -> dict[str, Any]:
        facts = self._normalize_facts(payload.get("facts"), fallback["facts"])
        candidate_name = self._clean_text(payload.get("candidate_name")) or facts.get("candidate_name") or candidate_name_hint
        facts["candidate_name"] = candidate_name
        hard_results = self._normalize_hard_results(payload.get("hard_rule_results"), profile.get("hard_constraints", []), fallback["hard_rule_results"])
        soft_results = [self._evaluate_rule(rule, facts, resume_text) for rule in profile.get("soft_constraints", [])]
        dimension_scores = self._normalize_dimension_scores(
            payload.get("dimension_scores"),
            profile.get("scoring_dimensions", []),
            fallback["dimension_scores"],
        )
        unknown_hard, unmet_hard, overall_score, status, survival = self._derive_screening_status(hard_results, dimension_scores)
        warnings = self._string_list(payload.get("warnings")) or fallback["warnings"]
        warnings = self._dedupe(warnings + self._build_warnings(facts, profile))
        info_gaps = self._string_list(payload.get("info_gaps")) or [f"{item['label']} 未找到充分证据" for item in unknown_hard]
        interview_questions = self._string_list(payload.get("interview_questions")) or fallback["interview_questions"]
        while len(interview_questions) < 3:
            interview_questions.append("请描述一次你在客户、内部团队和交付压力同时失控时的处理过程，要求讲清动作、取舍和结果。")
        interview_questions = interview_questions[:3]
        recommendation_text = self._recommendation_from_payload(payload.get("final_recommendation")) or self._recommendation_text(status, unmet_hard, unknown_hard, warnings)
        return {
            "candidate_name": candidate_name,
            "facts": facts,
            "status": status,
            "overall_score": overall_score,
            "hard_rule_results": hard_results,
            "dimension_scores": dimension_scores,
            "evidence": self._build_evidence_bundle(hard_results, soft_results, dimension_scores),
            "warnings": warnings,
            "info_gaps": info_gaps,
            "interview_questions": interview_questions,
            "final_recommendation": recommendation_text,
            "markdown_report": self._build_markdown_report(
                facts=facts,
                survival=survival,
                status=status,
                hard_results=hard_results,
                dimension_scores=dimension_scores,
                warnings=warnings,
                info_gaps=info_gaps,
                interview_questions=interview_questions,
                recommendation_text=recommendation_text,
            ),
        }

    def _heuristic_generate_follow_up_questions(self, parsed_jd: dict[str, Any], jd_text: str) -> dict[str, Any]:
        title = parsed_jd.get("title", "目标岗位")
        questions = [
            {
                "id": "hard-rules",
                "title": "必须满足的红线",
                "prompt": f"{title} 这次筛选里，哪些条件一旦不满足就可以直接淘汰？请明确写出年龄、学历、语言、管理跨度、行业经验等硬规则。",
                "category": "硬性门槛",
            },
            {
                "id": "soft-rules",
                "title": "可放宽条件",
                "prompt": "哪些条件是优先但不是硬性必须？请说明在什么情况下可以放宽，以及你愿意接受的替代经验。",
                "category": "放宽条件",
            },
            {
                "id": "top-abilities",
                "title": "最关键的三项能力",
                "prompt": "如果只能保留三个最重要的判断维度，你最看重什么？请写出能力项和你想看到的证据。",
                "category": "评分维度",
            },
            {
                "id": "fake-signals",
                "title": "最容易被伪装的亮点",
                "prompt": "这个岗位里，哪些经历很容易被候选人夸大？例如管理团队、平台运营、客户谈判、供应链协调等，请说明你想如何拆穿。",
                "category": "风险点",
            },
            {
                "id": "interview-focus",
                "title": "面试必须深挖的内容",
                "prompt": "如果系统要自动给出高压面试题，你最希望追问哪些真实能力或薄弱点？",
                "category": "面试追问",
            },
            {
                "id": "tradeoff",
                "title": "你最愿意放松什么",
                "prompt": "在行业经验、团队规模、语言能力、平台经验、薪资匹配之间，你最愿意放松哪一项？边界是什么？",
                "category": "取舍偏好",
            },
            {
                "id": "hire-risk",
                "title": "你最怕招错哪种人",
                "prompt": "请描述你最想规避的候选人类型，例如单兵销冠、流程传声筒、只会讲故事但没有结果闭环的人。",
                "category": "失败画像",
            },
        ]
        if "平台" in jd_text or any(keyword in jd_text for keyword in PLATFORM_KEYWORDS):
            questions.append(
                {
                    "id": "platform-proof",
                    "title": "平台与体系要求",
                    "prompt": "如果候选人自称懂平台运营或体系搭建，你希望看到哪些可验证的成果或动作，才算真正匹配？",
                    "category": "专项能力",
                }
            )
        return {"questions": questions[:8]}

    def _heuristic_compile_profile(
        self,
        parsed_jd: dict[str, Any],
        jd_text: str,
        answers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        answer_map = {item["question_id"]: item["answer"] for item in answers}
        title = parsed_jd.get("title", "目标岗位")
        hard_constraints: list[dict[str, Any]] = []
        soft_constraints: list[dict[str, Any]] = []

        if parsed_jd.get("experience_years"):
            hard_constraints.append(
                self._rule(
                    "exp-min",
                    "最低工作年限",
                    "experience_years",
                    "gte",
                    parsed_jd["experience_years"],
                    f"候选人需要至少 {parsed_jd['experience_years']} 年相关经验。",
                )
            )
        if parsed_jd.get("degree_requirement"):
            hard_constraints.append(
                self._rule(
                    "degree-min",
                    "最低学历",
                    "education_level",
                    "gte",
                    parsed_jd["degree_requirement"],
                    f"学历至少达到 {parsed_jd['degree_requirement']}。",
                )
            )
        if parsed_jd.get("language_requirements"):
            hard_constraints.append(
                self._rule(
                    "lang-english",
                    "英语沟通",
                    "english_level",
                    "required",
                    parsed_jd["language_requirements"],
                    "需要能在工作中使用英语沟通或谈判。",
                    keywords=parsed_jd["language_requirements"],
                )
            )

        parsed_team_size = self._extract_team_size(answer_map.get("hard-rules", "") + " " + jd_text)
        if parsed_team_size:
            hard_constraints.append(
                self._rule(
                    "team-size",
                    "管理跨度",
                    "management_team_size",
                    "gte",
                    parsed_team_size,
                    f"必须明确有管理 {parsed_team_size} 人及以上团队的经历。",
                )
            )

        industries = parsed_jd.get("industry_tags", [])
        if industries:
            soft_constraints.append(
                self._rule(
                    "industry-fit",
                    "行业贴合度",
                    "industry_keywords",
                    "contains_any",
                    industries,
                    "优先考虑具备相近行业或产品经验的候选人。",
                    required=False,
                    keywords=industries,
                )
            )

        platform_hits = [kw for kw in PLATFORM_KEYWORDS if kw in jd_text or kw in answer_map.get("top-abilities", "")]
        if platform_hits:
            soft_constraints.append(
                self._rule(
                    "platform-fit",
                    "平台经验",
                    "platform_keywords",
                    "contains_any",
                    platform_hits,
                    "优先考虑有平台运营、渠道搭建或独立站经验的候选人。",
                    required=False,
                    keywords=platform_hits,
                )
            )

        for index, text in enumerate(self._split_preferences(answer_map.get("soft-rules", "")), start=1):
            soft_constraints.append(
                self._rule(
                    f"soft-{index}",
                    f"可放宽条件 {index}",
                    "custom",
                    "text",
                    text,
                    text,
                    required=False,
                )
            )

        platform_proof = self._clean_text(answer_map.get("platform-proof"))
        if platform_proof:
            soft_constraints.append(
                self._rule(
                    "platform-proof",
                    "平台与体系要求",
                    "platform_proof",
                    "text",
                    platform_proof,
                    f"如果候选人强调平台运营或体系搭建，至少应提供这些可验证成果或动作：{platform_proof}",
                    required=False,
                    keywords=self._pick_keywords(platform_proof, PLATFORM_KEYWORDS),
                )
            )

        scoring_dimensions = self._build_scoring_dimensions(parsed_jd, jd_text, answer_map)
        output_requirements = [
            "生存判定：PASS / KILL（附原因）",
            "硬规则命中/缺失：逐项列出证据或未找到证据",
            "维度评分：每个维度给出 1-5 星和简评",
            "履历伪装预警：指出夸大或逻辑真空地带",
            "信息缺口：缺失的关键信息与复核建议",
            "致命三问：输出 3 个高压面试题",
            "最终建议：建议面试 / 人工复核 / 建议淘汰",
        ]
        if platform_proof:
            output_requirements.append(f"平台与体系要求：{platform_proof}")

        interview_focus = [
            "验证英语口语、客户谈判或跨部门协同的真实案例",
            "拆解团队管理跨度、职责归因和实际闭环结果",
            "要求候选人在极限场景下给出具体动作和取舍",
        ]
        if answer_map.get("interview-focus"):
            interview_focus.extend(self._split_preferences(answer_map["interview-focus"]))
        if platform_proof:
            interview_focus.append(f"平台与体系要求：{platform_proof}")

        boundaries = [
            "所有结论必须绑定简历中的证据片段或明确标记未找到证据。",
            "禁止把销售额、头衔、泛化职责直接等价为实际管理能力。",
            "关键硬规则无法确认时，必须降级到人工复核。",
        ]
        fake_signals = self._clean_text(answer_map.get("fake-signals"))
        tradeoff = self._clean_text(answer_map.get("tradeoff"))
        hire_risk = self._clean_text(answer_map.get("hire-risk"))
        if fake_signals:
            boundaries.append(f"重点拆穿的履历伪装信号：{fake_signals}")
        if tradeoff:
            boundaries.append(f"可放宽边界：{tradeoff}")
        if hire_risk:
            boundaries.append(f"重点规避的失败画像：{hire_risk}")

        role_summary = f"{title} 的岗位画像已经根据 JD 与招聘方回答整理为可冻结的筛选规则，重点关注 {', '.join([dim['name'] for dim in scoring_dimensions[:3]])}。"
        return {
            "role_summary": role_summary,
            "hard_constraints": hard_constraints,
            "soft_constraints": soft_constraints,
            "scoring_dimensions": scoring_dimensions,
            "output_requirements": output_requirements,
            "interview_focus": list(dict.fromkeys(interview_focus)),
            "boundaries": boundaries,
            "prompt_bundle": self._build_prompt_bundle(
                title=title,
                parsed_jd=parsed_jd,
                role_summary=role_summary,
                hard_constraints=hard_constraints,
                scoring_dimensions=scoring_dimensions,
                boundaries=boundaries,
                output_requirements=output_requirements,
            ),
        }

    def _heuristic_evaluate_resume(self, profile: dict[str, Any], resume_text: str, candidate_name_hint: str | None = None) -> dict[str, Any]:
        facts = self._extract_candidate_facts(resume_text, candidate_name_hint)
        hard_results = [self._evaluate_rule(rule, facts, resume_text) for rule in profile.get("hard_constraints", [])]
        soft_results = [self._evaluate_rule(rule, facts, resume_text) for rule in profile.get("soft_constraints", [])]
        dimension_scores = self._score_dimensions(profile.get("scoring_dimensions", []), facts, resume_text)
        unknown_hard, unmet_hard, overall_score, status, survival = self._derive_screening_status(hard_results, dimension_scores)
        warnings = self._build_warnings(facts, profile)
        info_gaps = [f"{item['label']} 未找到充分证据" for item in unknown_hard]
        interview_questions = self._build_interview_questions(profile, unmet_hard, unknown_hard, warnings)
        recommendation_text = self._recommendation_text(status, unmet_hard, unknown_hard, warnings)
        return {
            "candidate_name": facts.get("candidate_name"),
            "facts": facts,
            "status": status,
            "overall_score": overall_score,
            "hard_rule_results": hard_results,
            "dimension_scores": dimension_scores,
            "evidence": self._build_evidence_bundle(hard_results, soft_results, dimension_scores),
            "warnings": warnings,
            "info_gaps": info_gaps,
            "interview_questions": interview_questions,
            "final_recommendation": recommendation_text,
            "markdown_report": self._build_markdown_report(
                facts=facts,
                survival=survival,
                status=status,
                hard_results=hard_results,
                dimension_scores=dimension_scores,
                warnings=warnings,
                info_gaps=info_gaps,
                interview_questions=interview_questions,
                recommendation_text=recommendation_text,
            ),
        }

    def _heuristic_parse_jd(self, jd_text: str) -> dict[str, Any]:
        lines = [line.strip() for line in re.split(r"[\n\r]+", jd_text) if line.strip()]
        title = self._match_first(jd_text, [r"职位名称[:：]?\s*([^\n，。,；;]{2,20})", r"岗位[:：]?\s*([^\n，。,；;]{2,20})"])
        if not title and lines:
            title = next((line for line in lines if 1 < len(line) <= 18), lines[0])
        if title and len(title) > 18 and title.split():
            first_token = title.split()[0].strip()
            if 1 < len(first_token) <= 18:
                title = first_token
        if not title:
            sentence = re.split(r"[。；;!！?？]", jd_text)[0].strip()
            if sentence.split():
                first_token = sentence.split()[0].strip()
                if 1 < len(first_token) <= 18:
                    title = first_token
        seniority = self._pick_keywords(jd_text, ["经理", "总监", "主管", "专员", "负责人"])
        experience_years = self._extract_years_requirement(jd_text)
        degree_requirement = self._extract_degree_requirement(jd_text)
        language_requirements = [word for word in LANGUAGE_KEYWORDS if word in jd_text]
        industry_tags = [word for word in INDUSTRY_KEYWORDS if word in jd_text]
        summary = re.sub(r"\s+", " ", jd_text)[:220]
        risk_flags = []
        if "管理" in jd_text and not self._extract_team_size(jd_text):
            risk_flags.append("JD 提到了管理职责，但未明确团队规模。")
        if "英语" in jd_text and not any(word in jd_text for word in ["口语", "谈判", "沟通", "邮件"]):
            risk_flags.append("JD 需要英语，但未明确是证书要求还是实战要求。")
        return {
            "title": title or "目标岗位",
            "seniority": seniority[0] if seniority else None,
            "industry_tags": industry_tags,
            "language_requirements": language_requirements,
            "experience_years": experience_years,
            "degree_requirement": degree_requirement,
            "summary": summary,
            "risk_flags": risk_flags,
        }

    def _build_scoring_dimensions(
        self,
        parsed_jd: dict[str, Any],
        jd_text: str,
        answer_map: dict[str, str],
    ) -> list[dict[str, Any]]:
        dimensions = [
            {
                "id": "core-fit",
                "name": "核心经历贴合度",
                "weight": 30,
                "description": "判断候选人的主要工作经历与目标岗位场景是否匹配。",
                "keywords": parsed_jd.get("industry_tags", [])[:4],
            },
            {
                "id": "execution",
                "name": "业务闭环与结果质量",
                "weight": 25,
                "description": "关注是否具备可验证的结果、闭环动作和复杂问题处理能力。",
                "keywords": ["结果", "提升", "增长", "交付", "回款", "风险"],
            },
            {
                "id": "leadership",
                "name": "管理与跨部门协同",
                "weight": 25,
                "description": "关注团队管理跨度、跨部门推进、冲突处理与协调能力。",
                "keywords": ["管理", "团队", "协同", "跨部门", "沟通", "带领"],
            },
            {
                "id": "language-platform",
                "name": "语言与平台实战",
                "weight": 20,
                "description": "关注英语沟通、客户谈判、平台运营或渠道体系搭建经验。",
                "keywords": list(dict.fromkeys(parsed_jd.get("language_requirements", []) + PLATFORM_KEYWORDS[:2])),
            },
        ]
        focus_tokens = self._split_preferences(answer_map.get("top-abilities", ""))
        if focus_tokens:
            dimensions[0]["description"] = f"{dimensions[0]['description']} 招聘方还特别强调：{'；'.join(focus_tokens[:2])}。"
        if "平台" not in jd_text and not any(keyword in jd_text for keyword in PLATFORM_KEYWORDS):
            dimensions[-1]["name"] = "语言与客户实战"
            dimensions[-1]["description"] = "关注英语沟通、海外客户谈判、客诉处理等对外实战能力。"
            dimensions[-1]["keywords"] = parsed_jd.get("language_requirements", []) or ["英语", "客户", "谈判"]
        return dimensions

    def _build_prompt_bundle(
        self,
        title: str,
        parsed_jd: dict[str, Any],
        role_summary: str,
        hard_constraints: list[dict[str, Any]],
        scoring_dimensions: list[dict[str, Any]],
        boundaries: list[str],
        output_requirements: list[str],
    ) -> dict[str, Any]:
        output_schema = {
            "survival_decision": "PASS | KILL",
            "hard_rule_results": [{"label": "string", "status": "met|unmet|unknown", "evidence": "string|null"}],
            "dimension_scores": [{"name": "string", "stars": 1, "summary": "string"}],
            "warnings": ["string"],
            "info_gaps": ["string"],
            "interview_questions": ["string"],
            "final_recommendation": "string",
        }
        kill_switch = [rule["description"] for rule in hard_constraints] or ["若硬性条件不满足，直接输出 KILL。"]
        goals = [
            "快速区分硬性不匹配与可继续推进的候选人。",
            "所有结论必须带证据，避免无依据脑补。",
            "输出可直接用于招聘复核与面试追问的诊断报告。",
        ]
        rendered_prompt = "\n".join(
            [
                f"# Role: {title} AI 评估中枢",
                "# Context:",
                parsed_jd.get("summary", role_summary),
                "# Goals:",
                *[f"{index}. {goal}" for index, goal in enumerate(goals, start=1)],
                "# Hard Constraints:",
                *[f"- {item}" for item in kill_switch],
                "# Dimensions:",
                *[f"- {dim['name']} ({dim['weight']}%): {dim['description']}" for dim in scoring_dimensions],
                "# Boundaries:",
                *[f"- {item}" for item in boundaries],
                "# Output:",
                *[f"- {item}" for item in output_requirements],
            ]
        )
        return {
            "role": f"{title} AI 评估中枢",
            "context": role_summary,
            "goals": goals,
            "kill_switch": kill_switch,
            "evaluation_dimensions": scoring_dimensions,
            "boundaries": boundaries,
            "output_schema": output_schema,
            "rendered_prompt": rendered_prompt,
        }

    def _extract_candidate_facts(self, text: str, candidate_name_hint: str | None) -> dict[str, Any]:
        candidate_name = candidate_name_hint or self._match_first(text, [r"姓名[:：]?\s*([^\s\n]{2,12})"])
        if not candidate_name:
            lines = [line.strip() for line in re.split(r"[\n\r]+", text) if line.strip()]
            candidate_name = next((line for line in lines if 1 < len(line) <= 12), None)
        gender = self._match_first(text, [r"性别[:：]?\s*(男|女)", r"\b(男|女)\s*/\s*\d{2}岁"])
        age_value = self._match_first(text, [r"(\d{2})\s*岁", r"年龄[:：]?\s*(\d{2})"])
        age = int(age_value) if age_value else None
        experience_years = self._extract_years_requirement(text)
        team_size = self._extract_team_size(text)
        degree = self._extract_degree_requirement(text)
        english_hits = [word for word in LANGUAGE_KEYWORDS if word in text]
        industry_hits = [word for word in INDUSTRY_KEYWORDS if word in text]
        platform_hits = [word for word in PLATFORM_KEYWORDS if word in text]
        risk_hits = [word for word in ["客诉", "延期", "物流", "回款", "纠纷", "风控", "交付"] if word in text]
        headline_metrics = re.findall(r"\d+(?:\.\d+)?(?:万|亿|%|人|年|月|美元)", text)
        return {
            "candidate_name": candidate_name,
            "gender": gender,
            "age": age,
            "experience_years": experience_years,
            "management_team_size": team_size,
            "education_level": degree,
            "english_hits": english_hits,
            "industry_hits": industry_hits,
            "platform_hits": platform_hits,
            "risk_hits": risk_hits,
            "headline_metrics": headline_metrics[:10],
        }

    def _evaluate_rule(self, rule: dict[str, Any], facts: dict[str, Any], text: str) -> dict[str, Any]:
        field = rule["field"]
        value = rule["value"]
        evidence = None
        status = "unknown"
        actual = facts.get(field)
        if field == "experience_years":
            if actual is not None:
                status = "met" if int(actual) >= int(value) else "unmet"
                evidence = self._snippet(text, [f"{actual}年", "经验", "工作经历"])
        elif field == "education_level":
            if actual:
                status = "met" if DEGREE_ORDER.get(str(actual), 0) >= DEGREE_ORDER.get(str(value), 0) else "unmet"
                evidence = self._snippet(text, [str(actual)])
        elif field == "english_level":
            hits = facts.get("english_hits", [])
            if hits:
                actual = hits
                status = "met"
                evidence = self._snippet(text, hits)
        elif field == "management_team_size":
            if actual is not None:
                status = "met" if int(actual) >= int(value) else "unmet"
                evidence = self._snippet(text, [f"{actual}人", "管理", "团队"])
        elif field == "industry_keywords":
            hits = [keyword for keyword in value if keyword in text]
            actual = hits
            status = "met" if hits else ("unmet" if rule.get("required", False) else "unknown")
            evidence = self._snippet(text, hits) if hits else None
        elif field == "platform_keywords":
            hits = [keyword for keyword in value if keyword in text]
            actual = hits
            status = "met" if hits else "unknown"
            evidence = self._snippet(text, hits) if hits else None
        elif field == "custom":
            tokens = rule.get("keywords") or self._tokenize(rule["description"])
            evidence = self._snippet(text, tokens)
            status = "met" if evidence else "unknown"
        return {
            "rule_id": rule["id"],
            "label": rule["label"],
            "required": rule.get("required", True),
            "status": status,
            "expected": value,
            "actual": actual,
            "evidence": evidence,
            "description": rule["description"],
        }

    def _score_dimensions(self, dimensions: list[dict[str, Any]], facts: dict[str, Any], text: str) -> list[dict[str, Any]]:
        scored = []
        for dim in dimensions:
            hits = [keyword for keyword in dim.get("keywords", []) if keyword and keyword in text]
            base = 35 + min(25, len(hits) * 10)
            if dim["id"] == "leadership" and facts.get("management_team_size"):
                base += 20
            if dim["id"] == "language-platform" and (facts.get("english_hits") or facts.get("platform_hits")):
                base += 20
            if dim["id"] == "execution" and facts.get("risk_hits"):
                base += 15
            normalized_score = max(25, min(98, base))
            stars = max(1, min(5, round(normalized_score / 20)))
            scored.append(
                {
                    "id": dim["id"],
                    "name": dim["name"],
                    "weight": dim["weight"],
                    "normalized_score": normalized_score,
                    "stars": stars,
                    "summary": self._dimension_summary(dim["name"], hits, normalized_score),
                    "evidence": self._snippet(text, hits) if hits else None,
                }
            )
        return scored

    def _build_warnings(self, facts: dict[str, Any], profile: dict[str, Any]) -> list[str]:
        warnings = []
        if len(facts.get("headline_metrics", [])) >= 3 and not facts.get("management_team_size"):
            warnings.append("简历出现大量业绩数字，但缺少团队管理或职责归因证据。")
        if any(rule["field"] == "industry_keywords" for rule in profile.get("soft_constraints", [])) and not facts.get("industry_hits"):
            warnings.append("行业贴合度证据偏弱，需确认候选人是否能快速迁移到目标行业。")
        if any(rule["field"] == "english_level" for rule in profile.get("hard_constraints", [])) and not facts.get("english_hits"):
            warnings.append("岗位强调英语，但简历中未找到稳定的英语实战或证书证据。")
        return warnings

    def _build_interview_questions(
        self,
        profile: dict[str, Any],
        unmet_hard: list[dict[str, Any]],
        unknown_hard: list[dict[str, Any]],
        warnings: list[str],
    ) -> list[str]:
        questions = []
        if unmet_hard:
            first = unmet_hard[0]
            questions.append(f"你简历里关于“{first['label']}”未达到要求。请给出一个真实案例，证明你虽然表面不满足条件，但依然能胜任该岗位。")
        if unknown_hard:
            first = unknown_hard[0]
            questions.append(f"请具体拆解你在“{first['label']}”上的实际证据：团队规模、职责边界、结果指标分别是什么？")
        if warnings:
            questions.append(f"你简历里存在“{warnings[0]}”的风险。请用一个最复杂的实战案例证明不是包装出来的。")
        for focus in profile.get("interview_focus", []):
            if len(questions) >= 3:
                break
            questions.append(f"围绕“{focus}”，请给出一个你亲自负责、可量化、可复盘的案例。")
        while len(questions) < 3:
            questions.append("请描述一次你在客户、内部团队和交付压力同时失控时的处理过程，要求讲清动作、取舍和结果。")
        return questions[:3]

    def _recommendation_text(
        self,
        status: str,
        unmet_hard: list[dict[str, Any]],
        unknown_hard: list[dict[str, Any]],
        warnings: list[str],
    ) -> str:
        if status == "auto_reject_review":
            return f"建议标记为自动淘汰待确认。核心原因：{'; '.join(item['label'] for item in unmet_hard)} 未满足。"
        if status == "recommend_interview":
            return "建议进入面试流程，重点验证高压场景下的真实闭环能力。"
        if status == "recommend_reject":
            return "建议淘汰。硬性条件虽然未明确失守，但综合匹配度偏低，难以支撑继续投入面试资源。"
        reasons = [item["label"] for item in unknown_hard] + warnings[:2]
        joined = "；".join(reasons) if reasons else "存在关键证据缺口"
        return f"建议人工复核。当前存在待确认项：{joined}。"

    def _hard_rule_status_label(self, status: str) -> str:
        return {
            "met": "已满足",
            "unmet": "不满足",
            "unknown": "待核实",
        }.get(status, status)

    def _evaluation_status_label(self, status: str) -> str:
        return {
            "auto_reject_review": "自动淘汰待确认",
            "manual_review": "人工复核",
            "recommend_interview": "建议面试",
            "recommend_reject": "建议淘汰",
        }.get(status, status)

    def _build_markdown_report(
        self,
        facts: dict[str, Any],
        survival: str,
        status: str,
        hard_results: list[dict[str, Any]],
        dimension_scores: list[dict[str, Any]],
        warnings: list[str],
        info_gaps: list[str],
        interview_questions: list[str],
        recommendation_text: str,
    ) -> str:
        hard_lines = "\n".join(
            [
                f"- **{item['label']}**：{self._hard_rule_status_label(item['status'])}；证据：{item['evidence'] or '未找到证据'}"
                for item in hard_results
            ]
        )
        dimension_lines = "\n".join(
            [f"- **{item['name']}**：{'★' * item['stars']}{'☆' * (5 - item['stars'])}；{item['summary']}" for item in dimension_scores]
        )
        warning_lines = "\n".join([f"- {item}" for item in warnings]) if warnings else "- 暂未发现明显伪装风险。"
        gap_lines = "\n".join([f"- {item}" for item in info_gaps]) if info_gaps else "- 暂无关键缺口。"
        question_lines = "\n".join([f"{index + 1}. {item}" for index, item in enumerate(interview_questions)])
        return "\n\n".join(
            [
                f"# 候选人匹配度诊断报告\n\n- 候选人：{facts.get('candidate_name') or '未识别'}\n- 生存判定：**{'KILL' if status == 'auto_reject_review' else 'PASS'}**\n- 当前状态：**{self._evaluation_status_label(status)}**",
                "## 硬规则命中/缺失\n" + hard_lines,
                "## 维度评分\n" + dimension_lines,
                "## 履历伪装预警\n" + warning_lines,
                "## 信息缺口\n" + gap_lines,
                "## 致命三问\n" + question_lines,
                "## 最终建议\n" + recommendation_text,
            ]
        )

    def _derive_screening_status(self, hard_results: list[dict[str, Any]], dimension_scores: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float, str, str]:
        unknown_hard = [item for item in hard_results if item["status"] == "unknown" and item.get("required", True)]
        unmet_hard = [item for item in hard_results if item["status"] == "unmet" and item.get("required", True)]
        total_weight = sum(item["weight"] for item in dimension_scores) or 1
        overall_score = round(sum(item["normalized_score"] * (item["weight"] / total_weight) for item in dimension_scores), 1)
        if unmet_hard:
            return unknown_hard, unmet_hard, overall_score, "auto_reject_review", "KILL"
        if unknown_hard:
            return unknown_hard, unmet_hard, overall_score, "manual_review", "PASS"
        if overall_score >= 80:
            return unknown_hard, unmet_hard, overall_score, "recommend_interview", "PASS"
        if overall_score >= 60:
            return unknown_hard, unmet_hard, overall_score, "manual_review", "PASS"
        return unknown_hard, unmet_hard, overall_score, "recommend_reject", "PASS"

    def _build_evidence_bundle(
        self,
        hard_results: list[dict[str, Any]],
        soft_results: list[dict[str, Any]],
        dimension_scores: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        evidence = []
        for item in hard_results + soft_results:
            if item.get("evidence"):
                evidence.append({"source": "rule", "label": item["label"], "evidence": item["evidence"], "status": item["status"]})
        for item in dimension_scores:
            if item.get("evidence"):
                evidence.append({"source": "dimension", "label": item["name"], "evidence": item["evidence"], "status": item["stars"]})
        return evidence

    def _normalize_rules(self, items: Any, fallback: list[dict[str, Any]], required_default: bool) -> list[dict[str, Any]]:
        normalized = []
        for index, item in enumerate(items or [], start=1):
            if not isinstance(item, dict):
                continue
            label = self._clean_text(item.get("label"))
            description = self._clean_text(item.get("description"))
            field = self._identifier(item.get("field"))
            operator = self._identifier(item.get("operator"))
            if not label or not description or not field or not operator:
                continue
            normalized.append(
                {
                    "id": self._identifier(item.get("id")) or f"{field}-{index}",
                    "label": label,
                    "description": description,
                    "field": field,
                    "operator": operator,
                    "value": item.get("value"),
                    "required": bool(item.get("required", required_default)),
                    "source": self._clean_text(item.get("source")) or "llm-generated",
                    "keywords": self._string_list(item.get("keywords")),
                }
            )
        return normalized or fallback

    def _normalize_dimensions(self, items: Any, fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for index, item in enumerate(items or [], start=1):
            if not isinstance(item, dict):
                continue
            name = self._clean_text(item.get("name"))
            description = self._clean_text(item.get("description"))
            weight = self._to_int(item.get("weight"))
            if not name or not description or weight is None:
                continue
            normalized.append(
                {
                    "id": self._identifier(item.get("id")) or f"dimension-{index}",
                    "name": name,
                    "weight": max(5, min(100, weight)),
                    "description": description,
                    "keywords": self._string_list(item.get("keywords")),
                }
            )
        return normalized or fallback

    def _normalize_facts(self, payload: Any, fallback: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            return fallback
        return {
            "candidate_name": self._clean_text(payload.get("candidate_name")) or fallback.get("candidate_name"),
            "gender": self._clean_text(payload.get("gender")) or fallback.get("gender"),
            "age": self._to_int(payload.get("age"), fallback.get("age")),
            "experience_years": self._to_int(payload.get("experience_years"), fallback.get("experience_years")),
            "management_team_size": self._to_int(payload.get("management_team_size"), fallback.get("management_team_size")),
            "education_level": self._clean_text(payload.get("education_level")) or fallback.get("education_level"),
            "english_hits": self._string_list(payload.get("english_hits")) or fallback.get("english_hits", []),
            "industry_hits": self._string_list(payload.get("industry_hits")) or fallback.get("industry_hits", []),
            "platform_hits": self._string_list(payload.get("platform_hits")) or fallback.get("platform_hits", []),
            "risk_hits": self._string_list(payload.get("risk_hits")) or fallback.get("risk_hits", []),
            "headline_metrics": self._string_list(payload.get("headline_metrics")) or fallback.get("headline_metrics", []),
        }

    def _normalize_hard_results(self, items: Any, rules: list[dict[str, Any]], fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(items, list) or not items:
            return fallback
        rule_map = {item["id"]: item for item in rules}
        normalized = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            rule_id = self._identifier(item.get("rule_id")) or self._identifier(item.get("id"))
            source_rule = rule_map.get(rule_id, {})
            label = self._clean_text(item.get("label")) or source_rule.get("label")
            status = self._clean_text(item.get("status"))
            if not label or status not in {"met", "unmet", "unknown"}:
                continue
            normalized.append(
                {
                    "rule_id": rule_id or f"rule-{index}",
                    "label": label,
                    "required": bool(item.get("required", source_rule.get("required", True))),
                    "status": status,
                    "expected": item.get("expected", source_rule.get("value")),
                    "actual": item.get("actual"),
                    "evidence": self._clean_text(item.get("evidence")),
                    "description": self._clean_text(item.get("description")) or source_rule.get("description", ""),
                }
            )
        return normalized or fallback

    def _normalize_dimension_scores(self, items: Any, dimensions: list[dict[str, Any]], fallback: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not isinstance(items, list) or not items:
            return fallback
        dimension_map = {item["id"]: item for item in dimensions}
        normalized = []
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            dim_id = self._identifier(item.get("id"))
            source_dimension = dimension_map.get(dim_id, {})
            name = self._clean_text(item.get("name")) or source_dimension.get("name")
            weight = self._to_int(item.get("weight"), source_dimension.get("weight"))
            normalized_score = self._to_int(item.get("normalized_score"))
            stars = self._to_int(item.get("stars"))
            if normalized_score is None and stars is not None:
                normalized_score = stars * 20
            if stars is None and normalized_score is not None:
                stars = max(1, min(5, round(normalized_score / 20)))
            if not name or weight is None or normalized_score is None or stars is None:
                continue
            normalized.append(
                {
                    "id": dim_id or f"dimension-{index}",
                    "name": name,
                    "weight": max(5, min(100, weight)),
                    "normalized_score": max(0, min(100, normalized_score)),
                    "stars": max(1, min(5, stars)),
                    "summary": self._clean_text(item.get("summary")) or f"{name} 缺少明确证据，建议人工复核。",
                    "evidence": self._clean_text(item.get("evidence")),
                }
            )
        return normalized or fallback

    def _dimension_summary(self, name: str, hits: list[str], score: int) -> str:
        if hits:
            return f"{name} 命中了 {', '.join(hits[:3])} 等证据，当前判断分数为 {score}。"
        return f"{name} 缺少明确证据，当前判断分数为 {score}，建议人工复核。"

    def _extract_years_requirement(self, text: str) -> int | None:
        patterns = [r"(\d+)\s*年以上", r"(\d+)\s*年.*经验", r"至少\s*(\d+)\s*年"]
        values: list[int] = []
        for pattern in patterns:
            values.extend(int(item) for item in re.findall(pattern, text))
        return max(values) if values else None

    def _extract_degree_requirement(self, text: str) -> str | None:
        for degree in ["博士", "硕士", "MBA", "本科", "大专", "高中"]:
            if degree in text:
                return degree
        return None

    def _extract_team_size(self, text: str) -> int | None:
        matches = re.findall(r"(?:管理|带领|带队|团队规模|团队人数|管理过)[^\d]{0,8}(\d{1,3})\s*人", text)
        if not matches:
            return None
        return max(int(item) for item in matches)

    def _split_preferences(self, text: str) -> list[str]:
        chunks = re.split(r"[；;。\n]|(?:\d+[、.])", text)
        return [chunk.strip(" -") for chunk in chunks if len(chunk.strip()) > 4]

    def _rule(self, rule_id: str, label: str, field: str, operator: str, value: Any, description: str, required: bool = True, keywords: list[str] | None = None) -> dict[str, Any]:
        return {
            "id": rule_id,
            "label": label,
            "description": description,
            "field": field,
            "operator": operator,
            "value": value,
            "required": required,
            "source": "ai-generated",
            "keywords": keywords or [],
        }

    def _pick_keywords(self, text: str, keywords: list[str]) -> list[str]:
        return [item for item in keywords if item in text]

    def _match_first(self, text: str, patterns: list[str]) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _snippet(self, text: str, keywords: list[str]) -> str | None:
        clean_text = re.sub(r"\s+", " ", text)
        for keyword in keywords:
            if not keyword:
                continue
            index = clean_text.find(keyword)
            if index >= 0:
                start = max(0, index - 30)
                end = min(len(clean_text), index + len(keyword) + 40)
                return clean_text[start:end]
        return None

    def _tokenize(self, text: str) -> list[str]:
        return [token for token in re.split(r"[\s,，。；;、]+", text) if len(token) >= 2][:6]

    def _clean_text(self, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _recommendation_from_payload(self, value: Any) -> str | None:
        if isinstance(value, dict):
            summary = self._clean_text(value.get("summary"))
            decision = self._clean_text(value.get("decision"))
            risks = self._string_list(value.get("risks"))
            strengths = self._string_list(value.get("strengths"))
            parts = [part for part in [decision, summary] if part]
            if strengths:
                parts.append(f"亮点：{'；'.join(strengths[:3])}")
            if risks:
                parts.append(f"风险：{'；'.join(risks[:3])}")
            return " ".join(parts) if parts else None
        return self._clean_text(value)

    def _to_int(self, value: Any, default: int | None = None) -> int | None:
        if value is None:
            return default
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    def _identifier(self, value: Any) -> str | None:
        text = self._clean_text(value)
        if not text:
            return None
        sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "-", text).strip("-").lower()
        return sanitized or None

    def _string_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return self._dedupe([text for text in (self._clean_text(item) for item in value) if text])

    def _dedupe(self, items: list[str]) -> list[str]:
        seen = set()
        ordered = []
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered

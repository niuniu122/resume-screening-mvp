from __future__ import annotations

import json
from types import SimpleNamespace

from app.config import Settings
import app.services.recruiting_engine as engine_module


def make_client_with_json(payload: dict):
    class FakeChatCompletions:
        def create(self, **kwargs):
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))
                    )
                ]
            )

    class FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(completions=FakeChatCompletions())

    return FakeClient()


def test_parse_jd_prefers_llm_output(monkeypatch) -> None:
    payload = {
        "title": "外贸经理",
        "seniority": "经理",
        "industry_tags": ["包装", "制造"],
        "language_requirements": ["英语"],
        "experience_years": 5,
        "degree_requirement": "本科",
        "summary": "负责制造型外贸团队管理与客户谈判。",
        "risk_flags": ["英语要求需要验证实战能力"],
    }
    monkeypatch.setattr(
        engine_module,
        "get_settings",
        lambda: Settings(openai_api_key="test-key", openai_model="gpt-5.4", openai_base_url="https://example.com/v1"),
    )
    monkeypatch.setattr(engine_module, "OpenAI", lambda **kwargs: make_client_with_json(payload))

    engine = engine_module.RecruitingEngine()
    result = engine.parse_jd("外贸经理，需要英语和5年以上经验，本科。")

    assert result.model_version == "gpt-5.4"
    assert result.data["title"] == "外贸经理"
    assert result.data["industry_tags"] == ["包装", "制造"]


def test_evaluate_resume_falls_back_when_model_calls_fail(monkeypatch) -> None:
    class BrokenResponses:
        def create(self, **kwargs):
            raise RuntimeError("responses failed")

    class BrokenChatCompletions:
        def create(self, **kwargs):
            raise RuntimeError("chat failed")

    class BrokenClient:
        def __init__(self):
            self.responses = BrokenResponses()
            self.chat = SimpleNamespace(completions=BrokenChatCompletions())

    monkeypatch.setattr(
        engine_module,
        "get_settings",
        lambda: Settings(openai_api_key="test-key", openai_model="gpt-5.4", openai_base_url="https://example.com/v1"),
    )
    monkeypatch.setattr(engine_module, "OpenAI", lambda **kwargs: BrokenClient())

    engine = engine_module.RecruitingEngine()
    profile = {
        "hard_constraints": [
            {
                "id": "lang-english",
                "label": "英语沟通",
                "description": "需要能在工作中使用英语沟通。",
                "field": "english_level",
                "operator": "required",
                "value": ["英语"],
                "required": True,
                "source": "ai-generated",
                "keywords": ["英语"],
            }
        ],
        "soft_constraints": [],
        "scoring_dimensions": [
            {
                "id": "language-platform",
                "name": "语言与平台实战",
                "weight": 100,
                "description": "关注英语沟通和客户谈判能力。",
                "keywords": ["英语", "谈判"],
            }
        ],
        "interview_focus": ["英语口语真实谈判能力"],
    }

    result = engine.evaluate_resume(profile, "姓名：蓝小姐\n本科\n5年外贸经验\n英语谈判与客户沟通", "蓝小姐")

    assert result.model_version == "heuristic-v1"
    assert result.data["candidate_name"] == "蓝小姐"
    assert result.data["status"] in {"manual_review", "recommend_interview"}

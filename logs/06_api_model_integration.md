# 06 API Model Integration

## 目标

- 将简历初筛系统从“仅启发式规则”升级为“模型主判 + 规则兜底”的模式。
- 保持项目配置与本地 `Codex` 配置隔离，只在项目内配置模型 API。

## 本轮完成内容

- 后端新增 `OPENAI_BASE_URL` 与 `OPENAI_TIMEOUT_SECONDS` 配置。
- `RecruitingEngine` 已接入真实模型调用：
  - JD 解析
  - AI 追问生成
  - 岗位画像编译
  - 简历评估
- 当模型接口异常、返回空内容或非预期 JSON 时，系统会自动回退到内置启发式引擎。
- 项目内新增 `backend/.env`，用于本地运行时读取模型配置，不影响 `%USERPROFILE%\\.codex`。
- 新增 API 集成测试，覆盖“模型分支可用”和“失败时自动回退”。
- 测试默认通过 `backend/tests/conftest.py` 禁用真实模型网络调用，保证 CI 稳定和速度。

## 验证结果

- `cd backend && pytest -q`：`8 passed`
- 真实 API 烟雾验证：
  - `parse_jd` 已返回 `model_version = gpt-5.4`
  - 中文 JD 在真实 API 下可正确识别岗位标题
  - `evaluate_resume` 已返回真实模型评估结果

## 关键文件

- [backend/app/services/recruiting_engine.py](C:/Users/Administrator/Desktop/JD/backend/app/services/recruiting_engine.py)
- [backend/app/config.py](C:/Users/Administrator/Desktop/JD/backend/app/config.py)
- [backend/.env](C:/Users/Administrator/Desktop/JD/backend/.env)
- [backend/.env.example](C:/Users/Administrator/Desktop/JD/backend/.env.example)
- [backend/tests/test_recruiting_engine_api.py](C:/Users/Administrator/Desktop/JD/backend/tests/test_recruiting_engine_api.py)
- [backend/tests/conftest.py](C:/Users/Administrator/Desktop/JD/backend/tests/conftest.py)

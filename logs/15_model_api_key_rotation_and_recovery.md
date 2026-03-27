# 模块日志 15：模型 API Key 轮换与恢复

## 时间
- 2026-03-27

## 背景
- 之前项目内的模型上游鉴权返回 `401 AuthenticationError`，系统会自动回退到 `heuristic-v1`。
- 用户提供了新的模型 API key，并要求仅在项目内恢复，不影响本地 Codex 配置。

## 本次处理
1. 仅更新项目内的 [backend/.env](C:/Users/Administrator/Desktop/JD/backend/.env) 中的 `OPENAI_API_KEY`。
2. 未修改 `%USERPROFILE%\\.codex` 下的任何配置文件。
3. 重启运行中的后端服务，使新环境变量生效。
4. 依次验证：
   - 上游模型目录接口可鉴权访问。
   - 应用本地 `/health` 正常。
   - `RecruitingEngine` 的 `parse_jd`、`generate_follow_up_questions`、`compile_profile`、`evaluate_resume` 四段链路均重新走模型。

## 验证结果
- `GET {OPENAI_BASE_URL}/models`：`200`
- `GET http://127.0.0.1:8010/health`：`200`
- 引擎链路验证：
  - `parse_model_version = gpt-5.4`
  - `question_model_version = gpt-5.4`
  - `profile_model_version = gpt-5.4`
  - `resume_model_version = gpt-5.4`
  - `question_count = 8`
  - `has_prompt_bundle = true`

## 结论
- 项目内模型 API 已恢复到可用状态。
- 当前系统已重新回到“真实模型主判，启发式兜底”的运行方式。
- 本次恢复未影响本地 Codex 的全局配置。

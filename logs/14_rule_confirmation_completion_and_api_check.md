# 模块日志：规则确认补全与 API 检查

## 时间
- 2026-03-27

## 问题描述
- `Step 3 / 规则确认` 只展示了：
  - `role_summary`
  - `hard_constraints`
  - `soft_constraints`
  - `scoring_dimensions`
- 用户在 `Step 2 / AI 追问` 中填写的这两类信息在规则确认里看不到：
  - `你最怕招错哪种人`
  - `平台与体系要求`

## 根因
- 前端没有展示 `output_requirements`、`interview_focus`、`boundaries`。
- 后端启发式画像编译也没有把 `hire-risk`、`platform-proof`、`fake-signals`、`tradeoff` 这些追问答案完整写入画像字段。

## 修复内容
- 前端文件：`frontend/components/resume-screening-app.tsx`
  - 在规则确认中新增展示并可编辑：
    - `输出要求`
    - `面试追问重点`
    - `边界条件与失败画像`
    - `PromptBundle 预览`
- 后端文件：`backend/app/services/recruiting_engine.py`
  - `platform-proof` 现在会进入：
    - `soft_constraints`
    - `output_requirements`
    - `interview_focus`
  - `hire-risk` 现在会进入：
    - `boundaries`
  - 同时把 `fake-signals`、`tradeoff` 也纳入 `boundaries`
  - LLM 编译结果归一化时，`output_requirements` / `interview_focus` / `boundaries` 与启发式回退结果做去重合并，避免模型漏掉这些字段
- 后端文件：`backend/app/main.py`
  - 冻结岗位画像时，会根据当前编辑后的规则重新生成 `prompt_bundle`，避免用户改了规则但底层提示词没更新

## 回归测试
- 新增测试：`backend/tests/test_profile_draft.py`
  - 验证 `失败画像 / 平台与体系要求` 不会在编译画像时丢失
- 执行结果：
  - `pytest -q` -> `10 passed`
  - `npm run build` -> 通过

## API 实测
- 应用 API：
  - `GET /health` -> `200`
  - 使用现有岗位再次调用 `POST /jobs/{id}/interview/answer` 后，返回草稿里已经包含：
    - `平台与体系要求`
    - `重点规避的失败画像`
    - `重点拆穿的履历伪装信号`
- 上游模型 API：
  - 当前项目配置已加载到：
    - `OPENAI_API_KEY` 已存在
    - `OPENAI_BASE_URL` 已存在
    - 模型为 `gpt-5.4`
  - 但直接调用模型时，当前返回 `401 AuthenticationError`
  - 错误含义：令牌无效

## 当前结论
- 系统自己的应用 API 是正常的。
- 规则确认缺失字段的问题已经修好。
- 当前真实模型 API 鉴权失败，所以系统会自动退回启发式逻辑，直到更换有效 key。

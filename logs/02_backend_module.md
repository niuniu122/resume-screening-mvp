# 模块日志 02：后端模块

## 状态
- 已完成

## 目标
- 实现 JD 导入、追问回答、画像冻结、简历上传、自动评估、人工改判、审计日志。

## 实际落地文件
- `backend/requirements.txt`
- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/models.py`
- `backend/app/schemas.py`
- `backend/app/services/document_parser.py`
- `backend/app/services/recruiting_engine.py`
- `backend/app/main.py`
- `backend/tests/conftest.py`
- `backend/tests/test_workflow.py`

## API 完成情况
- 已实现 `POST /jobs/import-jd`
- 已实现 `POST /jobs/{id}/interview/answer`
- 已实现 `POST /jobs/{id}/freeze-profile`
- 已实现 `POST /jobs/{id}/resumes`
- 已实现 `GET /jobs`
- 已实现 `GET /jobs/{id}`
- 已实现 `GET /jobs/{id}/dashboard`
- 已实现 `GET /evaluations/{id}`
- 已实现 `POST /evaluations/{id}/decision`
- 已实现 `GET /health`

## 完成内容
- 建立了 `Job`、`RecruiterInterviewSession`、`ScreeningProfileVersion`、`ResumeSubmission`、`CandidateProfile`、`EvaluationResult`、`ReviewDecision`、`AuditLog` 数据模型。
- 支持 TXT / PDF / DOCX 文档解析和本地存储。
- 实现启发式 JD 解析、AI 追问生成、岗位画像编译、简历评估和 Markdown 报告输出。
- 实现异步简历处理与人工改判落库。
- 所有评估记录都保留模型版本、画像版本和审计日志。

## 测试结果
- `pytest -q`
- 结果：2 个测试通过

## 已知限制
- 当前默认使用 SQLite 本地库，方便本机运行；生产环境建议切换到 PostgreSQL。
- 当前评估引擎默认是启发式规则优先，已预留云端模型配置入口，但未强依赖外部 API。
- FastAPI 使用了 `on_event("startup")`，运行正常，但有 deprecation warning，后续可迁移到 lifespan。

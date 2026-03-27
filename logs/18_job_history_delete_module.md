# 模块日志 18：岗位历史删除

## 时间
- 2026-03-27

## 目标
- 让“岗位历史”支持直接删除历史岗位。
- 删除时同时清理岗位关联的简历、报告与上传文件。

## 本次改动
- 后端
  - `backend/app/services/storage.py`
    - 为本地存储和 OSS 存储补充 `delete(key)` 能力。
  - `backend/app/schemas.py`
    - 新增 `DeleteJobResponse`。
  - `backend/app/main.py`
    - 新增 `DELETE /jobs/{job_id}`。
    - 删除前先清空 `current_profile_version_id`。
    - 删除后级联清理岗位、追问会话、画像版本、简历提交、候选人画像、评估结果与复核记录。
    - 同时清理岗位 JD 文件和简历原文件。
- 前端
  - `frontend/lib/types.ts`
    - 新增删除岗位响应类型。
  - `frontend/lib/api.ts`
    - 新增 `deleteJob(jobId)`。
  - `frontend/components/resume-screening-app.tsx`
    - 在“岗位历史”卡片上新增删除按钮和二次确认弹窗。
    - 删除后自动刷新历史列表。
    - 若删除的是当前选中岗位，自动切到下一个岗位；如果没有剩余岗位，则清空当前工作区状态。

## 验证
- 后端测试：
  - `pytest -q` -> `11 passed`
- 前端构建：
  - `npm run build` -> 通过
- 接口烟雾测试：
  - 新建临时岗位
  - 调用 `DELETE /jobs/{job_id}` 返回 `200`
  - 再访问 `GET /jobs/{job_id}` 返回 `404`
- 运行中服务验证：
  - `GET http://127.0.0.1:8010/health` -> `200`
  - `GET https://6d072b50cdb21a.lhr.life/health` -> `200`

## 结果
- 当前公网测试版已经支持删除岗位历史。
- 浏览器刷新后即可看到删除入口。

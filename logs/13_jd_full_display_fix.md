# 模块日志：JD 完整展示修复

## 时间
- 2026-03-27

## 问题描述
- “当前岗位”卡片只展示了 `parsed_jd.summary` 摘要，用户无法完整查看 JD 要求。

## 修复内容
- 后端：
  - 在 `JobDetail` 中新增 `jd_text` 字段。
  - `build_job_detail` 现在会把岗位原始 JD 文本返回给前端。
- 前端：
  - “当前岗位”卡片从单行摘要改为三段式展示：
    - 岗位摘要
    - 关键要求
    - JD 要求全文
  - JD 全文区域支持滚动查看，避免长文本被截断。
  - 对归一化后的 JD 文本增加简单格式化，让“岗位职责 / 任职要求 / 编号条目”更易读。

## 相关文件
- `backend/app/schemas.py`
- `backend/app/main.py`
- `frontend/lib/types.ts`
- `frontend/components/resume-screening-app.tsx`

## 验证结果
- 后端测试：`pytest -q` 通过，共 `9 passed`
- 前端构建：`npm run build` 通过
- 接口验证：
  - `GET /jobs/{job_id}` 现已返回 `jd_text`
  - 当前岗位 `外贸经理` 的 JD 全文可通过接口正常读取

## 额外处理
- 为让当前运行中的测试站立即生效，重启了本地后端进程。
- 后端重启后重新执行了 `restore_demo_data.py`，把演示岗位和候选人数据重新灌回当前运行中的数据库。

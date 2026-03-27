# Codespaces 后端保活工作流记录

- 时间：2026-03-27
- 模块：GitHub Actions 保活

## 已完成

- 新增工作流：
  - `.github/workflows/keep-codespaces-backend-awake.yml`
- 工作流会每 `10` 分钟访问一次当前配置的后端健康检查地址：
  - `${{ vars.NEXT_PUBLIC_API_BASE_URL }}/health`
- 同时支持手动触发，便于现场验证。

## 目的

- 在测试阶段尽量减少 GitHub Codespace 因空闲而暂停。
- 即便没有人在页面上频繁操作，也会定期向后端发起一次可观测请求。

## 边界

- 这是“尽量保活”，不是平台级 SLA。
- 如果 Codespaces 平台策略或账户配额发生变化，仍可能出现暂停或唤醒延迟。

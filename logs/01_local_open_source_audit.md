# 模块日志 01：本机开源项目审计

## 时间
- 2026-03-26

## 目标
- 扫描本机可复用的开源项目，确认是否存在适合作为本次“简历初筛 Web MVP”开发基座的仓库。

## 发现
- `C:\Users\Administrator\Desktop\codex_openclaw\workspace\hermes-agent`
  - 完整 Python/Node 混合开源仓。
  - 更偏 AI Agent 基础设施，不是招聘系统，但可借鉴 Python 项目结构、依赖管理、测试组织方式。
- `C:\Users\Administrator\Desktop\codex_openclaw\workspace\openclaw-china`
  - Node monorepo，偏扩展与工作区管理。
  - 不适合作为本次业务系统直接基座，但可借鉴 workspace 组织方式。
- `C:\Users\Administrator\Desktop\codex_openclaw\workspace\opencli`
  - Node CLI 开源项目，结构完整。
  - 适合作为 TypeScript 工程规范参考，不适合作为业务 UI 基座。
- `C:\Users\Administrator\Desktop\codex_openclaw\workspace\pua\landing`
  - React/Vite 前端项目，适合作为视觉与组件拆分参考。
- `C:\Users\Administrator\.agents\skills\superpowers`
  - 实际为一个 junction，指向失效路径。
  - 本机不存在可直接使用的 `superpower` 实际项目内容。

## 结论
- 本机没有现成的“简历筛选系统”开源项目可直接改造。
- 当前开发将以 `JD` 目录为主仓进行定制实现。
- 工程参考来源：
  - 后端规范参考 `hermes-agent`
  - 前端组织与视觉参考 `pua/landing`
  - TypeScript 工程化参考 `opencli`

## 后续动作
- 在当前项目内直接搭建 `frontend` + `backend` 双目录结构。
- 每完成一个模块，补一份对应 Markdown 日志到 `logs/`。

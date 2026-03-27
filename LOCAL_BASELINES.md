# 本地开发基线说明

本项目没有在本机找到可直接改造的“简历筛选系统”开源仓，因此采用“当前仓定制实现 + 借用本机成熟开源项目的工程习惯”的方式推进。

## 已确认的本地参考项目

### 1. `C:\Users\Administrator\Desktop\codex_openclaw\workspace\hermes-agent`
- 用途：参考 Python 项目组织、依赖拆分、测试目录结构。
- 适用面：`backend/` 的工程化方式与测试风格。

### 2. `C:\Users\Administrator\Desktop\codex_openclaw\workspace\opencli`
- 用途：参考 TypeScript 工程脚本、开发体验、测试命令组织。
- 适用面：`frontend/` 的脚本与工程约束设计思路。

### 3. `C:\Users\Administrator\Desktop\codex_openclaw\workspace\pua\landing`
- 用途：参考现代 React 页面拆分与视觉层次。
- 适用面：内部工具型 Web 前端的视觉和组件组织灵感。

## 未能使用的项目

### `superpowers`
- 本机仅存在一个失效的 junction：`C:\Users\Administrator\.agents\skills\superpowers`
- 指向的真实目录不存在，因此无法作为这次开发的可用依赖或模板。

## 当前策略
- 主仓：`C:\Users\Administrator\Desktop\JD`
- 代码组织：`frontend/` + `backend/` + `logs/`
- 日志策略：每完成一个模块，在 `logs/` 下补一份 Markdown 日志

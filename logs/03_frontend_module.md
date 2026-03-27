# 模块日志 03：前端模块

## 状态
- 已完成

## 目标
- 实现岗位创建、AI 追问、规则确认、筛选看板四步工作台，以及岗位历史与报告查看。

## 实际落地文件
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/next.config.mjs`
- `frontend/next-env.d.ts`
- `frontend/app/layout.tsx`
- `frontend/app/page.tsx`
- `frontend/app/globals.css`
- `frontend/lib/api.ts`
- `frontend/lib/types.ts`
- `frontend/components/resume-screening-app.tsx`
- `frontend/components/evaluation-drawer.tsx`

## 页面与组件完成情况
- 已完成左侧岗位历史栏，可切换历史岗位并刷新。
- 已完成 4 步主工作台：岗位创建、AI 追问、规则确认、筛选看板。
- 已完成岗位画像编辑区，可修改硬条件、软条件和评分维度。
- 已完成简历批量上传入口与筛选统计卡片。
- 已完成候选人报告抽屉，支持查看 Markdown 报告、信息缺口、压力面试题和人工结论提交。

## 构建结果
- `npm run build`
- 结果：构建通过

## 视觉与交互
- 使用了中文内部工具视觉风格，带玻璃态卡片、渐变背景和双字体层级。
- 保留 Ant Design 的稳定性，同时通过自定义主题变量避免页面太像默认后台模板。

## 已知限制
- 当前前端为单页工作台，历史中心和详情都在同一页内切换，首版足够但后续可拆成多页面。
- 暂未接入登录态，人工改判默认以 `Recruiter` 身份提交。

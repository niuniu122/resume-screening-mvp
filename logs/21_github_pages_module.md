# 模块日志 21：GitHub Pages 发布接入

## 时间
- 2026-03-27

## 目标
- 让前端可以发布到 GitHub Pages
- 允许页面运行时手动指定后端地址，适配“前端在 GitHub，后端在本地电脑”的过渡方案

## 本次改动
- 前端
  - `frontend/lib/api.ts`
    - 增加运行时 API 地址覆盖能力
    - 支持从 `localStorage` 读取和保存后端地址
  - `frontend/components/resume-screening-app.tsx`
    - 增加“后端地址”设置卡片
    - 在 GitHub Pages 环境下，如果没有配置后端地址，则不自动请求错误的同源接口
  - `frontend/next.config.mjs`
    - 增加 `PAGES_BASE_PATH` 支持，适配 GitHub Pages 子路径部署
  - `frontend/public/.nojekyll`
    - 防止 GitHub Pages 用 Jekyll 处理 `_next` 目录
- 自动发布
  - `.github/workflows/pages.yml`
    - 新增 GitHub Pages 自动发布 workflow
    - 支持根据仓库名自动计算 Pages base path
- 发布辅助
  - `deploy/github-pages/README.md`
    - 补充 GitHub Pages 使用说明
  - `deploy/github-pages/publish-github-pages.ps1`
    - 一键创建仓库、推送代码、可选设置前端默认 API 地址
- 仓库准备
  - 初始化本地 Git 仓库
  - 完成两次本地提交，便于后续直接推送

## 验证
- `npm run build`：通过
- `PAGES_BASE_PATH=/resume-screening-mvp` 的构建：通过
- 静态产物检查：
  - `frontend/out/index.html` 已正确带上 `/resume-screening-mvp/` 资源前缀
  - `frontend/out/.nojekyll` 已生成

## 当前状态
- 项目已经具备推送到 GitHub 并用 GitHub Pages 发布前端的能力
- 仍需用户本人完成 GitHub 认证
- 后端如果继续放在本地电脑上，仍需要一个长期稳定的公网地址

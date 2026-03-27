# GitHub Pages 发布成功记录

- 时间：2026-03-27
- 模块：GitHub Pages 前端发布与本机后端联调准备

## 已完成

- GitHub CLI 登录成功。
- 已创建公开仓库：`niuniu122/resume-screening-mvp`。
- 已将当前项目推送到远程 `origin/main`。
- GitHub Pages workflow 成功执行完成。
- 前端访问地址已生效：
  - `https://niuniu122.github.io/resume-screening-mvp/`

## 后端联调收口

- 后端 `.env` 已加入 `https://niuniu122.github.io` 到 `CORS_ORIGINS`。
- 修复了 `deploy/runtime/run-backend.cmd` 中写死旧隧道域名的问题，改为直接读取项目内环境配置。
- 已重启本机后端，健康检查正常。

## 验证

- GitHub Pages 首页返回 `200`。
- 本机后端健康检查 `http://127.0.0.1:8010/health` 返回 `200`。
- 带 `Origin: https://niuniu122.github.io` 请求本机后端时，`Access-Control-Allow-Origin` 正常返回 `https://niuniu122.github.io`。

## 说明

- 现在前端已经稳定挂在 GitHub Pages 上。
- 真正给其他人使用时，仍需要把你电脑上的后端通过一个可访问的公网地址暴露出去，并在前端页面里的“后端地址”处填写该地址。

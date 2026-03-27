# GitHub Codespaces 公网后端发布记录

- 时间：2026-03-27
- 模块：GitHub Pages 前端 + GitHub Codespaces 公网后端联通

## 已完成

- 为仓库补充 Codespaces 运行配置：
  - `.devcontainer/devcontainer.json`
  - `.devcontainer/post-create.sh`
  - `.devcontainer/post-start.sh`
- 在 Codespace 中创建并启动后端环境：
  - 仓库：`niuniu122/resume-screening-mvp`
  - Codespace：`resume-screening-api-q76w69g6jp5pf694p`
- 在 Codespace 中创建 Python 虚拟环境并安装 `backend/requirements.txt`。
- 在 Codespace 中写入项目运行环境并启动 FastAPI 后端。
- 将 Codespace 的 `8010` 端口公开。
- 将 GitHub Pages 前端默认 API 地址更新为 Codespaces 后端公网地址，并重新触发 Pages 发布。
- 为 Codespaces 配置用户级密钥：
  - `OPENAI_API_KEY`
  - `OPENAI_MODEL`
  - `OPENAI_BASE_URL`

## 最终对外地址

- 前端：
  - `https://niuniu122.github.io/resume-screening-mvp/`
- 后端：
  - `https://resume-screening-api-q76w69g6jp5pf694p-8010.app.github.dev`

## 验证

- `GET /health`：
  - `https://resume-screening-api-q76w69g6jp5pf694p-8010.app.github.dev/health`
  - 返回 `200 {"status":"ok"}`
- CORS：
  - 以 `Origin: https://niuniu122.github.io` 请求后端时，正常返回 `Access-Control-Allow-Origin: https://niuniu122.github.io`
- 业务接口：
  - `POST /jobs/import-jd` 已通过公网后端成功返回结果

## 注意事项

- 当前 Codespace 机器规格为 `basicLinux32gb`，空闲超时为 `30 minutes`。
- 现在已经补上 `post-start.sh` 和 Codespaces 密钥，后续 Codespace 重启时可自动重建 `.env` 并重新拉起后端。
- GitHub Actions 页面部署目前会提示 `Node.js 20 actions are deprecated`，但本次发布成功，不影响当前使用。

# 05 Deployment Module

## 目标

- 将当前本地可运行的简历初筛系统改造成适合单人维护、可上线发布的版本。
- 落地阿里云部署路径：前端静态导出到 OSS/CDN，后端容器化部署到 SAE，数据库切换到 PostgreSQL，文件存储切换到 OSS。

## 本轮完成内容

- 后端新增 `DATABASE_URL`、`STORAGE_BACKEND`、`OSS_*`、`PUBLIC_API_BASE_URL` 等生产配置。
- 后端抽象出本地 / OSS 双存储实现，上传的 JD 和简历可在生产环境落到 OSS。
- 前端改为 `Next.js` 静态导出模式，构建产物落在 `frontend/out/`。
- 新增后端 Dockerfile，用于构建 SAE 可部署镜像。
- 新增阿里云部署说明、单人上线检查清单和 PowerShell 构建脚本。
- 保留本地开发模式，不影响当前开发测试流程。

## 关键文件

- [README.md](C:/Users/Administrator/Desktop/JD/README.md)
- [backend/DEPLOYMENT.md](C:/Users/Administrator/Desktop/JD/backend/DEPLOYMENT.md)
- [frontend/DEPLOYMENT.md](C:/Users/Administrator/Desktop/JD/frontend/DEPLOYMENT.md)
- [deploy/alicloud/README.md](C:/Users/Administrator/Desktop/JD/deploy/alicloud/README.md)
- [deploy/alicloud/release-checklist.md](C:/Users/Administrator/Desktop/JD/deploy/alicloud/release-checklist.md)
- [deploy/alicloud/export-frontend.ps1](C:/Users/Administrator/Desktop/JD/deploy/alicloud/export-frontend.ps1)
- [deploy/alicloud/build-backend-image.ps1](C:/Users/Administrator/Desktop/JD/deploy/alicloud/build-backend-image.ps1)

## 验证结果

- `cd backend && pytest -q`
- `cd frontend && npm run build`
- `cd backend && python scripts/init_db.py`
- 后端测试通过：`6 passed`
- 前端生产构建通过：已成功导出静态页到 `frontend/out/`
- 初始化脚本已验证可运行
- 当前机器未安装 Docker，因此未能在本机完成镜像构建验证；镜像文件与脚本已准备好，可在有 Docker 的机器或 CI/CD 中执行

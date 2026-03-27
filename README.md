# 简历初筛 Web MVP

一个面向招聘人员的内部工作台，用来完成：
- 上传岗位 JD
- 回答 AI 追问，冻结岗位画像
- 批量上传简历
- 自动输出结构化筛选报告
- 人工确认最终筛选结论

## 目录结构

- `backend/`：FastAPI + SQLAlchemy 服务
- `frontend/`：Next.js + TypeScript + Ant Design 前端
- `logs/`：模块开发日志
- `LOCAL_BASELINES.md`：本机可复用开源基线说明

## 后端启动

```powershell
cd C:\Users\Administrator\Desktop\JD\backend
uvicorn app.main:app --reload
```

默认地址：
- API: `http://localhost:8000`
- 健康检查: `http://localhost:8000/health`

## 前端启动

```powershell
cd C:\Users\Administrator\Desktop\JD\frontend
$env:NEXT_PUBLIC_API_BASE_URL="http://localhost:8000"
npm run dev
```

默认地址：
- Web: `http://localhost:3000`

## 已验证命令

```powershell
cd C:\Users\Administrator\Desktop\JD\backend
pytest -q

cd C:\Users\Administrator\Desktop\JD\frontend
npm run build
```

## 当前实现说明

- 默认使用 SQLite，数据库文件会生成在 `backend/` 目录下。
- JD 与简历文件默认保存到 `backend/storage/`。
- 评估引擎现在支持接入云端模型 API，岗位解析、追问生成、岗位画像编译和简历评估都会优先走模型；API 异常时再回退到启发式引擎。
- 模型配置读取项目内的 `backend/.env` 或运行时环境变量，不依赖本地 `Codex` 配置文件。
- 所有模块日志都保存在 `logs/` 下，方便回看开发过程。

## 当前上线形态

项目现在已经补齐了适合单人维护和上线的生产化基础：

- 前端支持 `Next.js` 静态导出，构建产物会输出到 `frontend/out/`，适合发布到阿里云 OSS + CDN。
- 后端提供 `Dockerfile`，适合构建镜像后发布到阿里云 SAE。
- 数据库已经支持通过 `DATABASE_URL` 切换到 PostgreSQL。
- 文件存储已经抽象为 `local / oss` 两套实现，生产环境可直接切到阿里云 OSS。
- 根目录下提供了阿里云部署说明、后端部署说明和本轮部署日志，便于你一个人持续维护。

## 单人上线推荐路径

建议按下面的顺序推进：

1. 在阿里云准备 `OSS + CDN + ACR + SAE + RDS PostgreSQL`。
2. 按 [deploy/alicloud/README.md](C:/Users/Administrator/Desktop/JD/deploy/alicloud/README.md) 准备生产环境变量。
3. 在本机执行前端静态导出和后端镜像构建。
4. 将 `frontend/out/` 上传到 OSS 静态站点 Bucket，并把后端镜像推到 ACR。
5. 在 SAE 中配置后端环境变量并部署镜像。
6. 用 `app.xxx.com` 指向前端站点，用 `api.xxx.com` 指向后端 API。
7. 完成一次真实烟雾测试，再把地址发给使用者。

## 生产部署入口

- 阿里云整体流程说明：[deploy/alicloud/README.md](C:/Users/Administrator/Desktop/JD/deploy/alicloud/README.md)
- 单人上线检查清单：[deploy/alicloud/release-checklist.md](C:/Users/Administrator/Desktop/JD/deploy/alicloud/release-checklist.md)
- 后端生产变量说明：[backend/DEPLOYMENT.md](C:/Users/Administrator/Desktop/JD/backend/DEPLOYMENT.md)
- 前端静态发布说明：[frontend/DEPLOYMENT.md](C:/Users/Administrator/Desktop/JD/frontend/DEPLOYMENT.md)
- 后端环境变量示例：[backend/.env.example](C:/Users/Administrator/Desktop/JD/backend/.env.example)
- 前端环境变量示例：[frontend/.env.production.example](C:/Users/Administrator/Desktop/JD/frontend/.env.production.example)

## 单人执行脚本

- 前端静态构建脚本：[deploy/alicloud/export-frontend.ps1](C:/Users/Administrator/Desktop/JD/deploy/alicloud/export-frontend.ps1)
- 后端镜像构建脚本：[deploy/alicloud/build-backend-image.ps1](C:/Users/Administrator/Desktop/JD/deploy/alicloud/build-backend-image.ps1)

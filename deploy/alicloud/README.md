# 阿里云部署说明

本目录提供当前项目在阿里云上稳定部署的推荐落地方式：

- 前端：`frontend/` 静态构建产物部署到 OSS，并通过 CDN 提供访问
- 后端：`backend/` 构建 Docker 镜像，推送到 ACR，再由 SAE 拉取部署
- 数据库：阿里云 RDS PostgreSQL
- 文件：阿里云 OSS

## 1. 前端发布

在 `frontend/` 下执行：

```bash
npm ci
NEXT_PUBLIC_API_BASE_URL=https://api.example.com npm run build
```

产物会输出到：

```text
frontend/out/
```

将 `frontend/out/` 全量上传到 OSS 的前端站点 Bucket，再通过 CDN 绑定 `app.xxx.com`。

## 2. 后端镜像

在 `backend/` 下执行：

```bash
docker build -t resume-screening-api:latest .
```

推送到 ACR 后，在 SAE 中使用镜像部署，启动命令保持默认：

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

如果当前维护机器没有安装 Docker，可以把这一步放到有 Docker 的构建机、云效流水线、GitHub Actions 或其他 CI/CD 平台执行。运行平台不强绑定代码仓，只要最终能把镜像推到 ACR 即可。

## 3. 环境变量

后端参考：

```text
backend/.env.example
```

前端参考：

```text
frontend/.env.production.example
```

重点变量：

- `DATABASE_URL`
- `STORAGE_BACKEND=oss`
- `OSS_BUCKET`
- `OSS_ENDPOINT`
- `OSS_ACCESS_KEY_ID`
- `OSS_ACCESS_KEY_SECRET`
- `CORS_ORIGINS`
- `NEXT_PUBLIC_API_BASE_URL`

## 4. 初始化数据库

将后端连接到新的 PostgreSQL 后，执行：

```bash
cd backend
python scripts/init_db.py
```

这是当前版本的首轮初始化方式，适合新环境冷启动。

## 5. OSS 使用约定

- `jobs/`：保存 JD 原文件
- `resumes/`：保存候选人简历原文件
- 数据库存储对象 key 和文件元数据
- 不建议把 Bucket 设成公共读

## 6. 建议的域名拆分

- `app.xxx.com`：前端静态站点
- `api.xxx.com`：后端 API

## 7. 发布检查

发布前至少执行：

```bash
cd backend && pytest -q
cd frontend && npm run build
```

# 单人上线检查清单

这份清单是给“一个人负责维护和上线”的场景准备的。建议每次正式发布都完整走一遍。

## 1. 云资源准备

- 已创建 OSS Bucket，用于前端静态站点
- 已创建 OSS Bucket 或同一 Bucket 目录，用于 JD / 简历原文件
- 已创建 CDN 并准备绑定前端域名
- 已创建 ACR 镜像仓库
- 已创建 SAE 应用
- 已创建 RDS PostgreSQL
- 已完成域名解析规划：`app.xxx.com` / `api.xxx.com`
- 若使用中国内地正式域名，已完成备案

## 2. 本地配置确认

- 已确认用于发版的机器可以执行 Docker；如果当前机器没有 Docker，已准备其他构建机或 CI/CD
- 已准备后端生产环境变量，参考 [backend/.env.example](C:/Users/Administrator/Desktop/JD/backend/.env.example)
- 已确认 `DATABASE_URL` 指向 PostgreSQL
- 已确认 `STORAGE_BACKEND=oss`
- 已确认 `OSS_BUCKET`、`OSS_ENDPOINT`、`OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET` 都可用
- 已确认 `CORS_ORIGINS` 包含前端正式域名
- 已确认前端 `NEXT_PUBLIC_API_BASE_URL` 指向正式 API 域名

## 3. 发布前验证

- 在 `backend/` 下执行 `pytest -q`
- 在 `frontend/` 下执行 `npm run build`
- 本地至少走通一次完整流程：导入 JD、回答追问、冻结画像、上传简历、查看报告、人工改判

## 4. 前端发布

- 执行 [export-frontend.ps1](C:/Users/Administrator/Desktop/JD/deploy/alicloud/export-frontend.ps1)
- 确认 `frontend/out/` 已生成
- 将 `frontend/out/` 全量上传到 OSS 静态站点 Bucket
- 刷新 CDN 缓存
- 访问前端正式域名确认首页可打开

## 5. 后端发布

- 执行 [build-backend-image.ps1](C:/Users/Administrator/Desktop/JD/deploy/alicloud/build-backend-image.ps1)
- 将镜像推送到 ACR
- 在 SAE 中更新镜像版本
- 在 SAE 中配置环境变量
- 若是新库，执行 `python scripts/init_db.py`
- 确认 `/health` 返回正常

## 6. 上线后烟雾测试

- 从公网打开前端域名
- 成功拉取岗位历史
- 新建测试岗位
- 上传一份测试简历
- 成功生成评估报告
- 提交一次人工改判
- 检查 SAE 日志、RDS 连接、OSS 文件是否正常

## 7. 回滚准备

- 保留上一个前端静态版本
- 保留上一个后端镜像 tag
- 不在未经确认的情况下回滚数据库结构
- 如果本次只改应用不改库，优先回滚前端和 SAE 镜像

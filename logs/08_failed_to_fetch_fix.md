# 08 Failed To Fetch Fix

## 问题

- 公网测试版页面可打开，但前端提示 `Failed to fetch`。

## 原因

- 前端打包后的 API 默认回退地址仍然是 `http://localhost:8000`。
- 对外用户在自己的浏览器里访问时，请求会打到他们自己的本机 `localhost`，因此网络失败。

## 修复

- 修改 [frontend/lib/api.ts](C:/Users/Administrator/Desktop/JD/frontend/lib/api.ts)
- 默认 API 地址改为：
  - 若显式配置了 `NEXT_PUBLIC_API_BASE_URL`，则使用它
  - 否则浏览器端自动使用 `window.location.origin`
  - 仅服务端环境保留 `http://localhost:8000` 作为本地默认值

## 验证

- 重新执行 `npm run build`
- 确认打包产物中不再包含 `localhost:8000`

# 07 Public Test Tunnel Release

## 目标

- 在不依赖正式云平台账号的前提下，直接把当前系统挂到公网，供少量测试用户访问。

## 本轮执行结果

- 使用 `cloudflared` 快速隧道将后端单入口服务暴露到公网。
- 前端静态产物已改为由后端同域托管，避免浏览器跨域问题。
- 当前可访问测试地址：
  - `https://loud-thirty--rentals.trycloudflare.com/`

## 验证结果

- 首页访问：返回 `200`
- 健康检查：`/health` 返回 `200`
- 真实接口验证：`POST /jobs/import-jd` 返回 `200`

## 运行说明

- 这是临时公网测试版，不是正式云部署。
- 只要这台电脑不关机、相关后台进程不退出，外部用户就可以继续访问。
- 如果要长期稳定对外使用，下一步仍建议迁移到正式云平台。

## 相关运行文件

- [deploy/runtime/run-backend.cmd](C:/Users/Administrator/Desktop/JD/deploy/runtime/run-backend.cmd)
- [deploy/runtime/run-backend-tunnel.cmd](C:/Users/Administrator/Desktop/JD/deploy/runtime/run-backend-tunnel.cmd)
- [tools/cloudflared.exe](C:/Users/Administrator/Desktop/JD/tools/cloudflared.exe)

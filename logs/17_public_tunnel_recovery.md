# 模块日志 17：公网隧道恢复

## 时间
- 2026-03-27

## 背景
- 原测试地址 `loud-thirty--rentals.trycloudflare.com` 打开报 `Cloudflare Tunnel 1033`。
- 根因是 Cloudflare 临时 quick tunnel 已失效，并且当天重新申请 quick tunnel 时连续返回 `500 Internal Server Error`。

## 处理过程
1. 确认本地后端 `8010` 正常。
2. 重新尝试 Cloudflare quick tunnel，失败。
3. 增加备用公网隧道脚本：
   - `deploy/runtime/start-public-tunnel.ps1`
   - `deploy/runtime/start-public-tunnel-localtunnel.ps1`
   - `deploy/runtime/start-public-tunnel-pinggy.ps1`
   - `deploy/runtime/start-public-tunnel-localhostrun.ps1`
4. 最终切换到 `localhost.run` 方案，并成功拿到公网地址。
5. 更新 `deploy/runtime/run-backend-tunnel.cmd`，让它默认走 `localhost.run`，避免下次继续调用失效的 Cloudflare quick tunnel。

## 当前可用公网地址
- `https://6d072b50cdb21a.lhr.life`

## 验证结果
- `GET https://6d072b50cdb21a.lhr.life/health` 返回 `200 {"status":"ok"}`
- `GET https://6d072b50cdb21a.lhr.life/` 返回系统首页 HTML

## 说明
- 这是临时公网地址，进程退出后地址会失效。
- 当前公网隧道进程为 `ssh.exe`，用于 `localhost.run`。

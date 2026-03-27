# GitHub Pages 部署说明

## 目标
- 前端发布到 GitHub Pages
- 后端继续运行在你的电脑上
- 前端支持在页面里动态填写后端地址，避免后端地址变化时必须重新发版

## 已完成的项目改造
- 前端保持 `Next.js static export`
- GitHub Pages workflow 已加入：
  - `.github/workflows/pages.yml`
- Pages 子路径适配已加入：
  - `frontend/next.config.mjs`
- 运行时后端地址覆盖已加入：
  - `frontend/lib/api.ts`
  - `frontend/components/resume-screening-app.tsx`

## 你需要准备
1. 一个 GitHub 账号
2. 一台能持续开机的本地电脑来跑后端
3. 一个能把你本地后端暴露到公网的固定地址方案

## 推荐流程
1. 在项目根目录初始化 Git 仓库
```powershell
cd C:\Users\Administrator\Desktop\JD
git init -b main
git add .
git commit -m "Initial GitHub Pages deployment setup"
```

2. 登录 GitHub CLI
```powershell
gh auth login --web --git-protocol https
```

3. 创建一个 GitHub 仓库并推送
```powershell
gh repo create resume-screening-mvp --private --source . --remote origin --push
```

4. 打开仓库设置，把 Pages 来源切到 `GitHub Actions`

5. 在仓库的 `Settings -> Secrets and variables -> Actions -> Variables` 新增：
- `NEXT_PUBLIC_API_BASE_URL`
  - 如果你已经有固定后端公网地址，就填这个地址
  - 如果还没有固定后端地址，也可以先不填，后续在页面里手动设置

6. 每次 push 到 `main` 后，GitHub Actions 会自动发布前端

## 页面如何连接你的本地后端
- GitHub Pages 发布后，页面左侧会出现“后端地址”设置卡片
- 你可以直接填：
  - `http://127.0.0.1:8010` 仅限你自己这台电脑
  - 或者填你的本地后端公网地址，供其他人访问

## 重要限制
- 这个方案只能保证“前端地址稳定”
- 后端仍然在你的电脑上，所以：
  - 电脑关机后，系统不可用
  - 后端没启动时，系统不可用
  - 你的公网后端地址失效时，系统不可用

## 结论
- 这是一个可快速落地的过渡方案
- 如果要真正稳定给别人长期使用，后端仍然建议迁到云端

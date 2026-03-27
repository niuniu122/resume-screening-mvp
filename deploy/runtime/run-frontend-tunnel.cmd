@echo off
cd /d C:\Users\Administrator\Desktop\JD
C:\Users\Administrator\Desktop\JD\tools\cloudflared.exe tunnel --url http://localhost:3000 --no-autoupdate > C:\Users\Administrator\Desktop\JD\deploy\runtime\frontend-tunnel.out.log 2> C:\Users\Administrator\Desktop\JD\deploy\runtime\frontend-tunnel.err.log

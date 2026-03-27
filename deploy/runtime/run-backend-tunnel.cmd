@echo off
cd /d C:\Users\Administrator\Desktop\JD
powershell -ExecutionPolicy Bypass -File C:\Users\Administrator\Desktop\JD\deploy\runtime\start-public-tunnel-localhostrun.ps1 > C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-final-tunnel.out.log 2> C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-final-tunnel.err.log

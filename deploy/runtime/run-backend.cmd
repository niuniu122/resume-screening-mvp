@echo off
cd /d C:\Users\Administrator\Desktop\JD\backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8010 > C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-final.out.log 2> C:\Users\Administrator\Desktop\JD\deploy\runtime\backend-final.err.log

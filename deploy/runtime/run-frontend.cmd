@echo off
cd /d C:\Users\Administrator\Desktop\JD\frontend
npx --yes serve@14.2.4 -s out -l 3000 > C:\Users\Administrator\Desktop\JD\deploy\runtime\frontend.out.log 2> C:\Users\Administrator\Desktop\JD\deploy\runtime\frontend.err.log

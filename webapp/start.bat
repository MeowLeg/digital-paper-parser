@echo off
echo 正在启动电子报管理Web服务...
cd /d D:\Github\digital-paper-parser\webapp
call conda activate kimi
python app.py
pause

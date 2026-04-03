@echo off
chcp 65001 >nul
set PATH=%PATH%;D:\poppler-25.12.0\Library\bin
D:\miniconda3\envs\kimi\python.exe monitor_daemon.py

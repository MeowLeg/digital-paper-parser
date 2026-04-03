@echo off
cd /d D:\Github\digital-paper-parser

:: 检查今天是否已经解析过
python -c "
import json
from datetime import datetime
from pathlib import Path

today = datetime.now().strftime('%Y-%m-%d')
record_file = Path(f'parsed_record_{today}.json')

if record_file.exists():
    try:
        with open(record_file, 'r', encoding='utf-8') as f:
            records = json.load(f)
        if len(records) >= 8:
            print(f'[跳过] 今日已解析 {len(records)} 个版面，无需重复执行')
            exit(0)
    except Exception as e:
        print(f'[警告] 读取记录文件失败：{e}')

print('[执行] 启动解析任务...')
"

if errorlevel 1 exit 1

:: 执行解析任务
D:\miniconda3\envs\kimi\python.exe monitor_daemon.py

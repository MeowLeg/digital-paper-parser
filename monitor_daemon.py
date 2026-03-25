# encoding=utf-8
"""
电子报解析任务实时监控守护进程
- 随主任务一起启动
- 监控解析进度
- 卡住自动重启（最多3次）
- 超过3次发送飞书通知
"""

import os
import json
import subprocess
import sys
import time
import threading
import urllib.request
from datetime import datetime
from pathlib import Path
from ftplib import FTP

# 配置
MAX_RETRY = 3
CHECK_INTERVAL = 60  # 每60秒检查一次
STUCK_THRESHOLD = 600  # 180秒没有进度则认为卡住
STATE_FILE = Path("D:/Github/digital-paper-parser/monitor_state.json")
LOG_FILE = Path("D:/Github/digital-paper-parser/monitor.log")

# Feishu Webhook 配置 - 舟山日报电子报解析任务通知
# 如果环境变量未设置，使用默认密钥（请替换为实际的webhook密钥）
FEISHU_WEBHOOK_KEY = os.environ.get("FEISHU_ZSRB_WEBHOOK_KEY", "88560d5e-2943-4645-9112-30bc71806c4e")

# 全局变量
main_process = None
monitor_running = True
last_parsed_count = 0
last_progress_time = time.time()


def log(message):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def load_state():
    """加载监控状态"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log(f"加载状态文件失败: {e}")
    return {"date": "", "retry_count": 0, "notified": False}


def save_state(state):
    """保存监控状态"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存状态文件失败: {e}")


def get_today_parsed_count():
    """获取今天已解析的PDF数量"""
    today = datetime.now().strftime("%Y-%m-%d")
    record_file = Path("D:/Github/digital-paper-parser") / f"parsed_record_{today}.json"

    if record_file.exists():
        try:
            with open(record_file, "r", encoding="utf-8") as f:
                records = json.load(f)
                return len(records)
        except Exception as e:
            log(f"读取解析记录失败: {e}")
    return 0


def get_expected_pdf_count():
    """获取今天应该解析的PDF数量"""
    try:
        today_str = datetime.now().strftime("%Y%m%d")
        ftp = FTP()
        ftp.connect("47.105.52.63", 21, timeout=30)
        ftp.login("zsftp", "zsftp^Psa99Epaper")
        ftp.cwd("舟山日报")

        folders = ftp.nlst()
        today_folder = None
        for folder in folders:
            if today_str in folder.lower():
                today_folder = folder
                break

        if not today_folder:
            return 0

        ftp.cwd(today_folder)
        files = ftp.nlst()
        pdf_count = len([f for f in files if f.lower().endswith(".pdf")])
        ftp.quit()

        return pdf_count
    except Exception as e:
        log(f"获取FTP文件数量失败: {e}")
        return 8


def send_feishu_notification(parsed_count, expected_count, reason=""):
    """发送飞书通知"""
    if not FEISHU_WEBHOOK_KEY:
        log("未配置飞书Webhook密钥，跳过通知")
        return False

    try:
        webhook_url = (
            f"https://open.feishu.cn/open-apis/bot/v2/hook/{FEISHU_WEBHOOK_KEY}"
        )

        today = datetime.now().strftime("%Y-%m-%d")

        if parsed_count == 0:
            status_text = "今日电子报解析完全失败，无任何内容"
            status_emoji = "[失败]"
        elif parsed_count < expected_count:
            status_text = f"今日电子报解析部分失败，仅完成 {parsed_count}/{expected_count} 个版面"
            status_emoji = "[警告]"
        else:
            status_text = f"今日电子报解析完成，共 {parsed_count}/{expected_count} 个版面"
            status_emoji = "[成功]"

        reason_text = f"\n原因：{reason}" if reason else ""

        message_text = f"{status_emoji} [电子报解析任务通知]\n\n日期：{today}\n状态：{status_text}{reason_text}\n重试次数：{MAX_RETRY}次\n\n请检查任务状态，可能需要手动执行。"

        payload = {
            "msg_type": "text",
            "content": {
                "text": message_text
            },
        }

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            if result.get("code") == 0:
                log("飞书通知发送成功")
                return True
            else:
                log(f"飞书通知发送失败: {result}")
                return False
    except Exception as e:
        log(f"发送飞书通知时出错: {e}")
        return False


def run_main_task():
    """运行主任务"""
    global main_process

    log("启动电子报解析任务...")

    main_process = subprocess.Popen(
        [
            "D:\\miniconda3\\envs\\kimi\\python.exe",
            "main.py",
            datetime.now().strftime("%Y"),
            datetime.now().strftime("%m"),
            datetime.now().strftime("%d"),
        ],
        cwd="D:\\Github\\digital-paper-parser\\resource",
        stdout=open(
            "D:\\Github\\digital-paper-parser\\output.log", "a", encoding="utf-8"
        ),
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
    )

    log(f"主任务PID: {main_process.pid}")
    return main_process


def kill_main_task():
    """终止主任务"""
    global main_process

    if main_process and main_process.poll() is None:
        log(f"终止主任务PID: {main_process.pid}")
        try:
            main_process.terminate()
            time.sleep(2)
            if main_process.poll() is None:
                main_process.kill()
        except Exception as e:
            log(f"终止任务时出错: {e}")


def monitor_task():
    """监控任务线程"""
    global monitor_running, last_parsed_count, last_progress_time

    today = datetime.now().strftime("%Y-%m-%d")
    state = load_state()

    # 如果是新的一天，重置状态
    if state.get("date") != today:
        log("新的一天，重置监控状态")
        state = {"date": today, "retry_count": 0, "notified": False}
        save_state(state)

    expected_count = get_expected_pdf_count()
    log(f"今天预期解析 {expected_count} 个PDF")

    while monitor_running:
        # 检查主任务状态
        if main_process is None:
            log("主任务未启动")
            time.sleep(CHECK_INTERVAL)
            continue

        # 检查主任务是否已结束
        return_code = main_process.poll()
        if return_code is not None:
            log(f"主任务已结束，返回码: {return_code}")

            # 检查是否完成
            parsed_count = get_today_parsed_count()
            if parsed_count >= expected_count:
                log(f"任务完成！已解析 {parsed_count}/{expected_count} 个PDF")
                # 发送成功通知
                if not state.get("notified", False):
                    if send_feishu_notification(parsed_count, expected_count, "任务成功完成"):
                        state["notified"] = True
                        save_state(state)
                monitor_running = False
                break

            # 任务结束但未完成，尝试重启
            if state["retry_count"] < MAX_RETRY:
                state["retry_count"] += 1
                log(f"任务未完成，第 {state['retry_count']}/{MAX_RETRY} 次重启...")
                save_state(state)

                # 重启任务
                run_main_task()
                last_parsed_count = parsed_count
                last_progress_time = time.time()
            else:
                # 超过最大重试次数
                log(f"已达到最大重试次数 ({MAX_RETRY})")
                if not state.get("notified", False):
                    parsed_count = get_today_parsed_count()
                    reason = "任务执行失败（返回码异常）" if return_code != 0 else "任务未完成"
                    if send_feishu_notification(parsed_count, expected_count, reason):
                        state["notified"] = True
                        save_state(state)
                monitor_running = False
                break
        else:
            # 任务仍在运行，检查进度
            current_parsed = get_today_parsed_count()

            if current_parsed > last_parsed_count:
                log(f"进度更新: {current_parsed}/{expected_count} 个PDF")
                last_parsed_count = current_parsed
                last_progress_time = time.time()
            else:
                # 检查是否卡住
                elapsed = time.time() - last_progress_time
                if elapsed > STUCK_THRESHOLD:
                    log(f"任务卡住！{elapsed:.0f}秒没有进度")

                    # 终止当前任务
                    kill_main_task()

                    # 尝试重启
                    if state["retry_count"] < MAX_RETRY:
                        state["retry_count"] += 1
                        log(f"第 {state['retry_count']}/{MAX_RETRY} 次重启...")
                        save_state(state)

                        run_main_task()
                        last_progress_time = time.time()
                    else:
                        log(f"已达到最大重试次数 ({MAX_RETRY})")
                        if not state.get("notified", False):
                            if send_feishu_notification(current_parsed, expected_count, "任务卡住无响应"):
                                state["notified"] = True
                                save_state(state)
                        monitor_running = False
                        break

        time.sleep(CHECK_INTERVAL)


def main():
    """主函数"""
    global monitor_running

    log("=" * 50)
    log("电子报解析任务监控守护进程启动")

    # 启动主任务
    run_main_task()

    # 启动监控线程
    monitor_thread = threading.Thread(target=monitor_task)
    monitor_thread.daemon = True
    monitor_thread.start()

    # 等待主任务结束
    try:
        while monitor_running:
            if main_process and main_process.poll() is not None:
                # 主任务结束，但监控可能还在处理重启逻辑
                time.sleep(1)
            else:
                time.sleep(1)
    except KeyboardInterrupt:
        log("收到中断信号，正在停止...")
        monitor_running = False
        kill_main_task()

    log("监控守护进程结束")
    return 0


if __name__ == "__main__":
    sys.exit(main())

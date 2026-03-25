# Network Monitor for Heartbeat
# 由Heartbeat调用的网络监控脚本

import subprocess
import os
from datetime import datetime

LOG_FILE = r"D:\github\digital-paper-parser\network_monitor.log"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"[{timestamp}] {message}"
    print(log_message)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_message + "\n")

def check_network():
    """检查网络连接状态"""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "3000", "223.5.5.5"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="ignore"
        )
        return result.returncode == 0
    except Exception as e:
        log(f"检查网络时出错: {e}")
        return False

def disable_wifi():
    """禁用无线网卡"""
    try:
        subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", "disabled"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="ignore"
        )
        log("无线网卡已禁用")
        return True
    except Exception as e:
        log(f"禁用无线网卡失败: {e}")
        return False

def enable_wifi():
    """启用无线网卡"""
    try:
        subprocess.run(
            ["netsh", "interface", "set", "interface", "Wi-Fi", "enabled"],
            capture_output=True,
            text=True,
            encoding="gbk",
            errors="ignore"
        )
        log("无线网卡已启用")
        return True
    except Exception as e:
        log(f"启用无线网卡失败: {e}")
        return False

def restart_wifi():
    """重启无线网卡"""
    import time
    log("开始重启无线网卡...")
    disable_wifi()
    log("等待60秒...")
    time.sleep(60)
    enable_wifi()
    log("等待30秒让网络恢复...")
    time.sleep(30)
    
    # 检查是否恢复
    if check_network():
        log("网络已恢复")
        return True
    else:
        log("网络仍未恢复")
        return False

def run_network_check():
    """Heartbeat调用的主函数"""
    log("=" * 50)
    log("Heartbeat网络检查")
    log("=" * 50)
    
    log("检查网络连接...")
    
    if check_network():
        log("网络连接正常")
        return True
    else:
        log("网络连接断开！")
        restart_wifi()
        return False

if __name__ == "__main__":
    run_network_check()

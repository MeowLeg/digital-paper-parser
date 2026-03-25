# encoding=utf-8

from ftplib import FTP
from datetime import datetime
import os
from typing import Optional

def get_current_date(split_char: str = ""):
    return datetime.now().strftime(split_char.join(["%Y", "%m", "%d"]))

class FetchFtp:
    def __init__(self, ftp_host, ftp_port, ftp_user, ftp_pass, target_dir):
        # self.ftp_host = ftp_host
        # self.ftp_port = ftp_port
        # self.ftp_user = ftp_user
        # self.ftp_pass = ftp_pass
        self.target_dir = target_dir

        ftp = None

        # FTP 服务器配置
        # 1. 连接FTP服务器
        ftp = FTP()
        ftp.connect(ftp_host, ftp_port, timeout=30)  # 超时时间30秒
        print(f"成功连接到FTP服务器: {ftp_host}")

        # 2. 登录（匿名FTP可省略，直接用 ftp.login()）
        ftp.login(ftp_user, ftp_pass)
        print("登录成功！")

        # 3. 查看欢迎信息/当前状态
        print(f"服务器欢迎信息: {ftp.getwelcome()}")
        print(f"当前工作目录: {ftp.pwd()}")

        # 4. 列出当前目录下的文件/文件夹
        print("\n当前目录内容:")
        ftp.dir()  # 详细列表（类似Linux ls -l）
        # 或用 nlst() 获取简单文件名列表：print(ftp.nlst())

        # 5. 切换目录
        # target_dir = "/舟山日报"  # 替换为目标目录
        ftp.cwd(target_dir)
        print(f"\n切换到目录 {target_dir} 成功，当前目录: {ftp.pwd()}")

        self.ftp = ftp


    def ftp_job(self, date_str: str | None = None) -> Optional[str]:
        ftp = self.ftp

        try:
            curdate = date_str if date_str else get_current_date()
            for item in ftp.nlst():
                # print(item)
                if curdate in item:
                    print(f"找到日期 {curdate} 对应的文件: {item}")

                    # 7. 从FTP服务器下载文件
                    download_dir_name = item  # 服务器上的文件
                    local_save_dir = f"{self.target_dir}/{item}"  # 本地保存路径
                    self.download_ftp_folder(ftp, download_dir_name, local_save_dir)
                    print(f"文件 {download_dir_name} 下载成功，保存到 {local_save_dir}")
                    return f"{self.target_dir}/{download_dir_name}"

            # 9. 退出登录
            ftp.quit()
            print("已安全退出FTP连接")

        except Exception as e:
            print(f"FTP操作出错: {str(e)}")
        finally:
            if ftp and ftp.sock:
                ftp.close()  # 确保连接关闭

        return None

    def download_ftp_folder(self, ftp, remote_folder, local_folder):
        """
        递归下载FTP服务器上的文件夹到本地
        :param ftp: 已登录的FTP对象
        :param remote_folder: FTP服务器上的目标文件夹路径
        :param local_folder: 本地保存的文件夹路径
        """
        # 1. 创建本地文件夹（如果不存在）
        if not os.path.exists(local_folder):
            os.makedirs(local_folder)
            print(f"创建本地文件夹: {local_folder}")

        try:
            # 2. 切换到FTP的目标文件夹
            ftp.cwd(remote_folder)
            print(f"进入FTP文件夹: {remote_folder}")
        except Exception as e:
            print(f"无法访问FTP文件夹 {remote_folder}: {e}")
            return

        # 3. 获取当前FTP文件夹下的所有项（文件+文件夹）
        items = []
        ftp.dir('.', items.append)  # dir返回详细信息，用于区分文件/文件夹

        for item in items:
            # 解析dir返回的行，提取类型（文件夹/文件）和名称
            # 示例行：drwxr-xr-x  2 user group  4096 Jul 01 10:00 test_folder
            #        -rw-r--r--  1 user group  1234 Jul 01 10:01 test.txt
            parts = item.split()
            item_type = parts[0][0]  # 'd'=文件夹，'-'=文件
            item_name = ' '.join(parts[8:])  # 处理名称含空格的情况

            # 跳过.和..
            if item_name in ('.', '..'):
                continue

            remote_path = f"{remote_folder}/{item_name}"
            local_path = os.path.join(local_folder, item_name)

            if item_type == 'd':
                # 4. 如果是文件夹，递归下载
                download_ftp_folder(ftp, remote_path, local_path)
                # 递归返回后，切回上级目录
                ftp.cwd('..')
            else:
                # 5. 如果是文件，下载到本地
                try:
                    with open(local_path, 'wb') as f:
                        ftp.retrbinary(f"RETR {item_name}", f.write)
                    print(f"下载成功: {remote_path} -> {local_path}")
                except Exception as e:
                    print(f"下载失败 {remote_path}: {e}")


if __name__ == "__main__":
    # ftp_demo()
    ftp_host = "47.105.52.63"
    ftp_port = 21
    ftp_user = "zsftp"
    ftp_pass = "zsftp^Psa99Epaper"
    target_dir = "舟山日报"
    ftpObj = FetchFtp(ftp_host, ftp_port, ftp_user, ftp_pass, target_dir)
    success = ftpObj.ftp_job("20260209")
    print(f"FTP操作成功: {success}")

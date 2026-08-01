"""SSH 远程命令执行工具。

基于系统 ssh/scp 命令封装，依赖免密登录配置。
Rocky Linux 主机：192.168.3.100 (root)

使用示例：
    from tools.ssh_utils import ssh_exec, ssh_upload, ssh_download

    # 执行远程命令
    out, err, code = ssh_exec("hostname; date")

    # 在指定目录执行
    out, _, _ = ssh_exec("ls -la", cwd="/root/ai/ai_chatbot_django")

    # 上传文件
    ssh_upload("local_file.txt", "/root/remote_file.txt")

    # 下载文件
    ssh_download("/root/remote_file.txt", "local_file.txt")
"""

import logging
import shlex
import subprocess

logger = logging.getLogger(__name__)

# ==================== 默认主机配置 ====================

DEFAULT_HOST = "192.168.3.100"
DEFAULT_USER = "root"
DEFAULT_PORT = 22

# 远程项目路径
REMOTE_PROJECT_DIR = "/root/ai/ai_chatbot_django"


def ssh_exec(command, host=DEFAULT_HOST, user=DEFAULT_USER, port=DEFAULT_PORT,
             cwd=None, timeout=60, check=False):
    """通过 SSH 在远程主机执行命令。

    Args:
        command: 要执行的命令字符串
        host: 远程主机地址
        user: 登录用户
        port: SSH 端口
        cwd: 远程工作目录（执行前先 cd）
        timeout: 超时时间（秒）
        check: 为 True 时，非零退出码抛出 RuntimeError

    Returns:
        (stdout, stderr, returncode) 三元组
    """
    if cwd:
        command = f"cd {shlex.quote(cwd)} && {command}"

    ssh_cmd = [
        "ssh",
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=no",
        "-o", "LogLevel=ERROR",
        "-p", str(port),
        f"{user}@{host}",
        command,
    ]

    logger.info(f"SSH 执行: {command}")
    result = subprocess.run(
        ssh_cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        logger.warning(f"SSH 命令退出码 {result.returncode}: {result.stderr.strip()}")
        if check:
            raise RuntimeError(
                f"SSH 命令失败 (code={result.returncode}): {result.stderr.strip()}"
            )

    return result.stdout, result.stderr, result.returncode


def ssh_upload(local_path, remote_path, host=DEFAULT_HOST, user=DEFAULT_USER,
               port=DEFAULT_PORT, timeout=120):
    """通过 SCP 上传文件到远程主机。

    Args:
        local_path: 本地文件路径
        remote_path: 远程目标路径
        host: 远程主机地址
        user: 登录用户
        port: SSH 端口
        timeout: 超时时间（秒）

    Returns:
        returncode
    """
    scp_cmd = [
        "scp",
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=no",
        "-o", "LogLevel=ERROR",
        "-P", str(port),
        local_path,
        f"{user}@{host}:{remote_path}",
    ]

    logger.info(f"SCP 上传: {local_path} -> {remote_path}")
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=timeout)

    if result.returncode != 0:
        logger.error(f"SCP 上传失败: {result.stderr.strip()}")
    return result.returncode


def ssh_download(remote_path, local_path, host=DEFAULT_HOST, user=DEFAULT_USER,
                 port=DEFAULT_PORT, timeout=120):
    """通过 SCP 从远程主机下载文件。

    Args:
        remote_path: 远程文件路径
        local_path: 本地保存路径
        host: 远程主机地址
        user: 登录用户
        port: SSH 端口
        timeout: 超时时间（秒）

    Returns:
        returncode
    """
    scp_cmd = [
        "scp",
        "-o", "ConnectTimeout=10",
        "-o", "StrictHostKeyChecking=no",
        "-o", "LogLevel=ERROR",
        "-P", str(port),
        f"{user}@{host}:{remote_path}",
        local_path,
    ]

    logger.info(f"SCP 下载: {remote_path} -> {local_path}")
    result = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=timeout)

    if result.returncode != 0:
        logger.error(f"SCP 下载失败: {result.stderr.strip()}")
    return result.returncode


def ssh_check(host=DEFAULT_HOST, user=DEFAULT_USER, port=DEFAULT_PORT):
    """检查 SSH 连接是否正常。

    Returns:
        True 表示连接正常
    """
    out, _, code = ssh_exec("echo ok", host=host, user=user, port=port, timeout=10)
    return code == 0 and "ok" in out


def ssh_exec_in_project(command, **kwargs):
    """在远程项目目录 (/root/ai/ai_chatbot_django) 下执行命令。

    Args:
        command: 要执行的命令
        **kwargs: 传递给 ssh_exec 的额外参数

    Returns:
        (stdout, stderr, returncode) 三元组
    """
    return ssh_exec(command, cwd=REMOTE_PROJECT_DIR, **kwargs)


# ==================== 命令行入口 ====================

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if len(sys.argv) < 2:
        print("用法:")
        print("  python -m tools.ssh_utils <command>     # 执行远程命令")
        print("  python -m tools.ssh_utils --check       # 检查连接")
        print("  python -m tools.ssh_utils --upload <local> <remote>")
        print("  python -m tools.ssh_utils --download <remote> <local>")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--check":
        ok = ssh_check()
        print(f"SSH 连接: {'正常' if ok else '失败'}")
        sys.exit(0 if ok else 1)

    elif arg == "--upload":
        if len(sys.argv) < 4:
            print("用法: --upload <local_path> <remote_path>")
            sys.exit(1)
        code = ssh_upload(sys.argv[2], sys.argv[3])
        sys.exit(code)

    elif arg == "--download":
        if len(sys.argv) < 4:
            print("用法: --download <remote_path> <local_path>")
            sys.exit(1)
        code = ssh_download(sys.argv[2], sys.argv[3])
        sys.exit(code)

    else:
        # 把所有参数拼成一条命令执行
        cmd = " ".join(sys.argv[1:])
        out, err, code = ssh_exec(cmd)
        if out:
            print(out, end="")
        if err:
            print(err, end="", file=sys.stderr)
        sys.exit(code)

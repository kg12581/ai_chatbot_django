"""
硬编码密钥扫描引擎（Web 版）

纯 Python 实现，检测代码中的硬编码密钥/密码/token。
检测思路与规则设计参考 Gitleaks
(https://github.com/gitleaks/gitleaks, MIT License, Copyright (c) 2019 Zachary Rice)。

核心机制：
  1. 按行扫描源码文件，用正则规则匹配敏感内容；
  2. 对高熵规则计算 Shannon 熵，过滤低熵误报；
  3. 全局白名单过滤文档占位符（your_password 等）；
  4. 输出时对密钥脱敏（只保留首尾少量字符）。

用法：
  from tools.secret_scanner import scan_repository
  findings = scan_repository("/path/to/project")
"""

import logging
import math
import os
import re
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def shannon_entropy(text: str) -> float:
    """计算字符串的 Shannon 熵（比特/字符），用于识别随机生成的密钥。"""
    if not text:
        return 0.0
    text = text.strip()
    if not text:
        return 0.0
    freq = {}
    for ch in text:
        freq[ch] = freq.get(ch, 0) + 1
    length = len(text)
    entropy = 0.0
    for count in freq.values():
        p = count / length
        entropy -= p * math.log2(p)
    return entropy


def _redact(secret: str) -> str:
    """脱敏：保留前 4 位与后 4 位，中间用 * 代替。过短则整体打码。"""
    if len(secret) <= 8:
        return "*" * len(secret)
    return secret[:4] + "*" * min(len(secret) - 8, 12) + secret[-4:]


# ===== 检测规则 =====
# id: 规则唯一标识；name: 展示名；severity: 严重级别
# regex: 匹配模式；entropy: 若设置，匹配文本熵值需达到该阈值才算命中
RULES: List[Dict] = [
    {
        "id": "django-secret-key",
        "name": "Django SECRET_KEY",
        "severity": "high",
        "regex": re.compile(r"django-insecure-[A-Za-z0-9!@#$%^&*()_\-+=<>,.?/:;{}|\\~]+"),
    },
    {
        "id": "deepseek-api-key",
        "name": "DeepSeek API Key",
        "severity": "high",
        "regex": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
        "entropy": 3.5,
    },
    {
        "id": "openai-api-key",
        "name": "OpenAI API Key",
        "severity": "high",
        "regex": re.compile(r"\bsk-proj-[A-Za-z0-9_\-]{20,}\b"),
        "entropy": 3.5,
    },
    {
        "id": "github-token",
        "name": "GitHub Token",
        "severity": "high",
        "regex": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b"),
        "entropy": 3.5,
    },
    {
        "id": "aws-access-key",
        "name": "AWS Access Key",
        "severity": "high",
        "regex": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    },
    {
        "id": "google-api-key",
        "name": "Google API Key",
        "severity": "high",
        "regex": re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b"),
        "entropy": 3.0,
    },
    {
        "id": "private-key",
        "name": "私钥块",
        "severity": "critical",
        "regex": re.compile(r"-----BEGIN (RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    },
    {
        "id": "mysql-password",
        "name": "数据库密码",
        "severity": "high",
        "regex": re.compile(r"""(?i)["']?\bPASSWORD\b["']?\s*[:=]\s*(["'][^"']{8,}["'])"""),
        "secretGroup": 1,
        "entropy": 2.5,
    },
    {
        "id": "generic-secret",
        "name": "通用密钥/Token",
        "severity": "medium",
        "regex": re.compile(
            r"""(?i)(?:api[_-]?key|secret|token|access[_-]?key|auth[_-]?key)\s*[:=]\s*(["'][^"']{8,}["'])"""
        ),
        "secretGroup": 1,
        "entropy": 3.0,
    },
    {
        "id": "mysql-connection-string",
        "name": "MySQL 连接串",
        "severity": "high",
        "regex": re.compile(r"mysql://[A-Za-z0-9_.\-]+:[^@\s/]+@[A-Za-z0-9_.\-]+"),
    },
]


# 全局白名单：文档/示例占位符等
ALLOWLIST_PATTERNS = [
    re.compile(r"your_password", re.IGNORECASE),
    re.compile(r"changeme", re.IGNORECASE),
    re.compile(r"example\.com", re.IGNORECASE),
    re.compile(r"your_?(api|secret|token|key)", re.IGNORECASE),
    re.compile(r"your_auth_code", re.IGNORECASE),
    re.compile(r"your_email@qq\.com", re.IGNORECASE),
    re.compile(r"P@ssw0rd", re.IGNORECASE),
    # Django 模板变量（{{ csrf_token }} 等）不是硬编码密钥
    re.compile(r"\{\{[^}]*\}\}"),
]


def _is_allowed(text: str) -> bool:
    return any(p.search(text) for p in ALLOWLIST_PATTERNS)


# 需要跳过的目录 / 文件（不进入扫描范围）
SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    "media", "staticfiles", "data", "chroma_langchain_db", ".idea",
    ".vscode", ".agents", ".codex",
}
SKIP_FILES = {".env", ".env.local", ".env.production", ".env.development", ".DS_Store"}

# 二进制/资源文件后缀，跳过
SKIP_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".woff", ".woff2", ".ttf",
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin", ".class", ".jar",
    ".mp3", ".mp4", ".avi", ".mov", ".wav", ".db", ".sqlite3", ".lock",
}

MAX_FILE_BYTES = 1024 * 1024  # 单文件最大 1MB
CLONE_TIMEOUT_SECONDS = 180  # git clone 超时
CLONE_RETRIES = 2  # clone 失败重试次数


class ScanTimeoutError(Exception):
    """扫描超时/超过上限时抛出，由上层转成友好提示。"""


def iter_source_files(root: str):
    """遍历项目源码文件（跳过忽略目录/文件/二进制/超大文件）。"""
    for dirpath, dirnames, filenames in os.walk(root):
        # 就地修剪忽略目录（只跳过明确列出的目录，保留 .github 等含配置的目录）
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            if filename in SKIP_FILES:
                continue
            ext = os.path.splitext(filename)[1].lower()
            # 跳过二进制/资源文件与无扩展名文件（避免扫描产物与随机文件）
            if ext in SKIP_EXTENSIONS or ext == "":
                continue
            path = os.path.join(dirpath, filename)
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                yield path
            except OSError:
                continue


def scan_text(text: str, filename: str = "") -> List[Dict]:
    """
    扫描单份文本，返回命中列表。

    每条命中：
      {
        "rule_id", "rule_name", "severity", "file_path",
        "line_number", "line_text", "secret_preview", "entropy",
      }
    """
    findings: List[Dict] = []
    seen = set()

    for line_no, line in enumerate(text.splitlines(), 1):
        for rule in RULES:
            for match in rule["regex"].finditer(line):
                secret = match.group(rule.get("secretGroup", 0))
                if _is_allowed(secret):
                    continue

                entropy = shannon_entropy(secret)
                threshold = rule.get("entropy")
                if threshold is not None and entropy < threshold:
                    continue

                key = (rule["id"], line_no, match.start(), match.end())
                if key in seen:
                    continue
                seen.add(key)

                # 行内容同样脱敏后再入库，避免密钥明文落库
                redacted_line = line.replace(secret, _redact(secret))
                findings.append({
                    "rule_id": rule["id"],
                    "rule_name": rule["name"],
                    "severity": rule["severity"],
                    "file_path": filename,
                    "line_number": line_no,
                    "line_text": redacted_line.strip()[:200],
                    "secret_preview": _redact(secret),
                    "entropy": round(entropy, 2),
                })
    return findings


def scan_repository(root: str, max_seconds: Optional[float] = None, max_files: Optional[int] = None) -> Dict:
    """
    扫描整个项目目录。

    返回：
      {
        "files_scanned": int,
        "findings": [...],
      }
    """
    findings: List[Dict] = []
    files_scanned = 0
    start_time = time.monotonic()

    for path in iter_source_files(root):
        if max_files is not None and files_scanned >= max_files:
            raise ScanTimeoutError(f"扫描文件数超过上限（{max_files} 个），已中止")
        if max_seconds is not None and time.monotonic() - start_time > max_seconds:
            raise ScanTimeoutError(f"扫描超过 {int(max_seconds)} 秒，已中止（仓库过大）")

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError as e:
            logger.debug(f"跳过文件 {path}: {e}")
            continue

        files_scanned += 1
        rel_path = os.path.relpath(path, root)
        file_findings = scan_text(text, rel_path)
        for finding in file_findings:
            finding["file_path"] = rel_path
        findings.extend(file_findings)

    findings.sort(key=lambda x: (x["file_path"], x["line_number"]))
    return {
        "files_scanned": files_scanned,
        "findings": findings,
    }


# 禁止扫描的系统目录（防止误扫整个磁盘）
FORBIDDEN_SCAN_ROOTS = [
    "/", "/System", "/Library", "/etc", "/usr", "/var", "/opt",
    "/private", "/bin", "/sbin", "/dev", "/proc", "/Volumes", "/Applications",
]


def scan_target(
    target: str = "",
    base_dir: str = "",
    max_seconds: Optional[float] = None,
    max_files: Optional[int] = None,
) -> Dict:
    """
    按用户指定目标执行扫描：
      - 留空：扫描 base_dir（当前项目）
      - Git 仓库 URL（http/https）：临时克隆到系统临时目录，扫描后自动清理
      - 本地绝对路径：直接扫描该目录

    返回结构与 scan_repository 相同。
    """
    import shutil
    import subprocess
    import tempfile
    from urllib.parse import urlparse

    stripped = (target or "").strip()

    # 1. 默认：扫描当前项目
    if not stripped:
        if not base_dir:
            raise ValueError("缺少扫描目标")
        return scan_repository(base_dir, max_seconds=max_seconds, max_files=max_files)

    # 2. Git 仓库 URL
    parsed = urlparse(stripped)
    if parsed.scheme in ("http", "https"):
        if not parsed.netloc or "@" in parsed.netloc or parsed.path.count("/") < 2:
            raise ValueError("Git 仓库 URL 无效（示例：https://github.com/user/repo.git）")
        tmp_dir = tempfile.mkdtemp(prefix="secret-scan-")
        try:
            # 使用 HTTP/1.1 + 连接超时 + 低速保护，避免网络抖动导致失败；失败自动重试
            clone_cmd = [
                "git", "-c", "http.version=HTTP/1.1",
                "-c", "http.connectTimeout=20",
                "-c", "http.lowSpeedLimit=1000",
                "-c", "http.lowSpeedTime=60",
                "clone", "--depth", "1", "--single-branch", "--quiet", stripped, tmp_dir,
            ]
            last_detail = "未知错误"
            for attempt in range(CLONE_RETRIES + 1):
                try:
                    proc = subprocess.run(
                        clone_cmd, capture_output=True, timeout=CLONE_TIMEOUT_SECONDS,
                    )
                except subprocess.TimeoutExpired:
                    raise ScanTimeoutError(
                        f"克隆 Git 仓库超过 {CLONE_TIMEOUT_SECONDS} 秒，已中止（网络慢或仓库过大）"
                    )
                if proc.returncode == 0:
                    break
                last_detail = (proc.stderr or b"").decode("utf-8", errors="ignore").strip() or last_detail
                if attempt < CLONE_RETRIES:
                    time.sleep(2 * (attempt + 1))
            else:
                raise ValueError(
                    f"克隆 Git 仓库失败（已重试 {CLONE_RETRIES} 次）: {last_detail[-300:]}"
                )
            return scan_repository(tmp_dir, max_seconds=max_seconds, max_files=max_files)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # 3. 本地目录
    abs_path = os.path.abspath(os.path.expanduser(stripped))
    for root in FORBIDDEN_SCAN_ROOTS:
        if abs_path == root or abs_path.startswith(root + os.sep):
            raise ValueError(f"禁止扫描系统目录: {root}")
    if not os.path.isdir(abs_path):
        raise ValueError(f"目录不存在: {abs_path}")
    return scan_repository(abs_path, max_seconds=max_seconds, max_files=max_files)

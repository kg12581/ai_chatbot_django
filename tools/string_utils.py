"""
字符串处理工具
"""

import re
import html


def truncate(text: str, max_len: int = 100, suffix: str = "...") -> str:
    """截断字符串到指定长度"""
    if not text or len(text) <= max_len:
        return text or ""
    return text[:max_len] + suffix


def strip_html(text: str) -> str:
    """移除 HTML 标签"""
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text)


def sanitize(text: str) -> str:
    """HTML 转义，防止 XSS"""
    if not text:
        return ""
    return html.escape(text, quote=True)


def highlight(text: str, keyword: str) -> str:
    """
    高亮关键词（返回 HTML，关键词包裹 <mark> 标签）
    """
    if not text or not keyword:
        return text or ""
    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    return pattern.sub(lambda m: f'<mark class="bg-amber-400/30 text-amber-300 rounded px-0.5">{m.group()}</mark>', text)


def slugify(text: str) -> str:
    """将文本转为 URL 安全的 slug"""
    if not text:
        return ""
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


def mask_email(email: str) -> str:
    """邮箱脱敏：abc***@example.com"""
    if not email or "@" not in email:
        return email or ""
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        return f"{'*' * len(name)}@{domain}"
    return f"{name[0]}{'*' * (len(name) - 2)}{name[-1]}@{domain}"


def mask_phone(phone: str) -> str:
    """手机号脱敏：138****5678"""
    if not phone or len(phone) < 7:
        return phone or ""
    return f"{phone[:3]}{'*' * (len(phone) - 7)}{phone[-4:]}"


def count_words(text: str) -> int:
    """统计字数（中英文混合）"""
    if not text:
        return 0
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    english = len(re.findall(r"[a-zA-Z]+", text))
    return chinese + english

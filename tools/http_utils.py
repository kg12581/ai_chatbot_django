"""
HTTP 请求工具封装
"""

import logging
import time
from typing import Dict, Optional, Any

import requests

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15
DEFAULT_RETRY = 3
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
}


def get(
    url: str,
    *,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retry: int = DEFAULT_RETRY,
    **kwargs,
) -> requests.Response:
    """
    带重试的 GET 请求

    Args:
        url:       请求地址
        headers:   自定义请求头
        params:    查询参数
        timeout:   超时秒数
        retry:     重试次数
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    last_error = None

    for attempt in range(1, retry + 1):
        try:
            resp = requests.get(
                url,
                headers=merged_headers,
                params=params,
                timeout=timeout,
                **kwargs,
            )
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_error = e
            logger.warning(f"GET {url} 第 {attempt}/{retry} 次失败: {e}")
            if attempt < retry:
                time.sleep(attempt * 1.5)

    raise last_error


def get_json(
    url: str,
    *,
    headers: Optional[Dict] = None,
    params: Optional[Dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retry: int = DEFAULT_RETRY,
    default: Any = None,
) -> Dict:
    """
    GET 请求并返回 JSON，失败时返回 default
    """
    try:
        resp = get(url, headers=headers, params=params, timeout=timeout, retry=retry)
        return resp.json()
    except (requests.RequestException, ValueError) as e:
        logger.error(f"GET JSON {url} 失败: {e}")
        return default if default is not None else {}


def post_json(
    url: str,
    *,
    json_data: Optional[Dict] = None,
    headers: Optional[Dict] = None,
    timeout: int = DEFAULT_TIMEOUT,
    retry: int = DEFAULT_RETRY,
) -> Dict:
    """
    POST JSON 请求并返回 JSON 响应
    """
    merged_headers = {**DEFAULT_HEADERS, "Content-Type": "application/json", **(headers or {})}
    last_error = None

    for attempt in range(1, retry + 1):
        try:
            resp = requests.post(
                url,
                json=json_data,
                headers=merged_headers,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            logger.warning(f"POST {url} 第 {attempt}/{retry} 次失败: {e}")
            if attempt < retry:
                time.sleep(attempt * 1.5)

    raise last_error


def download(
    url: str,
    filepath: str,
    *,
    headers: Optional[Dict] = None,
    timeout: int = 60,
    chunk_size: int = 8192,
) -> str:
    """
    下载文件到本地

    Returns:
        保存的文件路径
    """
    merged_headers = {**DEFAULT_HEADERS, **(headers or {})}
    resp = requests.get(url, headers=merged_headers, timeout=timeout, stream=True)
    resp.raise_for_status()

    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            f.write(chunk)

    logger.info(f"下载完成: {url} -> {filepath}")
    return filepath

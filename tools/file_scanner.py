"""
目录文件名扫描工具

扫描指定目录下的所有文件名（支持递归），可按关键词/扩展名/深度过滤，
并输出文件统计（总数、目录数、按扩展名分布）。

用法：
  # 作为模块调用
  from tools.file_scanner import scan_file_names
  result = scan_file_names("/path/to/dir", pattern="test", extensions=[".py"])

  # 命令行
  python -m tools.file_scanner /path/to/dir
  python -m tools.file_scanner /path/to/dir --pattern test --ext .py,.md --max-depth 3
"""

import argparse
import logging
import os
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# 默认跳过目录（噪音目录）
DEFAULT_SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build",
    "media", "staticfiles", "data", "chroma_langchain_db", ".idea", ".vscode",
    ".agents", ".codex",
}


def scan_file_names(
    directory: str,
    *,
    recursive: bool = True,
    pattern: Optional[str] = None,
    extensions: Optional[List[str]] = None,
    max_depth: Optional[int] = None,
    skip_dirs: Optional[Set[str]] = None,
    max_files: Optional[int] = None,
) -> Dict:
    """
    扫描指定目录下的文件名。

    Args:
        directory: 要扫描的目录（绝对路径或相对路径）
        recursive: 是否递归子目录，默认 True
        pattern: 文件名包含关键词（大小写不敏感），None 表示不过滤
        extensions: 扩展名过滤，如 [".py", ".md"]，None 表示全部
        max_depth: 最大扫描深度（顶层为 1），None 表示不限制
        skip_dirs: 要跳过的目录名集合，None 使用默认噪音目录
        max_files: 最多返回文件数，超过则截断并标记 truncated

    Returns:
        {
            "directory": 实际扫描的目录绝对路径,
            "total_files": 目录内文件总数（过滤前）,
            "total_dirs": 目录总数,
            "matched_files": 过滤后返回的文件数,
            "truncated": 是否因 max_files 截断,
            "by_extension": {扩展名: 数量},
            "files": [相对路径, ...]（已排序）,
        }

    Raises:
        ValueError: directory 不存在或不是目录
    """
    directory = os.path.abspath(os.path.expanduser(directory))
    if not os.path.isdir(directory):
        raise ValueError(f"目录不存在或不是目录: {directory}")

    skip = DEFAULT_SKIP_DIRS if skip_dirs is None else set(skip_dirs)
    ext_set = _normalize_extensions(extensions)
    keyword = pattern.lower() if pattern else None

    files: List[str] = []
    total_files = 0
    total_dirs = 0
    truncated = False

    if not recursive:
        # 只扫顶层
        try:
            entries = sorted(os.listdir(directory))
        except OSError as e:
            raise ValueError(f"无法读取目录 {directory}: {e}")
        for name in entries:
            path = os.path.join(directory, name)
            if os.path.isdir(path):
                total_dirs += 1
                continue
            total_files += 1
            if _match(name, keyword, ext_set):
                files.append(name)
    else:
        base_depth = directory.rstrip(os.sep).count(os.sep) + 1
        for dirpath, dirnames, filenames in os.walk(directory):
            # 计算当前深度（顶层为 1）
            depth = dirpath.rstrip(os.sep).count(os.sep) - base_depth + 2
            if max_depth is not None and depth > max_depth:
                dirnames[:] = []
                continue

            dirnames[:] = sorted(d for d in dirnames if d not in skip)
            total_dirs += len(dirnames)

            for name in sorted(filenames):
                total_files += 1
                rel = os.path.relpath(os.path.join(dirpath, name), directory)
                if _match(name, keyword, ext_set):
                    files.append(rel)
                    if max_files is not None and len(files) >= max_files:
                        truncated = True
                        return _build_result(
                            directory, total_files, total_dirs, files, truncated, ext_set
                        )

    return _build_result(directory, total_files, total_dirs, files, truncated, ext_set)


def find_file_names(directory: str, keyword: str, **kwargs) -> List[str]:
    """
    便捷方法：在目录中查找文件名包含指定关键词的文件。

    Args:
        directory: 目标目录
        keyword: 文件名关键词（大小写不敏感）
        **kwargs: 透传给 scan_file_names 的其他参数

    Returns:
        匹配文件的相对路径列表
    """
    result = scan_file_names(directory, pattern=keyword, **kwargs)
    return result["files"]


def _match(filename: str, keyword: Optional[str], ext_set: Optional[Set[str]]) -> bool:
    """判断文件名是否同时满足关键词与扩展名过滤。"""
    if keyword and keyword not in filename.lower():
        return False
    if ext_set:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ext_set:
            return False
    return True


def _normalize_extensions(extensions: Optional[List[str]]) -> Optional[Set[str]]:
    """规范化扩展名：统一小写并确保以点开头。"""
    if not extensions:
        return None
    normalized = set()
    for ext in extensions:
        ext = ext.strip().lower()
        if not ext:
            continue
        if not ext.startswith("."):
            ext = "." + ext
        normalized.add(ext)
    return normalized or None


def _build_result(
    directory: str,
    total_files: int,
    total_dirs: int,
    files: List[str],
    truncated: bool,
    ext_set: Optional[Set[str]],
) -> Dict:
    """汇总扫描结果。"""
    by_ext: Dict[str, int] = {}
    for rel in files:
        ext = os.path.splitext(rel)[1].lower() or "(无扩展名)"
        by_ext[ext] = by_ext.get(ext, 0) + 1
    by_ext = dict(sorted(by_ext.items(), key=lambda x: -x[1]))
    return {
        "directory": directory,
        "total_files": total_files,
        "total_dirs": total_dirs,
        "matched_files": len(files),
        "truncated": truncated,
        "by_extension": by_ext,
        "files": files,
    }


def _print_result(result: Dict) -> None:
    """命令行打印扫描结果。"""
    print(f"扫描目录: {result['directory']}")
    print(f"文件总数: {result['total_files']}   目录数: {result['total_dirs']}   命中: {result['matched_files']}")
    if result["truncated"]:
        print("（结果超出 max_files 上限，已截断）")
    if result["by_extension"]:
        print("\n扩展名分布:")
        for ext, count in result["by_extension"].items():
            print(f"  {ext:<14} {count}")
    print(f"\n命中文件 ({result['matched_files']}):")
    for rel in result["files"]:
        print(f"  {rel}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="file_scanner",
        description="扫描指定目录下的文件名",
    )
    parser.add_argument("directory", help="要扫描的目录")
    parser.add_argument("--pattern", default=None, help="文件名包含的关键词（不区分大小写）")
    parser.add_argument("--ext", default=None, help="扩展名过滤，逗号分隔，如 .py,.md 或 py,md")
    parser.add_argument("--max-depth", type=int, default=None, help="最大扫描深度（顶层为 1）")
    parser.add_argument("--no-recursive", action="store_true", help="只扫描顶层目录")
    parser.add_argument("--skip-dirs", default=None, help="额外跳过的目录名，逗号分隔")
    parser.add_argument("--max-files", type=int, default=None, help="最多返回文件数")
    args = parser.parse_args(argv)

    extensions = [e.strip() for e in args.ext.split(",")] if args.ext else None
    extra_skips = {s.strip() for s in args.skip_dirs.split(",") if s.strip()} if args.skip_dirs else None
    skip_dirs = DEFAULT_SKIP_DIRS | extra_skips if extra_skips else None

    try:
        result = scan_file_names(
            args.directory,
            recursive=not args.no_recursive,
            pattern=args.pattern,
            extensions=extensions,
            max_depth=args.max_depth,
            skip_dirs=skip_dirs,
            max_files=args.max_files,
        )
    except ValueError as e:
        parser.error(str(e))
        return 2

    _print_result(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

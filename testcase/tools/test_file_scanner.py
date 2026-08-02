"""目录文件名扫描工具测试"""

import pytest

from tools.file_scanner import find_file_names, scan_file_names


def test_scan_basic(tmp_path):
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "b.txt").write_text("", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.py").write_text("", encoding="utf-8")
    result = scan_file_names(str(tmp_path))
    assert result["total_files"] == 3
    assert len(result["files"]) == 3


def test_pattern_and_extension(tmp_path):
    (tmp_path / "test_a.py").write_text("", encoding="utf-8")
    (tmp_path / "app.py").write_text("", encoding="utf-8")
    (tmp_path / "test.md").write_text("", encoding="utf-8")
    result = scan_file_names(str(tmp_path), pattern="test", extensions=[".py"])
    assert result["files"] == ["test_a.py"]


def test_no_recursive(tmp_path):
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.py").write_text("", encoding="utf-8")
    result = scan_file_names(str(tmp_path), recursive=False)
    assert result["files"] == ["a.py"]


def test_max_depth(tmp_path):
    (tmp_path / "a.py").write_text("", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "b.py").write_text("", encoding="utf-8")
    result = scan_file_names(str(tmp_path), max_depth=1)
    assert result["files"] == ["a.py"]


def test_truncation(tmp_path):
    for i in range(5):
        (tmp_path / f"f{i}.txt").write_text("", encoding="utf-8")
    result = scan_file_names(str(tmp_path), max_files=3)
    assert result["truncated"] is True
    assert len(result["files"]) == 3


def test_missing_dir():
    with pytest.raises(ValueError):
        scan_file_names("/no/such/dir")


def test_find_file_names(tmp_path):
    (tmp_path / "hello_world.py").write_text("", encoding="utf-8")
    assert find_file_names(str(tmp_path), "world") == ["hello_world.py"]

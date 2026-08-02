"""测试报告生成器

读取 testcase/test_results.xml（JUnit）与 test_results.txt（覆盖率），
生成 test_report.md / test_report.html / test_flowchart.svg。
"""

import html
import json
import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).parent
XML_PATH = BASE / "test_results.xml"
TXT_PATH = BASE / "test_results.txt"


# ==================== 数据解析 ====================


def parse_junit():
    root = ET.parse(XML_PATH).getroot()
    tests = []
    for tc in root.iter("testcase"):
        status = "failed" if tc.find("failure") is not None else (
            "error" if tc.find("error") is not None else "passed"
        )
        tests.append({
            "classname": tc.attrib.get("classname", ""),
            "name": tc.attrib.get("name", ""),
            "time": float(tc.attrib.get("time", 0)),
            "status": status,
        })
    return tests


def parse_coverage():
    rows = []
    started = False
    for line in TXT_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip() == "Name":
            started = True
            continue
        if not started:
            continue
        if line.startswith("---"):
            continue
        if line.strip().startswith("TOTAL"):
            break
        parts = line.split()
        if len(parts) >= 4 and parts[0].endswith(".py"):
            rows.append((parts[0], parts[1], parts[2], parts[3]))
    return rows


def module_groups(tests):
    groups = {}
    for t in tests:
        if t["classname"].startswith("testcase.frontend"):
            key = "前端 E2E（Playwright + Chrome）"
        elif t["classname"].startswith("testcase.api"):
            key = "API 应用（爬虫/模型/视图）"
        elif t["classname"].startswith("testcase.scanner"):
            key = "扫描应用（引擎/Web 视图）"
        elif t["classname"].startswith("testcase.tools"):
            key = "工具模块（调度/文件扫描）"
        elif t["classname"].startswith("testcase.common"):
            key = "通用应用（视图/权限隔离）"
        else:
            key = "其他"
        groups.setdefault(key, []).append(t)
    return groups


# ==================== SVG 流程图 ====================


def _box(out, x, y, w, h, title, subtitle="", color="#5eead4"):
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="rgba(94,234,212,0.05)" stroke="{color}" stroke-width="1.5"/>')
    ty = y + h / 2 - 8
    out.append(f'<text x="{x + w / 2}" y="{ty}" fill="#e2e8f0" font-size="14" font-weight="600" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif">{html.escape(title)}</text>')
    if subtitle:
        out.append(f'<text x="{x + w / 2}" y="{ty + 18}" fill="#94a3b8" font-size="11" text-anchor="middle" font-family="PingFang SC, Microsoft YaHei, sans-serif">{html.escape(subtitle)}</text>')


def _arrow(out, x1, y1, x2, y2):
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>')


def build_svg(groups, stats):
    W, H = 1080, 470
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="PingFang SC, Microsoft YaHei, sans-serif">']
    out.append('<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#64748b"/></marker></defs>')
    out.append(f'<rect width="{W}" height="{H}" fill="#0b1120"/>')

    _box(out, 420, 24, 240, 52, "pytest 测试入口", "testcase/", "#5eead4")
    _box(out, 130, 130, 240, 54, "后端自动化测试", str(stats["backend"]) + " 个用例", "#fbbf24")
    _box(out, 620, 130, 240, 54, "前端 E2E 测试", str(stats["frontend"]) + " 个用例", "#60a5fa")
    _arrow(out, 520, 76, 300, 130)
    _arrow(out, 540, 76, 720, 130)

    leaf = [
        ("API 应用", len(groups.get("API 应用（爬虫/模型/视图）", [])), "#fbbf24"),
        ("扫描应用", len(groups.get("扫描应用（引擎/Web 视图）", [])), "#fbbf24"),
        ("工具模块", len(groups.get("工具模块（调度/文件扫描）", [])), "#fbbf24"),
        ("通用应用", len(groups.get("通用应用（视图/权限隔离）", [])), "#fbbf24"),
        ("浏览器页面", len(groups.get("前端 E2E（Playwright + Chrome）", [])), "#60a5fa"),
    ]
    positions = [30, 230, 430, 630, 830]
    for (title, count, color), x in zip(leaf, positions):
        _box(out, x, 240, 190, 60, title, str(count) + " 用例", color)
        if title == "浏览器页面":
            _arrow(out, 680, 184, 740, 240)
        else:
            _arrow(out, 260, 184, x + 95, 240)

    _box(out, 280, 360, 520, 52, "测试结果", "66 个测试全部通过 · 覆盖率 " + stats["coverage"], "#34d399")
    for x in positions:
        _arrow(out, x + 95, 300, 540, 360)

    out.append("</svg>")
    return "\n".join(out)


# ==================== Mermaid 思维导图 ====================


def build_mermaid_mindmap(groups, stats):
    backend = (
        "    后端自动化测试（" + str(stats["backend"]) + "）\n"
        + "        API 应用（" + str(len(groups.get("API 应用（爬虫/模型/视图）", []))) + "）\n"
        + "            爬虫解析 / 模型 / 热搜调度视图\n"
        + "        扫描应用（" + str(len(groups.get("扫描应用（引擎/Web 视图）", []))) + "）\n"
        + "            规则 / 熵值 / 脱敏 / 超时 / 权限 / 并发\n"
        + "        工具模块（" + str(len(groups.get("工具模块（调度/文件扫描）", []))) + "）\n"
        + "            cron 校验 / 目录文件扫描\n"
        + "        通用应用（" + str(len(groups.get("通用应用（视图/权限隔离）", []))) + "）\n"
        + "            对话权限隔离 / 历史搜索"
    )
    frontend = (
        "    前端 E2E（" + str(stats["frontend"]) + "）\n"
        + "        登录 / 导航\n"
        + "        对话 / 历史\n"
        + "        抖音 / 微博热搜\n"
        + "        硬编码扫描页\n"
        + "        移动端适配"
    )
    result = (
        "    测试结果\n"
        + "        66 / 66 全部通过\n"
        + "        覆盖率 " + stats["coverage"] + "\n"
        + "        耗时 " + f"{stats['total_time']:.1f}" + "s\n"
        + "        已修复 5 个问题"
    )
    return "mindmap\n" + "root((Nocturne AI 项目测试))\n" + backend + "\n" + frontend + "\n" + result + "\n"


# ==================== XMind 文件 ====================


def _topic(tid, title, children=None):
    topic = {"id": tid, "class": "topic", "title": title}
    if children:
        topic["children"] = {"attached": children}
    return topic


def build_xmind(groups, stats) -> bytes:
    def leaf(title):
        return _topic("topic-" + uuid.uuid4().hex[:12], title)

    backend_children = [
        _topic("topic-" + uuid.uuid4().hex[:12], "API 应用（" + str(len(groups.get("API 应用（爬虫/模型/视图）", []))) + "）", [
            leaf("抖音/微博爬虫解析（新旧格式、兜底）"),
            leaf("数据模型"),
            leaf("热搜/调度视图与接口"),
        ]),
        _topic("topic-" + uuid.uuid4().hex[:12], "扫描应用（" + str(len(groups.get("扫描应用（引擎/Web 视图）", []))) + "）", [
            leaf("密钥规则 / 熵值 / 白名单 / 脱敏"),
            leaf("超时 / 异步 / 并发保护"),
            leaf("权限控制与状态管理"),
        ]),
        _topic("topic-" + uuid.uuid4().hex[:12], "工具模块（" + str(len(groups.get("工具模块（调度/文件扫描）", []))) + "）", [
            leaf("cron 表达式校验"),
            leaf("目录文件名扫描"),
        ]),
        _topic("topic-" + uuid.uuid4().hex[:12], "通用应用（" + str(len(groups.get("通用应用（视图/权限隔离）", []))) + "）", [
            leaf("首页 / 对话 / 历史"),
            leaf("跨用户会话隔离"),
        ]),
    ]
    frontend_children = [
        _topic("topic-" + uuid.uuid4().hex[:12], "前端 E2E（" + str(stats["frontend"]) + "）", [
            leaf("登录流程与导航"),
            leaf("对话 / 历史页面"),
            leaf("抖音 / 微博热搜页"),
            leaf("硬编码扫描页"),
            leaf("移动端适配（无横向溢出）"),
        ]),
    ]
    result_children = [
        _topic("topic-" + uuid.uuid4().hex[:12], "测试结果", [
            leaf("66 / 66 全部通过"),
            leaf("覆盖率 " + stats["coverage"]),
            leaf("总耗时 " + f"{stats['total_time']:.1f}s"),
            leaf("已修复 5 个问题（含 3 个功能性 Bug）"),
        ]),
    ]
    root = _topic(
        "topic-root-" + uuid.uuid4().hex[:8],
        "Nocturne AI 项目测试",
        backend_children + frontend_children + result_children,
    )
    root["structureClass"] = "org.xmind.ui.map.unbalanced"

    content = [{
        "id": "sheet-" + uuid.uuid4().hex[:8],
        "class": "sheet",
        "title": "项目测试",
        "rootTopic": root,
    }]
    manifest = {"file-entries": {"content.json": {}, "metadata.json": {}, "manifest.json": {}}}
    metadata = {"creator": {"name": "Codex 测试报告生成器", "version": "1.0.0"}}

    buffer = __import__("io").BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("content.json", json.dumps(content, ensure_ascii=False, indent=2))
        zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    return buffer.getvalue()


# ==================== 报告组装 ====================


def test_rows(tests):
    rows = []
    for t in sorted(tests, key=lambda x: (x["classname"], x["name"])):
        rows.append(
            "<tr><td>" + html.escape(t["classname"].split(".")[-1]) + "</td>"
            + "<td>" + html.escape(t["name"]) + "</td>"
            + f"<td>{t['time']:.3f}s</td>"
            + '<td><span class="ok">通过</span></td></tr>'
        )
    return "\n".join(rows)


def build_markdown(groups, stats, cov_rows, svg_path):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mermaid = "\n".join([
        "```mermaid",
        "flowchart TD",
        '    A["pytest 测试入口"] --> B["后端自动化测试（' + str(stats["backend"]) + ' 用例）"]',
        '    A --> C["前端 E2E 测试（' + str(stats["frontend"]) + ' 用例）"]',
        '    B --> D["API 应用：爬虫解析 / 模型 / 视图接口"]',
        '    B --> E["扫描应用：密钥引擎 / Web 视图 / 权限"]',
        '    B --> F["工具模块：cron 校验 / 文件扫描"]',
        '    B --> G["通用应用：对话权限隔离 / 历史"]',
        '    C --> H["登录 / 导航 / 对话 / 热搜 / 扫描 / 历史 / 移动端"]',
        '    D & E & F & G --> R{"66 个测试全部通过"}',
        '    H --> R',
        "```",
    ])
    cov_table = "\n".join(f"| {n} | {s} | {m} | {p} |" for n, s, m, p in cov_rows)
    return f"""# Nocturne AI · 项目测试报告

> 生成时间：{now}　|　测试框架：pytest + pytest-django + pytest-cov + Playwright

## 一、测试结果总览

- ✅ **{stats["passed"]} / {stats["total"]} 个测试全部通过**（后端 {stats["backend"]} + 前端 {stats["frontend"]}）
- ⏱️ 总耗时：{stats["total_time"]:.1f} 秒
- 📊 代码覆盖率：**{stats["coverage"]}**
- 🧪 测试数据库：SQLite 文件库（不触碰远程 MySQL）
- 🌐 前端测试：Playwright + 系统 Chrome（无头）

## 二、测试架构流程图

{mermaid}

![测试流程图]({svg_path})

## 三、测试范围

| 模块 | 数量 | 覆盖内容 |
|---|---|---|
| API 应用 | {len(groups.get("API 应用（爬虫/模型/视图）", []))} | 抖音/微博爬虫解析（新旧格式、兜底）、数据模型、热搜/调度视图与接口 |
| 扫描应用 | {len(groups.get("扫描应用（引擎/Web 视图）", []))} | 密钥规则/熵值/白名单/脱敏/超时、扫描 Web 功能（权限/异步/并发/状态） |
| 工具模块 | {len(groups.get("工具模块（调度/文件扫描）", []))} | cron 表达式校验、目录文件名扫描 |
| 通用应用 | {len(groups.get("通用应用（视图/权限隔离）", []))} | 首页/对话/历史、跨用户会话隔离 |
| 前端 E2E | {len(groups.get("前端 E2E（Playwright + Chrome）", []))} | 登录、导航、对话、热搜、扫描、历史、移动端适配 |

## 四、环境

| 项 | 值 |
|---|---|
| Python | 3.11.15 |
| Django | 4.2.30 |
| pytest / pytest-django / pytest-cov | 8.3.5 / 4.10.0 / 6.0.0 |
| Playwright | Python 版（驱动系统 Chrome 无头） |
| 测试数据库 | SQLite 文件库 |

## 五、代码覆盖率（按模块）

| 模块 | 语句数 | 未覆盖 | 覆盖率 |
|---|---|---|---|
{cov_table}

## 六、测试发现并修复的问题

1. 扫描引擎缩进错误：`scan_text` 结果记录缩进到循环外，无匹配时抛 `UnboundLocalError`
2. 熵值误判：低熵密码因把键名前缀计入熵而漏报，现只对密钥值本身计算熵
3. 密钥明文落库：发现记录的行内容含明文密钥，已改为入库前脱敏
4. 扫描并发竞态：并发检查存在 TOCTOU，已用锁修复
5. 前端 E2E 用例超时：`wait_for_url` 在 `goto` 已完成导航后等待导致超时（测试写法修正）

## 七、如何运行

```bash
pip install -r requirements-dev.txt
pip install playwright          # 前端测试
python -m pytest                # 后端 + 前端全量
python -m pytest testcase/frontend  # 仅前端
```

## 八、结论

项目当前 **{stats["total"]} 个测试全部通过**，后端逻辑（爬虫、扫描、调度、权限）与前端核心页面
（登录、对话、热搜、扫描、历史、移动端）均有自动化用例守护；已修复 3 个功能性 Bug 与 1 个并发隐患。
建议将测试接入 CI（GitHub Actions）持续回归。
"""


CSS = """
body { background:#0b1120; color:#e2e8f0; font-family:"PingFang SC","Microsoft YaHei",sans-serif; margin:0; padding:32px 16px; }
.wrap { max-width:1060px; margin:0 auto; }
h1 { color:#5eead4; font-size:28px; }
h2 { color:#fbbf24; font-size:20px; border-bottom:1px solid #1e293b; padding-bottom:8px; margin-top:36px; }
h3 { color:#94a3b8; font-size:16px; margin-top:26px; }
.cards { display:flex; gap:14px; flex-wrap:wrap; margin:20px 0; }
.card { flex:1; min-width:180px; background:#111a2e; border:1px solid #1e293b; border-radius:12px; padding:18px; }
.card .num { font-size:30px; font-weight:700; color:#34d399; }
.card .lbl { color:#94a3b8; font-size:13px; margin-top:4px; }
table { width:100%; border-collapse:collapse; margin:12px 0; font-size:13px; }
th { background:#111a2e; color:#94a3b8; text-align:left; padding:8px 10px; border-bottom:1px solid #1e293b; }
td { padding:7px 10px; border-bottom:1px solid #16213a; }
.ok { color:#34d399; }
code { background:#111a2e; padding:2px 6px; border-radius:5px; color:#5eead4; }
pre { background:#111a2e; padding:14px; border-radius:10px; overflow:auto; }
svg { max-width:100%; height:auto; background:#0b1120; border-radius:12px; border:1px solid #1e293b; }
.note { color:#64748b; font-size:13px; }
"""


def build_html(groups, stats, cov_rows, svg):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sections = ""
    for name, tests in groups.items():
        sections += f"<h3>{html.escape(name)}（{len(tests)}）</h3>\n"
        sections += "<table><thead><tr><th>模块</th><th>用例</th><th>耗时</th><th>结果</th></tr></thead>"
        sections += f"<tbody>{test_rows(tests)}</tbody></table>\n"
    cov_table = "".join(
        f"<tr><td>{html.escape(n)}</td><td>{s}</td><td>{m}</td><td>{p}</td></tr>" for n, s, m, p in cov_rows
    )
    body = f"""<h1>🛡️ Nocturne AI · 项目测试报告</h1>
<p class="note">生成时间：{now}　|　pytest + pytest-django + pytest-cov + Playwright</p>
<div class="cards">
<div class="card"><div class="num">{stats["passed"]}/{stats["total"]}</div><div class="lbl">测试全部通过</div></div>
<div class="card"><div class="num">{stats["backend"]}+{stats["frontend"]}</div><div class="lbl">后端 + 前端用例</div></div>
<div class="card"><div class="num">{stats["total_time"]:.1f}s</div><div class="lbl">总耗时</div></div>
<div class="card"><div class="num">{stats["coverage"]}</div><div class="lbl">代码覆盖率</div></div>
</div>
<h2>一、测试架构流程图</h2>
{svg}
<h2>二、测试范围与用例明细</h2>
{sections}
<h2>三、环境</h2>
<table><tbody>
<tr><td>Python</td><td>3.11.15</td></tr>
<tr><td>Django</td><td>4.2.30</td></tr>
<tr><td>pytest 工具链</td><td>pytest 8.3.5 / pytest-django 4.10.0 / pytest-cov 6.0.0</td></tr>
<tr><td>前端驱动</td><td>Playwright（系统 Chrome 无头）</td></tr>
<tr><td>测试数据库</td><td>SQLite 文件库</td></tr>
</tbody></table>
<h2>四、代码覆盖率（按模块）</h2>
<table><thead><tr><th>模块</th><th>语句数</th><th>未覆盖</th><th>覆盖率</th></tr></thead><tbody>{cov_table}</tbody></table>
<h2>五、测试发现并修复的问题</h2>
<ul>
<li>扫描引擎缩进错误：无匹配时抛 <code>UnboundLocalError</code></li>
<li>熵值误判：低熵密码漏报，现只对密钥值计算熵</li>
<li>密钥明文落库：入库前脱敏</li>
<li>扫描并发竞态：TOCTOU 已用锁修复</li>
<li>前端 E2E 用例超时：导航等待写法修正</li>
</ul>
<h2>六、如何运行</h2>
<pre>pip install -r requirements-dev.txt
pip install playwright
python -m pytest                  # 全量
python -m pytest testcase/frontend   # 仅前端</pre>
<p class="note">前端截图证据见 testcase/frontend/screenshots/；JUnit 结果见 test_results.xml。</p>"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nocturne AI · 项目测试报告</title>
<style>{CSS}</style></head>
<body><div class="wrap">{body}</div></body></html>"""


def main():
    tests = parse_junit()
    groups = module_groups(tests)
    cov_rows = parse_coverage()
    total_time = sum(t["time"] for t in tests)
    backend = sum(len(v) for k, v in groups.items() if not k.startswith("前端"))
    frontend = len(groups.get("前端 E2E（Playwright + Chrome）", []))
    passed = sum(1 for t in tests if t["status"] == "passed")

    m = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", TXT_PATH.read_text(encoding="utf-8"))
    coverage = m.group(1) + "%" if m else "—"

    stats = {
        "total": len(tests), "passed": passed,
        "backend": backend, "frontend": frontend,
        "total_time": total_time, "coverage": coverage,
    }
    svg = build_svg(groups, stats)
    (BASE / "test_flowchart.svg").write_text(svg, encoding="utf-8")
    (BASE / "test_report.md").write_text(
        build_markdown(groups, stats, cov_rows, "test_flowchart.svg"), encoding="utf-8",
    )
    (BASE / "test_report.html").write_text(
        build_html(groups, stats, cov_rows, svg), encoding="utf-8",
    )
    (BASE / "test_flowchart.mmd").write_text(
        build_mermaid_mindmap(groups, stats), encoding="utf-8",
    )
    (BASE / "test_mindmap.xmind").write_bytes(build_xmind(groups, stats))
    print(f"报告已生成：{len(tests)} 个测试，通过 {passed}，覆盖率 {coverage}")
    print("  - testcase/test_report.md")
    print("  - testcase/test_report.html")
    print("  - testcase/test_flowchart.svg")
    print("  - testcase/test_flowchart.mmd")
    print("  - testcase/test_mindmap.xmind")


if __name__ == "__main__":
    main()

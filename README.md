# Nocturne AI · 暗夜智能对话平台

基于 **Django 4.2** + **LangGraph** + **DeepSeek API** 构建的 AI 智能对话平台，
集成 **RAG 检索增强**、**SSH 远程运维**、**抖音/微博热搜爬虫**、**定时调度（重启自动恢复）**、
**硬编码密钥扫描（自研 Web 功能）**、**埋点统计**、**完整自动化测试** 等功能模块。
采用优雅的暗色主题（Nocturne）设计，响应式布局，移动端适配。

---

## ✨ 功能特性

### 🤖 AI 智能对话
- DeepSeek 大模型（OpenAI 兼容接口），默认中文回复
- LangGraph Agent 架构：RAG 检索 + SSH 远程命令双工具
- 多轮对话管理（数据库会话/消息存储）、SSE 流式输出
- RAG 本地向量库（ChromaDB + HuggingFace Embeddings）
- SSH 远程运维（危险命令黑名单、30 秒超时）

### 🔥 热搜榜单
- **抖音热搜**：实时爬取、入库、榜单展示、一键刷新
- **微博热搜**：实时爬取、入库、榜单展示、一键刷新
- 每条话题带跳转链接（抖音搜索 / 微博搜索，接口无链接时自动构造）
- 管理命令：`python manage.py crawl_douyin` / `crawl_weibo`

### ⏰ 定时调度系统
- APScheduler 后台调度 + Cron 表达式（5 段，Asia/Shanghai）
- 任务配置持久化到数据库，**服务重启后自动恢复已启用任务**
- 前端可视化配置：启动/停止、快捷预设、下次执行预览、执行统计

### 🛡️ 硬编码密钥扫描（自研 Web 功能）
- 纯 Python 扫描引擎（正则 + Shannon 熵 + 白名单 + 脱敏）
- 支持扫描：当前项目 / 本地目录 / Git 仓库 URL（临时克隆自动清理）
- 后台异步执行、超时控制（默认 300 秒 / 5 万文件）、并发保护
- 结果入库、页面管理（标记误报/已修复）、Admin 后台
- 管理命令：`python manage.py scan_secrets [目标]`
- 另附 Gitleaks 配置与脚本：`scripts/scan_secrets.sh`

### 📊 埋点统计
- 自建轻量埋点：页面 PV 自动上报、`data-track` 按钮点击自动绑定
- 上报接口 `POST /api/track/`（登录/匿名均支持，参数清洗）
- 统计页 `/analytics/`：PV/UV、事件排行、热门页面、最近事件
- 导出命令：`python manage.py export_analytics`

### ✅ 自动化测试
- pytest + pytest-django + pytest-cov（后端）+ Playwright（前端 E2E）
- 73 个测试用例：爬虫解析、模型、视图、扫描引擎、调度、权限隔离、浏览器页面
- 测试报告生成：Markdown / HTML / SVG 流程图 / Mermaid / XMind
- 一键执行：`bash ~/.codex/skills/test-execution/scripts/run_tests.sh`

### 🔐 用户认证与权限
- Django Auth 登录/登出/密码重置（邮件链接）
- 普通用户只能看自己的对话记录，管理员可看全部
- Admin 后台注册全部数据模型

---

## 🏗️ 技术栈

| 类别 | 技术 |
|---|---|
| 后端 | Django 4.2.30 |
| AI | LangGraph + LangChain Core + DeepSeek Chat |
| 向量库 | ChromaDB + sentence-transformers |
| 数据库 | MySQL 8.0+（PyMySQL） |
| 调度 | APScheduler 3.x（BackgroundScheduler + CronTrigger） |
| 测试 | pytest / pytest-django / pytest-cov / Playwright |
| 前端 | Tailwind CSS + Lucide Icons + 原生 JavaScript |
| Python | 3.11+ |

---

## 📁 项目结构

```
ai_chatbot_django/
├── core/                       # Django 项目配置（settings/urls，配置全部走 .env）
├── common/                     # AI 对话应用（会话/消息/上传/MCP/Skill）
├── api/                        # 热搜 + 调度应用（抖音/微博爬虫、定时任务）
├── scanner/                    # 硬编码扫描应用（自研引擎 + Web 页面）
├── analytics/                  # 埋点统计应用（事件模型/上报/统计页）
├── tools/                      # 工具集（ssh/调度/日期/字符串/http/db/格式化/密钥扫描/文件扫描）
├── templates/                  # HTML 模板（含 scanner、analytics 页面）
├── static/                     # 静态资源（css / js：chat.js、tracking.js）
├── testcase/                   # 测试套件 + 测试报告 + 报告生成器
├── docs/                       # 功能实现说明文档
├── scripts/                    # Gitleaks 扫描脚本等
├── requirements.txt            # 运行依赖
├── requirements-dev.txt        # 测试依赖
├── pytest.ini                  # pytest 配置
└── README.md
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- MySQL 8.0+（数据库 `ai_chatbot`）
- DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）

### 2. 安装依赖

```bash
pip install -r requirements.txt
# 测试工具链（可选）
pip install -r requirements-dev.txt
pip install playwright
```

### 3. 配置环境变量（项目根目录 `.env`）

```bash
# AI
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx

# Django 密钥（必填，未配置时本地随机生成）
DJANGO_SECRET_KEY=xxxxxxxx

# 数据库
DB_NAME=ai_chatbot
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

### 4. 数据库迁移与账号

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. 启动服务

```bash
python manage.py runserver 0.0.0.0:8000
```

### 6. 主要页面

| 页面 | URL | 说明 |
|---|---|---|
| 登录 | `/accounts/login/` | 用户认证 |
| AI 对话 | `/chat/` | 智能对话 |
| 历史记录 | `/history/` | 对话历史 |
| 抖音热搜 | `/api/douyin/hot/` | 榜单 + 调度配置 |
| 微博热搜 | `/api/weibo/hot/` | 榜单 + 调度配置 |
| 硬编码扫描 | `/scanner/` | 密钥扫描 |
| 数据统计 | `/analytics/` | 埋点统计 |
| Admin | `/admin/` | 数据管理 |

---

## 🔌 API 接口

### 热搜与调度（需登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/douyin/crawl/` | 触发抖音爬取 |
| POST | `/api/weibo/crawl/` | 触发微博爬取 |
| GET | `/api/scheduler/status/` | 抖音任务状态 |
| POST | `/api/scheduler/start/` | 启动抖音任务（`{"cron_expr": "0 * * * *"}`） |
| POST | `/api/scheduler/stop/` | 停止抖音任务 |
| GET/POST | `/api/weibo/scheduler/status\|start\|stop/` | 微博任务对应接口 |

### 硬编码扫描（需登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/scanner/` | 扫描页面 |
| POST | `/scanner/run/` | 启动扫描（`{"target": "路径或 Git URL", "max_seconds": 300, "max_files": 50000}`） |
| GET | `/scanner/status/<id>/` | 查询扫描进度 |
| POST | `/scanner/findings/<id>/status/` | 标记误报/已修复 |

### 埋点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/track/` | 事件上报（`{"event_type","event_name","page_url","payload"}`） |
| GET | `/analytics/` | 统计页（需登录） |

### AI 对话（需登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/chat/api/chat/stream/` | SSE 流式对话 |
| POST | `/chat/api/upload/` | 文件上传 |
| DELETE | `/chat/api/conversations/<id>/` | 删除会话 |

---

## ⚙️ 定时调度

- 标准 5 段 cron（分 时 日 月 周），时区 Asia/Shanghai
- 配置持久化到 `SchedulerConfig`；**服务重启后自动恢复已启用任务**
  （见 `docs/定时任务重启恢复实现说明.md`）
- 多 worker / 多机部署建议改用外部调度触发管理命令，避免重复执行

常用预设：`*/30 * * * *`（每30分钟）、`0 * * * *`（每小时）、`0 0 * * *`（每天凌晨）

---

## 🧪 测试

```bash
# 全量测试（后端 + 前端 E2E）
python -m pytest

# 只跑某模块
python -m pytest testcase/api
python -m pytest testcase/frontend

# 生成测试报告（md/html/svg/mermaid/xmind）
python testcase/generate_report.py
```

- 测试使用 SQLite 文件库，不依赖远程 MySQL
- 前端测试用 Playwright 驱动系统 Chrome，截图存于 `testcase/frontend/screenshots/`
- 测试代码位于 `testcase/`，按应用分子目录

---

## 🛠️ 常用命令

```bash
python manage.py migrate                  # 数据库迁移
python manage.py runserver 0.0.0.0:8000   # 启动服务
python manage.py crawl_douyin             # 爬取抖音热搜
python manage.py crawl_weibo              # 爬取微博热搜
python manage.py scan_secrets [目标]      # 硬编码扫描
python manage.py export_analytics         # 导出埋点数据 CSV
python manage.py check --deploy           # 部署安全检查
```

---

## 🔐 安全提示

1. `SECRET_KEY`、数据库密码等敏感配置一律放 `.env`，不要提交到代码
2. 生产环境设置 `DEBUG=False`、收紧 `ALLOWED_HOSTS`、启用 HTTPS
3. 定期用 `python manage.py scan_secrets` 或 `/scanner/` 扫描硬编码密钥
4. 已在 Git 历史泄露的密钥必须轮换
5. 测试代码中的假密钥不要写成完整格式（GitHub 推送保护会拦截）

---

## 🐛 常见问题

**Q: 服务重启后定时任务还在吗？**
A: 在。已启用任务会自动恢复（详见 `docs/定时任务重启恢复实现说明.md`）。

**Q: 扫描大仓库超时？**
A: 可在 `/scanner/run/` 请求中传 `max_seconds`（≤600）、`max_files`（≤200000），
或扫描子目录。

**Q: 微博热搜点不了？**
A: 已修复：接口返回的 `url` 是纯文本时自动构造微博搜索链接；
历史坏数据也已回填。

**Q: ChromaDB 报 sqlite3 版本错误？**
A: 安装 `pysqlite3-binary` 并在 `core/__init__.py` 中替换 sqlite3 模块。

**Q: 爬虫无数据？**
A: 接口失败时使用模拟数据兜底；如需真实数据可替换带签名/登录态的请求实现。

---

## 📜 License

MIT

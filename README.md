# Nocturne AI · 暗夜智能对话平台

基于 **Django 4.2** + **LangGraph** + **DeepSeek API** 构建的 AI 智能对话平台，集成 **RAG 检索增强生成**、**抖音热搜爬虫**、**定时调度系统** 等功能模块。采用优雅的暗色主题（Nocturne）设计，响应式布局，开箱即用。

---

## ✨ 功能特性

### 🤖 AI 智能对话
- **DeepSeek 大模型**：使用 DeepSeek API（OpenAI 兼容接口），默认中文回复
- **LangGraph Agent 架构**：支持工具调用（RAG 检索），具备可观测的执行状态图
- **多轮对话管理**：基于数据库的会话/消息存储，支持历史记录回溯与继续对话
- **流式输出**：SSE 流式响应，打字机效果即时展示 AI 回复
- **RAG 检索增强**：基于 ChromaDB + HuggingFace Embeddings 的本地向量库，根据上下文精准回答

### 🔥 抖音热搜榜
- **实时爬取**：一键抓取抖音平台当前热搜话题（排名、标题、热度、标签）
- **数据入库**：MySQL 持久化存储，支持多批次历史数据回溯
- **榜单展示**：Top 3 高亮，热度图标 + 标签分级（热/新/沸）
- **管理命令**：`python manage.py crawl_douyin` 支持脚本/CI 调用

### ⏰ 定时调度系统
- **APScheduler 后台调度**：基于 MemoryJobStore 的单例调度管理器
- **Cron 表达式**：支持标准 5 段 cron（分 时 日 月 周），内置中文语义描述
- **前端可视化配置**：启动/停止按钮、快捷预设（每30分钟/每小时/每6小时/每天凌晨）、下次执行预览、执行统计
- **任务持久化**：SchedulerConfig 模型记录启用状态、cron、上次执行时间/结果/总次数

### 🧰 Python 工具类集合
`tools/` 目录下提供通用工具模块：

| 模块 | 说明 |
|---|---|
| `date_utils.py` | 日期时间处理（格式化、时区转换、相对时间、常用快捷方法） |
| `string_utils.py` | 字符串处理（截断、脱敏、URL 解析、正则辅助、emoji 过滤） |
| `http_utils.py` | HTTP 请求封装（requests 基础封装、重试、超时、统一异常） |
| `db_utils.py` | 数据库辅助（批量插入、分页查询、事务上下文） |
| `format_utils.py` | 数据格式化（字节/数字/JSON/货币格式化，表格渲染） |
| `scheduler.py` | 定时调度管理器（APScheduler 封装，单例模式，Cron 支持） |

### 🎨 UI / UX
- **Nocturne 暗色主题**：薄荷绿 + 琥珀金渐变，玻璃拟态 + 细颗粒网格背景
- **响应式设计**：移动端 / 平板 / 桌面端自适应
- **页面路由**：首页 `/`、对话 `/chat/`、历史 `/history/`、抖音热搜 `/api/douyin/hot/`
- **动效**：淡入上升、渐显、脉冲、浮动、闪烁、滑动进入等微交互

---

## 🏗️ 技术栈

| 类别 | 技术 |
|---|---|
| 后端框架 | Django 4.2.30 |
| AI 框架 | LangGraph 0.6.11 + LangChain Core 0.3.86 |
| 大语言模型 | DeepSeek Chat (deepseek-chat) |
| 向量数据库 | ChromaDB 1.5.9 |
| Embedding | sentence-transformers/all-MiniLM-L6-v2 |
| 关系数据库 | MySQL 8.0+ (PyMySQL) |
| 任务调度 | APScheduler 3.x (BackgroundScheduler + CronTrigger) |
| 前端 | Tailwind CSS + Lucide Icons + 原生 JavaScript |
| Python 版本 | 3.11+ |

---

## 📁 项目结构

```
ai_chatbot_django/
├── api/                          # 抖音热搜 + 调度 应用
│   ├── management/commands/
│   │   └── crawl_douyin.py       # Django 管理命令：爬取热搜
│   ├── migrations/
│   │   ├── 0001_initial.py       # DouyinHotSearch 模型
│   │   └── 0002_schedulerconfig.py  # SchedulerConfig 模型
│   ├── crawler.py                # 抖音热搜爬虫核心
│   ├── models.py                 # 数据库模型
│   ├── urls.py                   # API 路由
│   └── views.py                  # 视图 + 调度管理 API
├── djangoapp/                    # AI 对话 应用
│   ├── migrations/0001_initial.py  # Conversation / Message 模型
│   ├── models.py                 # 会话、消息 ORM
│   └── views.py                  # 聊天页面、流式 API、历史记录
├── djangoproj/                   # Django 项目配置
│   ├── settings.py               # 数据库 / 应用 / 静态文件 配置
│   ├── urls.py                   # 全局 URL 路由
│   ├── asgi.py / wsgi.py         # ASGI / WSGI 入口
│   └── __init__.py
├── static/                       # 静态资源
│   ├── css/styles.css            # Nocturne 主题自定义样式
│   └── js/chat.js                # 聊天页交互 + 流式渲染
├── templates/                    # HTML 模板
│   ├── base.html                 # 全局基模板（导航 / 页脚 / CDN）
│   ├── home.html                 # 首页：功能介绍 + 快速开始
│   ├── chat.html                 # 对话页：消息列表 + 流式输入
│   ├── history.html              # 历史记录页：会话列表
│   └── api/
│       └── douyin_hot.html       # 抖音热搜 + 调度配置面板
├── tools/                        # Python 工具类集合
│   ├── __init__.py
│   ├── date_utils.py
│   ├── string_utils.py
│   ├── http_utils.py
│   ├── db_utils.py
│   ├── format_utils.py
│   └── scheduler.py              # 定时调度管理器
├── chatbot.py                    # LangGraph Agent 定义（LLM + RAG 工具）
├── manage.py                     # Django 入口脚本
├── requirements.txt              # 依赖清单
├── .env                          # 环境变量（DEEPSEEK_API_KEY 等，需自行创建）
├── .gitignore
└── README.md
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- MySQL 8.0+（已创建数据库 `ai_chatbot`）
- 可用的 DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）

### 2. 安装依赖

```bash
cd ai_chatbot_django
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```bash
# DeepSeek API（必填）
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx

# 可选：MySQL 连接（如与 settings.py 中不同）
# DB_HOST=127.0.0.1
# DB_PORT=3306
# DB_NAME=ai_chatbot
# DB_USER=root
# DB_PASSWORD=your_password
```

### 4. 配置数据库连接

编辑 [djangoproj/settings.py](file:///Users/kgt/code/rocky/ai/ai_chatbot_django/djangoproj/settings.py#L74-L89) 中的 `DATABASES` 配置，确保指向你的 MySQL 实例：

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "ai_chatbot",
        "USER": "root",
        "PASSWORD": "Admin@123456",
        "HOST": "192.168.3.100",
        "PORT": "3306",
        "OPTIONS": {"charset": "utf8mb4"},
    }
}
```

### 5. 数据库迁移

```bash
python manage.py migrate
```

将自动创建以下数据表：

| 表名 | 说明 |
|---|---|
| `conversation` | AI 对话会话 |
| `message` | 对话消息（用户 / 助手） |
| `douyin_hot_search` | 抖音热搜数据 |
| `scheduler_config` | 定时任务配置 |

### 6. 启动开发服务器

```bash
python manage.py runserver 0.0.0.0:8000
```

访问以下地址验证功能：

| 页面 | URL |
|---|---|
| 首页 | http://localhost:8000/ |
| AI 对话 | http://localhost:8000/chat/ |
| 历史记录 | http://localhost:8000/history/ |
| 抖音热搜 + 调度 | http://localhost:8000/api/douyin/hot/ |

---

## 🔌 API 接口

### AI 对话

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/chatbot/` | 单次问答（兼容旧版，返回 JSON） |
| POST | `/chat/api/chat/stream/` | 流式对话（SSE，推荐），body: `{ "conv_id": 1, "message": "..." }` |
| GET  | `/chat/api/conversations/<int:conv_id>/` | 获取指定会话的全部消息 |

### 抖音热搜

| 方法 | 路径 | 说明 |
|---|---|---|
| GET  | `/api/douyin/hot/` | 热搜榜 HTML 页面 |
| POST | `/api/douyin/crawl/` | 触发爬取，返回 `{ success, total, batch_time, items }` |
| CLI  | `python manage.py crawl_douyin` | 命令行触发爬取 |

### 定时调度

| 方法 | 路径 | 说明 |
|---|---|---|
| GET  | `/api/scheduler/status/` | 获取调度器与任务状态 |
| POST | `/api/scheduler/start/` | 启动任务，body: `{ "cron_expr": "0 * * * *" }` |
| POST | `/api/scheduler/stop/` | 停止并移除任务 |

Cron 表达式格式（5 段，Asia/Shanghai 时区）：

```
┌───────────── 分钟 (0 - 59)
│ ┌─────────── 小时 (0 - 23)
│ │ ┌───────── 日   (1 - 31)
│ │ │ ┌─────── 月   (1 - 12)
│ │ │ │ ┌───── 星期 (0 - 6, 0=周日)
│ │ │ │ │
* * * * *
```

常用预设：

- `*/30 * * * *` — 每 30 分钟
- `0 * * * *` — 每小时整点
- `0 */6 * * *` — 每 6 小时
- `0 0 * * *` — 每天凌晨 0 点

---

## ⚙️ 模块详解

### LangGraph Agent（chatbot.py）

基于 `StateGraph` 构建的 ReAct 式 Agent：

```
User Message → chatbot 节点
      ↓（判断是否需检索）
      ├─→ 工具节点（retrieve_relevant_documents）→ 回到 chatbot
      └─→ END
```

- **LLM**：`deepseek-chat` via OpenAI-compatible ChatOpenAI
- **System Prompt**：默认中文回复 + 仅基于检索上下文回答 + 回答简洁
- **RAG 工具**：`retrieve_relevant_documents(query)` — ChromaDB MMR 检索 Top 2
- **向量库路径**：`./chroma_langchain_db/`（首次使用前需通过脚本导入文档）

### SchedulerManager（tools/scheduler.py）

单例模式的调度器管理器：

```python
from tools.scheduler import scheduler_manager, validate_cron

# 校验 cron
print(validate_cron("*/2 * * * *"))
# { "valid": True, "human_readable": "每2分钟执行", ... }

# 添加任务（支持 "module.path.func" 字符串）
scheduler_manager.add_job(
    job_id="my_task",
    func="api.crawler.fetch_and_save",
    cron_expr="0 * * * *",
)

# 生命周期
scheduler_manager.start()
scheduler_manager.pause_job("my_task")
scheduler_manager.resume_job("my_task")
scheduler_manager.remove_job("my_task")
scheduler_manager.shutdown()

# 查看状态
print(scheduler_manager.get_status())
# { "running": True, "jobs": [{ "id": "...", "next_run": "..." }] }
```

注意事项：

- 单进程部署下运行正常；多 worker（Gunicorn/uWSGI）请使用外部调度系统（Celery Beat / systemd timer / Kubernetes CronJob）
- Django dev server 的 auto-reloader 会在辅助进程中自动跳过初始化（检测 `RUN_MAIN` 环境变量）
- 每次任务执行后自动调用 `connections.close_all()` 防止连接泄漏

---

## 📝 常用命令

```bash
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 启动服务
python manage.py runserver 0.0.0.0:8000

# 手动爬取抖音热搜
python manage.py crawl_douyin

# 创建超级管理员（访问 /admin）
python manage.py createsuperuser

# 收集静态文件（生产环境）
python manage.py collectstatic --noinput
```

---

## 🔐 安全提示（部署前必改）

1. **修改 `SECRET_KEY`**：`djangoproj/settings.py` 中请替换为强随机字符串
2. **关闭 DEBUG**：生产环境 `DEBUG = False`
3. **收紧 `ALLOWED_HOSTS`**：不要使用 `"*"`，填写实际域名/IP
4. **数据库凭据**：使用环境变量注入，不要硬编码在 settings.py 中（可配合 `python-dotenv` + `os.getenv`）
5. **API Key 保管**：`DEEPSEEK_API_KEY` 严禁提交到 Git
6. **HTTPS**：生产环境务必启用 HTTPS，推荐 Nginx 反向代理 + Gunicorn

---

## 🐛 常见问题

**Q: 启动后 ChromaDB 报 sqlite3 版本错误？**
A: 若系统自带 sqlite3 版本过低，可安装 `pysqlite3-binary` 并在项目入口 `__init__.py` 中 `import pysqlite3; import sys; sys.modules['sqlite3'] = pysqlite3`。

**Q: 抖音爬虫无数据？**
A: 当前 `api/crawler.py` 采用模拟数据兜底（抖音官方 API 需要登录签名）。如需真实数据，请在 `fetch_and_save()` 中替换为带 Cookie/Signature 的请求实现。

**Q: 调度器多 worker 重复执行？**
A: 使用外部调度（如 systemd timer、Celery Beat、K8s CronJob）触发 `python manage.py crawl_douyin`，禁用页面内 APScheduler。

**Q: Embedding 模型下载慢？**
A: 设置 `HF_ENDPOINT=https://hf-mirror.com` 或手动下载 `all-MiniLM-L6-v2` 到本地并在 `chatbot.py` 中用本地路径加载。

---

## 📜 License

MIT

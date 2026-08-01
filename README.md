# Nocturne AI · 暗夜智能对话平台

基于 **Django 4.2** + **LangGraph** + **DeepSeek API** 构建的 AI 智能对话平台，集成 **RAG 检索增强生成**、**SSH 远程运维**、**抖音热搜爬虫**、**定时调度系统**、**用户认证与权限隔离** 等功能模块。采用优雅的暗色主题（Nocturne）设计，响应式布局，移动端适配，开箱即用。

---

## ✨ 功能特性

### 🤖 AI 智能对话
- **DeepSeek 大模型**：使用 DeepSeek API（OpenAI 兼容接口），默认中文回复
- **LangGraph Agent 架构**：支持双工具调用（RAG 检索 + SSH 远程命令），具备可观测的执行状态图
- **多轮对话管理**：基于数据库的会话/消息存储，支持历史记录回溯与继续对话
- **流式输出**：SSE 流式响应（token 级别），打字机效果即时展示 AI 回复
- **RAG 检索增强**：基于 ChromaDB + HuggingFace Embeddings 的本地向量库，支持动态添加文档
- **SSH 远程运维**：AI 可自动执行远程服务器命令（查看状态、进程、日志等），内置危险命令拦截

### � 用户认证与权限
- **Django Auth 系统**：登录 / 登出 / 密码重置（邮件链接方式）
- **权限隔离**：普通用户只能查看自己的对话记录，管理员（admin）可查看所有
- **密码重置**：完整邮件重置流程（开发环境输出到控制台，生产环境支持 SMTP）
- **Admin 后台**：所有数据模型已注册，支持后台管理

### �🔥 抖音热搜榜
- **实时爬取**：一键抓取抖音平台当前热搜话题（排名、标题、热度、标签）
- **数据入库**：MySQL 持久化存储，支持多批次历史数据回溯
- **榜单展示**：Top 3 高亮，热度图标 + 标签分级（热/新/沸）
- **管理命令**：`python manage.py crawl_douyin` 支持脚本/CI 调用

### ⏰ 定时调度系统
- **APScheduler 后台调度**：基于 MemoryJobStore 的单例调度管理器
- **Cron 表达式**：支持标准 5 段 cron（分 时 日 月 周），内置中文语义描述
- **前端可视化配置**：启动/停止按钮、快捷预设、下次执行预览、执行统计
- **任务持久化**：SchedulerConfig 模型记录启用状态、cron、上次执行时间/结果/总次数

### 🧰 Python 工具类集合
`tools/` 目录下提供通用工具模块：

| 模块 | 说明 |
|---|---|
| `ssh_utils.py` | SSH 远程命令执行（exec/upload/download，基于系统 ssh/scp） |
| `scheduler.py` | 定时调度管理器（APScheduler 封装，单例模式，Cron 支持） |
| `date_utils.py` | 日期时间处理（格式化、时区转换、相对时间） |
| `string_utils.py` | 字符串处理（截断、脱敏、URL 解析、正则辅助） |
| `http_utils.py` | HTTP 请求封装（重试、超时、统一异常） |
| `db_utils.py` | 数据库辅助（批量插入、分页查询、事务上下文） |
| `format_utils.py` | 数据格式化（字节/数字/JSON/货币格式化，表格渲染） |

### 🎨 UI / UX
- **Nocturne 暗色主题**：薄荷绿 + 琥珀金渐变，玻璃拟态 + 细颗粒网格背景
- **响应式设计**：移动端 / 平板 / 桌面端自适应，手机端聊天侧边栏抽屉模式
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
├── core/                         # Django 项目配置
│   ├── settings.py               # 数据库 / 认证 / 邮件 / 静态文件 配置
│   ├── urls.py                   # 全局 URL 路由（含 Admin + Auth）
│   ├── asgi.py / wsgi.py         # ASGI / WSGI 入口
│   └── __init__.py               # pymysql 初始化
├── common/                       # AI 对话 应用
│   ├── migrations/
│   │   ├── 0001_initial.py       # Conversation / Message 模型
│   │   └── 0002_conversation_user.py  # 用户字段迁移
│   ├── admin.py                  # Admin 后台注册
│   ├── models.py                 # 会话、消息 ORM（含 user 外键）
│   └── views.py                  # 聊天页面、流式 API、历史记录（含权限隔离）
├── api/                          # 抖音热搜 + 调度 应用
│   ├── management/commands/
│   │   └── crawl_douyin.py       # Django 管理命令：爬取热搜
│   ├── migrations/
│   │   ├── 0001_initial.py
│   │   └── 0002_schedulerconfig.py
│   ├── admin.py                  # Admin 后台注册
│   ├── crawler.py                # 抖音热搜爬虫核心
│   ├── models.py                 # DouyinHotSearch / SchedulerConfig
│   ├── urls.py                   # API 路由
│   └── views.py                  # 视图 + 调度管理 API
├── tools/                        # Python 工具类集合
│   ├── ssh_utils.py              # SSH 远程命令执行
│   ├── scheduler.py              # 定时调度管理器
│   ├── date_utils.py             # 日期时间处理
│   ├── string_utils.py           # 字符串处理
│   ├── http_utils.py             # HTTP 请求封装
│   ├── db_utils.py               # 数据库辅助
│   └── format_utils.py           # 数据格式化
├── templates/                    # HTML 模板
│   ├── base.html                 # 全局基模板（导航栏用户菜单 / 页脚）
│   ├── home.html                 # 首页
│   ├── chat.html                 # 对话页（移动端抽屉模式）
│   ├── history.html              # 历史记录页
│   ├── registration/             # Django Auth 模板
│   │   ├── login.html            # 登录页
│   │   ├── password_reset_form.html
│   │   ├── password_reset_done.html
│   │   ├── password_reset_confirm.html
│   │   ├── password_reset_complete.html
│   │   ├── password_reset_email.txt
│   │   └── password_reset_subject.txt
│   └── api/
│       └── douyin_hot.html       # 抖音热搜 + 调度配置面板
├── static/                       # 静态资源
│   ├── css/styles.css            # Nocturne 主题样式
│   └── js/chat.js                # 聊天页交互 + 流式渲染
├── chatbot.py                    # LangGraph Agent（LLM + RAG 工具 + SSH 工具）
├── manage.py                     # Django 入口
├── requirements.txt              # 依赖清单
├── .env                          # 环境变量（DEEPSEEK_API_KEY，需自行创建）
├── .gitignore
└── README.md
```

---

## 🚀 快速开始

### 1. 环境要求

- Python 3.11+
- MySQL 8.0+（已创建数据库 `ai_chatbot`）
- 可用的 DeepSeek API Key（[申请地址](https://platform.deepseek.com/)）
- （可选）SSH 免密登录配置（用于 AI 远程运维功能）

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
```

### 4. 配置数据库连接

编辑 [core/settings.py](core/settings.py) 中的 `DATABASES` 配置：

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": "ai_chatbot",
        "USER": "root",
        "PASSWORD": "your_password",
        "HOST": "127.0.0.1",
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
| `common_conversation` | AI 对话会话（含 user 外键） |
| `common_message` | 对话消息（用户 / 助手） |
| `douyin_hot_search` | 抖音热搜数据 |
| `scheduler_config` | 定时任务配置 |

### 6. 创建超级用户

```bash
python manage.py createsuperuser
```

用于登录系统和管理 Admin 后台。

### 7. 启动开发服务器

```bash
python manage.py runserver 0.0.0.0:8000
```

访问以下地址验证功能：

| 页面 | URL | 说明 |
|---|---|---|
| 登录 | http://localhost:8000/accounts/login/ | 用户认证 |
| 首页 | http://localhost:8000/ | 功能概览 |
| AI 对话 | http://localhost:8000/chat/ | 智能对话（支持 SSH 运维） |
| 历史记录 | http://localhost:8000/history/ | 对话历史 |
| 抖音热搜 | http://localhost:8000/api/douyin/hot/ | 热搜 + 调度配置 |
| Admin 后台 | http://localhost:8000/admin/ | 数据管理 |

---

## 🔌 API 接口

### AI 对话（需登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/chat/api/chat/stream/` | 流式对话（SSE），body: `{ "conversation_id": 1, "message": "..." }` |
| DELETE | `/chat/api/conversations/<int:conv_id>/` | 删除指定会话 |

### 抖音热搜（需登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/douyin/hot/` | 热搜榜 HTML 页面 |
| POST | `/api/douyin/crawl/` | 触发爬取，返回 `{ success, total, batch_time, items }` |
| CLI | `python manage.py crawl_douyin` | 命令行触发爬取 |

### 定时调度（需登录）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/scheduler/status/` | 获取调度器与任务状态 |
| POST | `/api/scheduler/start/` | 启动任务，body: `{ "cron_expr": "0 * * * *" }` |
| POST | `/api/scheduler/stop/` | 停止并移除任务 |

### 认证（公开）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET/POST | `/accounts/login/` | 登录 |
| GET | `/accounts/logout/` | 登出 |
| GET/POST | `/accounts/password_reset/` | 密码重置（发送邮件） |
| GET/POST | `/accounts/reset/<uidb64>/<token>/` | 设置新密码 |

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

常用预设：`*/30 * * * *`（每30分钟）、`0 * * * *`（每小时）、`0 */6 * * *`（每6小时）、`0 0 * * *`（每天凌晨）

---

## ⚙️ 模块详解

### LangGraph Agent（chatbot.py）

基于 `StateGraph` 构建的 ReAct 式 Agent，支持双工具调用：

```
User Message → chatbot 节点
      ↓（判断是否需要工具）
      ├─→ retrieve_relevant_documents（RAG 检索）→ 回到 chatbot
      ├─→ execute_ssh_command（SSH 远程命令）→ 回到 chatbot
      └─→ END
```

- **LLM**：`deepseek-chat` via OpenAI-compatible ChatOpenAI
- **RAG 工具**：ChromaDB MMR 检索 Top 2，支持动态添加文档
- **SSH 工具**：在远程服务器执行命令，内置危险命令黑名单，30 秒超时
- **流式输出**：`stream_chat()` 基于 `stream_mode="messages"` 实现 token 级流式

```python
from chatbot import llm, graph, stream_chat, add_documents, get_document_count

# 纯 LLM 流式
for chunk in llm.stream(messages):
    print(chunk.content)

# Agent 流式（支持工具调用）
for chunk in stream_chat([{"role": "user", "content": "服务器状态如何？"}]):
    print(chunk, end="")

# 向知识库添加文档
add_documents(["文档内容1", "文档内容2"], [{"title": "标题1"}, {"title": "标题2"}])
```

### SSH 远程运维（tools/ssh_utils.py）

```python
from tools.ssh_utils import ssh_exec, ssh_upload, ssh_download, ssh_check

# 执行远程命令
stdout, stderr, returncode = ssh_exec("hostname; uptime")

# 上传/下载文件
ssh_upload("local.txt", "/root/remote.txt")
ssh_download("/root/remote.txt", "local.txt")

# 检查连接
if ssh_check():
    print("SSH 连接正常")
```

### 用户权限隔离（common/views.py）

- **普通用户**：只能查看/操作自己的对话记录（`Conversation.objects.filter(user=request.user)`）
- **管理员**：可查看所有用户的对话记录（`Conversation.objects.all()`）
- 新建对话自动绑定当前用户
- 跨用户访问返回 404

### 邮件配置（core/settings.py）

开发环境使用 console backend（邮件输出到控制台），生产环境切换为 SMTP：

```python
# 开发环境（当前）
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# 生产环境（取消注释并填写 SMTP 信息）
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = "smtp.qq.com"
# EMAIL_PORT = 465
# EMAIL_USE_SSL = True
# EMAIL_HOST_USER = "your_email@qq.com"
# EMAIL_HOST_PASSWORD = "your_auth_code"
```

### SchedulerManager（tools/scheduler.py）

```python
from tools.scheduler import scheduler_manager, validate_cron

# 校验 cron
print(validate_cron("*/2 * * * *"))
# { "valid": True, "human_readable": "每2分钟执行", ... }

# 添加任务
scheduler_manager.add_job(
    job_id="my_task",
    func="api.crawler.fetch_and_save",
    cron_expr="0 * * * *",
)

scheduler_manager.start()
print(scheduler_manager.get_status())
```

---

## 📝 常用命令

```bash
# 数据库迁移
python manage.py makemigrations
python manage.py migrate

# 启动服务
python manage.py runserver 0.0.0.0:8000

# 创建超级用户
python manage.py createsuperuser

# 手动爬取抖音热搜
python manage.py crawl_douyin

# 收集静态文件（生产环境）
python manage.py collectstatic --noinput
```

---

## 🔐 安全提示（部署前必改）

1. **修改 `SECRET_KEY`**：`core/settings.py` 中请替换为强随机字符串
2. **关闭 DEBUG**：生产环境 `DEBUG = False`
3. **收紧 `ALLOWED_HOSTS`**：不要使用 `"*"`，填写实际域名/IP
4. **数据库凭据**：使用环境变量注入，不要硬编码在 settings.py 中
5. **API Key 保管**：`DEEPSEEK_API_KEY` 严禁提交到 Git
6. **SSH 安全**：`tools/ssh_utils.py` 中的主机配置请根据实际环境修改
7. **HTTPS**：生产环境务必启用 HTTPS

---

## 🐛 常见问题

**Q: 启动后 ChromaDB 报 sqlite3 版本错误？**
A: 安装 `pysqlite3-binary` 并在 `core/__init__.py` 中替换 sqlite3 模块。

**Q: 抖音爬虫无数据？**
A: 当前 `api/crawler.py` 采用模拟数据兜底（抖音官方 API 需要登录签名）。如需真实数据，请替换为带 Cookie/Signature 的请求实现。

**Q: SSH 工具连接失败？**
A: 确保已配置 SSH 免密登录（`ssh-copy-id root@your_server`），并检查 `tools/ssh_utils.py` 中的主机配置。

**Q: Embedding 模型下载慢？**
A: 设置 `HF_ENDPOINT=https://hf-mirror.com` 或设置 `HF_HUB_OFFLINE=1` 使用本地缓存。

**Q: 调度器多 worker 重复执行？**
A: 使用外部调度（systemd timer、Celery Beat、K8s CronJob）触发 `python manage.py crawl_douyin`，禁用页面内 APScheduler。

---

## 📜 License

MIT

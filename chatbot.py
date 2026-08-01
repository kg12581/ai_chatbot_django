"""AI 对话核心模块。

提供两种对话模式：
  - llm: 纯大模型对话（直接调用 DeepSeek，无检索增强）
  - graph: Agent 模式（LangGraph 工作流，可调用 RAG 检索和 SSH 远程命令工具）

使用方式：
  from chatbot import llm              # 纯 LLM
  from chatbot import graph            # Agent 工作流
  from chatbot import stream_chat      # Agent 流式输出（token 级别）
  from chatbot import add_documents    # 向知识库添加文档
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Annotated

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

load_dotenv()

logger = logging.getLogger(__name__)

# ==================== LLM 配置 ====================

llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    temperature=0.7,
)

# ==================== RAG 向量库 ====================

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vector_store = Chroma(
    collection_name="rag_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)

retriever = vector_store.as_retriever(
    search_type="mmr", search_kwargs={"k": 2, "fetch_k": 10}
)


def add_documents(texts, metadatas=None):
    """向知识库添加文档。

    Args:
        texts: 文档文本列表，例如 ["文档1内容", "文档2内容"]
        metadatas: 元数据列表，例如 [{"title": "标题1", "url": "..."}]
    """
    docs = [
        Document(page_content=t, metadata=m or {})
        for t, m in zip(texts, metadatas or [{}] * len(texts))
    ]
    vector_store.add_documents(docs)
    logger.info(f"已添加 {len(docs)} 篇文档到知识库，当前总数: {vector_store._collection.count()}")
    return len(docs)


def get_document_count():
    """返回知识库中的文档数量。"""
    return vector_store._collection.count()


def _format_document(document) -> str:
    title = document.metadata.get("title")
    url = document.metadata.get("url")
    parts = []
    if title:
        parts.append(f"标题: {title}")
    if url:
        parts.append(f"链接: {url}")
    parts.append(f"内容:\n{document.page_content}")
    return "\n".join(parts)


@tool
def retrieve_relevant_documents(query: str) -> list:
    """根据查询检索知识库中的相关文档。"""
    results = retriever.invoke(query)
    if not results:
        return ["未检索到相关文档。"]
    return [_format_document(doc) for doc in results]


# ==================== SSH 远程命令工具 ====================

# 危险命令黑名单（禁止执行）
_DANGEROUS_PATTERNS = [
    "rm -rf", "shutdown", "reboot", "halt", "init ", "mkfs",
    "dd if=", "> /dev/sd", "chmod -R 777 /", "userdel", "groupdel",
]


def _is_dangerous(command: str) -> bool:
    """检查命令是否包含危险操作。"""
    cmd_lower = command.lower()
    return any(p in cmd_lower for p in _DANGEROUS_PATTERNS)


@tool
def execute_ssh_command(command: str) -> str:
    """在 Rocky Linux 远程服务器 (192.168.3.100) 上执行 SSH 命令。

    可用于查询服务器状态、查看进程、检查日志、查看文件等。
    禁止执行危险命令（如 rm -rf、shutdown、reboot 等）。

    Args:
        command: 要在远程服务器上执行的 shell 命令
    Returns:
        命令的输出结果（stdout），如果出错则返回错误信息
    """
    if _is_dangerous(command):
        return f"安全限制：命令 '{command}' 包含危险操作，已被拒绝执行。"

    from tools.ssh_utils import ssh_exec

    try:
        stdout, stderr, returncode = ssh_exec(command, timeout=30)
        result = ""
        if stdout:
            # 截断过长的输出
            if len(stdout) > 3000:
                stdout = stdout[:3000] + "\n... (输出已截断)"
            result += stdout
        if stderr and returncode != 0:
            result += f"\n[stderr]: {stderr[:500]}"
        if not result:
            result = f"(命令执行完成，退出码 {returncode}，无输出)"
        return result
    except Exception as e:
        return f"SSH 执行失败: {e}"


# ==================== GitHub 仓库分析工具 ====================

_GITHUB_REPO_CACHE = {}  # repo_url -> {repo_dir, files}

# 忽略的文件/目录（不读取大文件、二进制文件、第三方库等）
_GITHUB_IGNORE_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".idea", ".vscode", "target", "vendor",
}
_GITHUB_READABLE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h", ".hpp",
    ".go", ".rs", ".rb", ".php", ".cs", ".swift", ".kt", ".scala",
    ".html", ".css", ".scss", ".vue", ".svelte",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".md", ".txt", ".sh", ".bash", ".zsh", ".dockerfile",
    ".sql", ".xml", ".proto",
}
_GITHUB_MAX_FILE_SIZE = 50 * 1024  # 单文件最大 50KB


def _safe_join(base: str, rel: str) -> Path:
    """安全路径拼接，防止目录穿越。"""
    base_p = Path(base).resolve()
    target = (base_p / rel).resolve()
    if base_p not in target.parents and target != base_p:
        raise ValueError(f"路径非法: {rel}")
    return target


def _repo_key(url: str) -> str:
    """从 URL 提取仓库标识（owner/repo）。"""
    url = url.rstrip("/").rstrip(".git")
    if url.startswith("https://github.com/"):
        return "/".join(url.replace("https://github.com/", "").split("/")[:2])
    return url


@tool
def github_clone_repo(repo_url: str) -> str:
    """克隆一个 GitHub 仓库到本地临时目录（仅克隆最新 1 个 commit，速度快）。

    Args:
        repo_url: GitHub 仓库地址，例如 https://github.com/kg12581/ai_chatbot_django
    Returns:
        仓库标识（owner/repo）和基础文件列表
    """
    key = _repo_key(repo_url)
    if key in _GITHUB_REPO_CACHE:
        info = _GITHUB_REPO_CACHE[key]
        return f"仓库已缓存: {key}\n目录: {info['repo_dir']}\n{info['file_tree_preview']}"

    try:
        tmp = Path(tempfile.mkdtemp(prefix="ghrepo_")).resolve()
        repo_name = Path(repo_url.rstrip("/").rstrip(".git").split("/")[-1])
        repo_dir = str((tmp / repo_name).resolve())

        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--single-branch", repo_url, repo_dir],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            shutil.rmtree(str(tmp), ignore_errors=True)
            return f"克隆失败: {proc.stderr[:500]}"

        # 构建文件树
        files = []
        repo_dir_path = Path(repo_dir)
        for p in repo_dir_path.rglob("*"):
            if not p.is_file():
                continue
            rel = p.relative_to(repo_dir_path).as_posix()
            parts = set(rel.split("/"))
            if _GITHUB_IGNORE_DIRS & parts:
                continue
            files.append(rel)
        files.sort()

        # 文件树预览（前 150 个文件）
        preview_lines = []
        for f in files[:150]:
            preview_lines.append(f)
        if len(files) > 150:
            preview_lines.append(f"... 还有 {len(files) - 150} 个文件")
        tree_preview = f"共 {len(files)} 个文件:\n" + "\n".join(preview_lines)

        _GITHUB_REPO_CACHE[key] = {
            "repo_dir": repo_dir,
            "tmp_dir": tmp,
            "files": files,
            "file_tree_preview": tree_preview,
        }

        return f"✅ 已克隆: {key}\n目录: {repo_dir}\n{tree_preview}"
    except subprocess.TimeoutExpired:
        return "克隆超时（120 秒）。"
    except Exception as e:
        return f"克隆失败: {e}"


@tool
def github_list_files(repo_url: str, directory: str = "", pattern: str = "") -> str:
    """列出已克隆仓库的指定目录下的文件，支持按后缀过滤。

    Args:
        repo_url: GitHub 仓库地址（必须先调用 github_clone_repo 克隆）
        directory: 子目录，留空表示根目录
        pattern: 文件名后缀过滤，例如 .py 或 .ts
    Returns:
        匹配的文件列表
    """
    key = _repo_key(repo_url)
    if key not in _GITHUB_REPO_CACHE:
        return "仓库未克隆，请先调用 github_clone_repo。"
    info = _GITHUB_REPO_CACHE[key]

    try:
        base = _safe_join(info["repo_dir"], directory)
    except ValueError:
        return "目录路径非法。"
    if not base.is_dir():
        return f"目录不存在: {directory or '/'}"

    result = []
    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(info["repo_dir"]).as_posix()
        parts = set(rel.split("/"))
        if _GITHUB_IGNORE_DIRS & parts:
            continue
        if pattern and not rel.lower().endswith(pattern.lower()):
            continue
        # 只列当前目录层级 + 1 层深度的，避免返回过多
        depth_diff = len(Path(rel).parts) - len((Path(directory) if directory else Path("")).parts)
        if depth_diff <= 2:
            try:
                sz = p.stat().st_size
                sz_str = f"{sz/1024:.1f}KB" if sz < 1024*1024 else f"{sz/1024/1024:.1f}MB"
                result.append(f"{rel}  ({sz_str})")
            except OSError:
                result.append(rel)
        if len(result) >= 200:
            result.append("... (结果过多，已截断到 200 条)")
            break
    return "\n".join(result) if result else "(无匹配文件)"


@tool
def github_read_file(repo_url: str, file_path: str, start_line: int = 0, max_lines: int = 300) -> str:
    """读取已克隆仓库中的指定文件内容，支持按行范围读取。

    Args:
        repo_url: GitHub 仓库地址
        file_path: 仓库内的文件相对路径，例如 common/views.py
        start_line: 起始行号（从 0 开始，留空表示从头读）
        max_lines: 最多读取行数，默认 300
    Returns:
        文件内容（带行号）
    """
    key = _repo_key(repo_url)
    if key not in _GITHUB_REPO_CACHE:
        return "仓库未克隆，请先调用 github_clone_repo。"
    info = _GITHUB_REPO_CACHE[key]

    try:
        target = _safe_join(info["repo_dir"], file_path)
    except ValueError:
        return "文件路径非法。"

    if not target.is_file():
        return f"文件不存在: {file_path}"

    ext = target.suffix.lower()
    if ext not in _GITHUB_READABLE_EXTS and ext != "":
        return f"文件类型 {ext} 不支持读取（可能是二进制文件）。"

    try:
        size = target.stat().st_size
        if size > _GITHUB_MAX_FILE_SIZE:
            return f"文件过大 ({size/1024:.1f}KB)，超过 {_GITHUB_MAX_FILE_SIZE/1024:.0f}KB 限制。"
        content = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"读取失败: {e}"

    lines = content.splitlines()
    end_line = min(start_line + max_lines, len(lines))
    snippet = lines[start_line:end_line]

    numbered = []
    for i, line in enumerate(snippet, start=start_line + 1):
        numbered.append(f"{i:5d}| {line}")

    header = f"文件: {file_path}  (共 {len(lines)} 行，显示 {start_line+1}-{end_line})"
    return header + "\n" + "\n".join(numbered)


@tool
def github_search_code(repo_url: str, keyword: str) -> str:
    """在已克隆仓库中全文搜索关键词，返回匹配的文件和行号。

    Args:
        repo_url: GitHub 仓库地址
        keyword: 搜索关键词，支持简单字符串匹配（区分大小写）
    Returns:
        匹配结果列表
    """
    key = _repo_key(repo_url)
    if key not in _GITHUB_REPO_CACHE:
        return "仓库未克隆，请先调用 github_clone_repo。"
    info = _GITHUB_REPO_CACHE[key]

    if not keyword or len(keyword) < 2:
        return "关键词太短（至少 2 个字符）。"

    results = []
    for rel in info["files"]:
        ext = Path(rel).suffix.lower()
        if ext not in _GITHUB_READABLE_EXTS and ext != "":
            continue
        try:
            target = info["repo_dir"] / Path(rel)
            if target.stat().st_size > _GITHUB_MAX_FILE_SIZE:
                continue
            lines = target.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            if keyword in line:
                snippet = line.strip()[:120]
                results.append(f"{rel}:{i}  {snippet}")
                if len(results) >= 80:
                    break
        if len(results) >= 80:
            results.append("... (结果过多，已截断到 80 条)")
            break
    return "\n".join(results) if results else f"未找到包含 '{keyword}' 的代码。"


# ==================== LangGraph Agent 工作流 ====================

tools = [
    retrieve_relevant_documents,
    execute_ssh_command,
    github_clone_repo,
    github_list_files,
    github_read_file,
    github_search_code,
]
llm_with_tools = llm.bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def _chatbot_node(state: State):
    """LangGraph 聊天节点：Agent 模式，可调用工具。"""
    system_prompt = (
        "你是一个智能AI助手，请默认使用中文回答用户的问题。\n"
        "回答尽量简洁明了。\n\n"
        "你可以使用以下工具来帮助回答问题：\n"
        "1. retrieve_relevant_documents: 检索本地知识库中的相关文档\n"
        "2. execute_ssh_command: 在 Rocky Linux 远程服务器上执行命令\n"
        "   - 可用于查看服务器状态、进程、日志、文件等\n"
        "   - 例如：hostname、uptime、ps aux、df -h、free -m\n"
        "   - 禁止执行危险命令（rm -rf、shutdown 等）\n"
        "3. github_clone_repo: 克隆 GitHub 仓库到本地（仅 latest commit，速度快）\n"
        "   - 参数: repo_url (例如 https://github.com/kg12581/ai_chatbot_django)\n"
        "4. github_list_files: 列出已克隆仓库的目录内容，支持按后缀过滤\n"
        "   - 参数: repo_url, directory(可选), pattern(可选，如 .py)\n"
        "5. github_read_file: 读取仓库中的指定文件内容（带行号，最多300行）\n"
        "   - 参数: repo_url, file_path, start_line(可选), max_lines(可选)\n"
        "6. github_search_code: 在仓库中全文搜索关键词\n"
        "   - 参数: repo_url, keyword\n\n"
        "分析 GitHub 仓库代码的标准流程：\n"
        "  步骤1: 用 github_clone_repo 克隆仓库\n"
        "  步骤2: 用 github_list_files 查看目录结构\n"
        "  步骤3: 根据需要用 github_read_file 读取核心文件\n"
        "  步骤4: 或用 github_search_code 搜索特定关键词\n"
        "  步骤5: 综合结果给出分析报告\n\n"
        "当用户询问服务器相关信息时，请主动使用 SSH 工具获取实时数据。\n"
        "当用户询问项目相关知识时，请先检索知识库。\n"
        "当用户要求分析 GitHub 仓库或查看代码时，请按上述流程使用 GitHub 工具。"
    )

    # 动态加载激活的 Skill 与 MCP 配置
    try:
        from common.skill_views import get_active_skills_prompt, get_active_mcp_tools_info
        skill_prompt = get_active_skills_prompt()
        mcp_info = get_active_mcp_tools_info()
        if skill_prompt:
            system_prompt += skill_prompt
        if mcp_info:
            system_prompt += "\n\n可用的 MCP 工具与服务器：\n" + mcp_info
    except Exception as e:
        logger.warning(f"加载 Skill/MCP 配置失败（非致命）: {e}")

    system_message = SystemMessage(content=system_prompt)
    return {
        "messages": [
            llm_with_tools.invoke([system_message] + state["messages"]),
        ]
    }


graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", _chatbot_node)
tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)
graph_builder.add_conditional_edges("chatbot", tools_condition)
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")
graph = graph_builder.compile()


def stream_chat(history_messages):
    """Agent 流式对话（token 级别输出）。

    使用 LangGraph 的 stream_mode='messages' 实现 token 级别流式输出，
    同时支持工具调用（RAG 检索 + SSH 命令）。

    Args:
        history_messages: 历史消息列表，格式 [{"role": "user", "content": "..."}, ...]

    Yields:
        str: AI 回复的文本片段
    """
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    # 构建消息列表（不含 system prompt，graph 节点中会添加）
    messages = []
    for msg in history_messages:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # 使用 stream_mode='messages' 实现 token 级别流式
    for chunk, metadata in graph.stream(
        {"messages": messages},
        stream_mode="messages",
    ):
        # 只输出 chatbot 节点产生的 AI 回复内容
        if (
            metadata.get("langgraph_node") == "chatbot"
            and hasattr(chunk, "content")
            and chunk.content
        ):
            yield chunk.content


def get_chatbot_response(messages: list):
    """使用 Agent 工作流同步调用（含工具调用）。

    Args:
        messages: LangChain 消息列表
    Returns:
        graph.invoke 的完整结果
    """
    logger.info(f"Agent 调用，输入消息数: {len(messages)}, 知识库文档数: {get_document_count()}")
    return graph.invoke({"messages": messages})

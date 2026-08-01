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


# ==================== LangGraph Agent 工作流 ====================

tools = [retrieve_relevant_documents, execute_ssh_command]
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
        "   - 例如：hostname、uptime、ps aux、df -h、free -m、cat /etc/os-release\n"
        "   - 禁止执行危险命令（rm -rf、shutdown 等）\n\n"
        "当用户询问服务器相关信息时，请主动使用 SSH 工具获取实时数据。\n"
        "当用户询问项目相关知识时，请先检索知识库。"
    )

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

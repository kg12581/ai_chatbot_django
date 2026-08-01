"""AI 对话核心模块。

提供两种对话模式：
  - llm: 纯大模型对话（直接调用 DeepSeek，无检索增强）
  - graph: RAG 模式（LangGraph 工作流，先检索知识库再回答）

使用方式：
  from chatbot import llm              # 纯 LLM 流式输出
  from chatbot import graph            # RAG 模式
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

# ==================== LangGraph RAG 工作流 ====================

tools = [retrieve_relevant_documents]
llm_with_tools = llm.bind_tools(tools)


class State(TypedDict):
    messages: Annotated[list, add_messages]


def _chatbot_node(state: State):
    """LangGraph 聊天节点：根据检索到的上下文回答问题。"""
    doc_count = get_document_count()
    if doc_count == 0:
        # 知识库为空时，提示 LLM 直接回答
        system_prompt = (
            "你是一个智能AI助手，请默认使用中文回答用户的问题。\n"
            "回答尽量简洁明了。"
        )
    else:
        system_prompt = (
            "你是一个智能AI助手，请默认使用中文回答用户的问题。\n"
            "请先使用工具检索相关文档，然后根据检索到的上下文回答问题。\n"
            "如果检索结果不足以回答问题，可以结合自身知识回答，但要说明情况。\n"
            "回答尽量简洁明了。"
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


def get_chatbot_response(messages: list):
    """使用 RAG 工作流同步调用（含知识库检索）。

    Args:
        messages: LangChain 消息列表
    Returns:
        graph.invoke 的完整结果
    """
    logger.info(f"RAG 调用，输入消息数: {len(messages)}, 知识库文档数: {get_document_count()}")
    return graph.invoke({"messages": messages})

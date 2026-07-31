import os
from typing import Annotated
from langchain_core.messages import SystemMessage
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.tools import tool

from dotenv import load_dotenv

load_dotenv()

# 使用 HuggingFace 本地 Embedding（无需 API Key，首次运行会自动下载模型）
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vector_store = Chroma(
    collection_name="rag_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",
)

retriever = vector_store.as_retriever(
    search_type="mmr", search_kwargs={"k": 2, "fetch_k": 10}
)

def _format_document(document) -> str:
    title = document.metadata.get("title")
    url = document.metadata.get("url")
    metadata_summary = (
        f"Title: {title}" if title else f"Metadata: {document.metadata}"
    )
    if url:
        metadata_summary = f"{metadata_summary}\nURL: {url}"

    return f"{metadata_summary}\nContent:\n{document.page_content}"


@tool
def retrieve_relevant_documents(query: str) -> list:
    "This tool will retrieve relevant document based on the query, this tool will give you all the available context"
    results = retriever.invoke(query)
    formatted_results = [_format_document(doc) for doc in results]
    return formatted_results

class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

# tool = TavilySearch(max_results=2)
# tools = [tool]
tools = [retrieve_relevant_documents]
# 使用 DeepSeek API（OpenAI 兼容接口）
llm = ChatOpenAI(
    model="deepseek-chat",
    api_key=os.environ["DEEPSEEK_API_KEY"],
    base_url="https://api.deepseek.com",
    temperature=0.7,
)
llm_with_tools = llm.bind_tools(tools)


def chatbot(state: State):
    SYSTEM_PROMPT = (
        "你是一个智能AI助手，请默认使用中文回答用户的问题。\n"
        "只根据以下检索到的上下文内容来回答问题。\n"
        "如果不知道答案，就直接说不知道，不要编造答案。\n"
        "回答前请始终使用工具检索相关内容。\n"
        "回答尽量简洁明了。"
    )

    system_message = SystemMessage(content=SYSTEM_PROMPT)

    return {
        "messages": [
            llm_with_tools.invoke([system_message] + state["messages"]),
        ]
    }


graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=[retrieve_relevant_documents])
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
# Any time a tool is called, we return to the chatbot to decide the next step
graph_builder.add_edge("tools", "chatbot")
graph_builder.add_edge(START, "chatbot")

graph = graph_builder.compile()

def get_chatbot_response(messages: list):
    print(f"Input messages to graph: {messages}")
    result = graph.invoke({"messages": messages})
    print(f"Graph result: {result}")
    return result
from typing import TypedDict, Annotated, Literal
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_community.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, START, END, add_messages
from langgraph.prebuilt import ToolNode
from dotenv import load_dotenv
from sqlalchemy import Engine

from agent_tools import get_tools

load_dotenv()

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    website_url: str
    repo_name: str
    conclusion: str

analyze_prompt = ChatPromptTemplate([
    (
        "system",
        """
        You are a friendly website quality assurance analyzer agent. Your job is to use your tools to visit
        the website URL provided and analyze it for issues, suggestions, and possible improvements.
        You are also able to view the GitHub repository for the website and read the website's source.
        You are provided the conversation history including past messages from this quality assurance
        agent and past messages from the human. The human's query should be the latest human message.
        The query could be a command t analyze the website, or some aspect of the website. It could
        also be a question that the human has about their website. You do not do anything other than
        analyze the website, submit diagnostics, and answer questions related to the website.
        Don't submit diagnostics without a good reason. If you are just speculating, without being
        very confident, then don't submit a diagnostic.
        Your name is Webster.
        Think in steps.
        You have browser interaction tools. For dynamic UIs, open a page, click elements, type into fields,
        wait for selectors, and then read the resulting page text/metadata before concluding.

        Some of the many potential diagnostic topics that you could analyze:
            - SEO (search engine optimization)
            - Performance
            - Correctness / broken things in general
            - Accessibility
            - Code / repository-related
            - Content issues
        
        Website URL: {website_url}
        GitHub repository: {repo_name}

        When accessing the GitHub repository, always list the directory structure first
        before attempting to read specific files, so you know which paths exist.
        """
    ),
    MessagesPlaceholder("messages")
])

conclude_prompt = ChatPromptTemplate([
    (
        "system",
        """
        You are the final step of a friendly website quality assurance analyzer agent system.
        The analysis phase is fully complete. All tool calls you see in the message history
        have already been executed - do not attempt to call any tools yourself.
        Any submit_diagnostic tool calls in the history mean those diagnostics have already
        been saved. Your only job is to write a short, concise, human-readable summary of
        what was found and what actions were taken during analysis and answer any questions.
        It does not necessarily have to be a list or structured format — a few sentences is fine.
        It's possible the human simply asked a question. Then, answer the question.
        You are speaking on behalf of the entire QA analyzer agent system. Speak as if you are the
        entire website quality assurance analyzer system.
        You should always respond with some text.
        Do not reveal nor talk about database internals to the user (e.g. primary key ids).
        Your name is Webster. Be friendly.
        """
    ),
    MessagesPlaceholder("messages")
])

async def run_agent(messages: list[BaseMessage], website_url: str, repo_name: str, db_engine: Engine, website_entry_id: int, github_token: str) -> str:
    tools, cleanup = await get_tools(db_engine, website_entry_id, github_token)

    llm_analyze = ChatOpenAI(model="gpt-5.2").bind_tools(tools)
    llm_conclude = ChatOpenAI(model="gpt-5.2")

    def analyze(state: AgentState) -> AgentState:
        response = (analyze_prompt | llm_analyze).invoke({
            "messages": state["messages"],
            "website_url": state["website_url"],
            "repo_name": state["repo_name"],
        })
        return {"messages": response}

    def conclude(state: AgentState) -> AgentState:
        response = (conclude_prompt | llm_conclude).invoke({
            "messages": state["messages"]
        })
        return {"conclusion": response.content}

    def analyze_path(state: AgentState) -> Literal["tools", "conclude"]:
        if state["messages"][-1].tool_calls:
            return "tools"
        else:
            return "conclude"

    graph = StateGraph(AgentState)
    graph.add_node("analyze", analyze)
    graph.add_node("analyze_tools", ToolNode(tools, handle_tool_errors=True))
    graph.add_node("conclude", conclude)
    graph.add_edge(START, "analyze")
    graph.add_conditional_edges("analyze", analyze_path, {"tools": "analyze_tools", "conclude": "conclude"})
    graph.add_edge("analyze_tools", "analyze")
    graph.add_edge("conclude", END)

    agent = graph.compile()
    try:
        result = await agent.ainvoke({
            "messages": messages,
            "website_url": website_url,
            "repo_name": repo_name,
        })
    finally:
        await cleanup()

    return result["conclusion"]

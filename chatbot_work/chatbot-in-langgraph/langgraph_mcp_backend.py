from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool, BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
import aiosqlite
import requests
import asyncio
import threading

load_dotenv()


"""This code creates a dedicated asyncio event loop running in a separate background thread.

The main purpose is to allow synchronous Python code (like Streamlit) to execute asynchronous functions (coroutines) without creating a new event loop every time.

Let's understand it step by step.
1. Create an event loop
_ASYNC_LOOP = asyncio.new_event_loop()



- Creates a new asyncio event loop.
- An event loop manages and executes asynchronous tasks.
- At this point, the loop is created but not running.
Think of it as creating a workspace where asynchronous tasks will execute.
2. Create a separate thread
_ASYNC_THREAD = threading.Thread(    target=_ASYNC_LOOP.run_forever,    daemon=True)



Here:
- threading.Thread() creates a new thread.
- target=_ASYNC_LOOP.run_forever tells that thread what function to execute.
- run_forever() keeps the event loop running continuously.
- daemon=True means this background thread won't prevent Python from exiting when all non-daemon threads finish.
Then:
_ASYNC_THREAD.start()



Starts the thread.

Now your event loop is running continuously in the background.
Your application
Main thread

Synchronous Python / Streamlit code

Submit asynchronous tasks

Background thread
Async event loop

Runs continuously using run_forever()
Executes coroutines


3. Submit a coroutine
def _submit_async(coro):    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)



This is the most important part.

asyncio.run_coroutine_threadsafe():
- Takes an asynchronous coroutine.
- Schedules it on the specified event loop.
- Returns a concurrent.futures.Future object.
For example:
async def add(a, b):    await asyncio.sleep(2)    return a + bfuture = _submit_async(add(10, 20))



The coroutine is scheduled on the background event loop.

Notice: _submit_async() does not wait for the result. It returns a Future.
4. Wait for the result
def run_async(coro):    return _submit_async(coro).result()



Here, .result() is important.

It blocks the calling thread until the asynchronous task completes and returns its result.

Example:
result = run_async(add(10, 20))print(result)



Output:
30


The main thread waits for the result, while the coroutine executes in the background event-loop thread.
5. Submit without waiting
def submit_async_task(coro):    """Schedule a coroutine on the backend event loop."""    return _submit_async(coro)



Unlike run_async(), this function does not call .result().

Example:
future = submit_async_task(add(10, 20))



The task runs in the background. Your main thread can continue doing other work.

Later, you can retrieve the result:
result = future.result()



Difference between the three functions
Function	Behaviour
_submit_async()	Schedules coroutine and returns Future
run_async()	Schedules coroutine and waits for result
submit_async_task()	Schedules coroutine and returns Future without waiting

The key concept to understand:
- asyncio event loop = manages asynchronous execution.
- Thread = allows that event loop to run independently of the main thread.
- run_coroutine_threadsafe() = submits work to that event loop from another thread.
- .result() = waits until the submitted work finishes.
This pattern is particularly useful when your application has a synchronous frontend, such as Streamlit, but an asynchronous backend using LangGraph, MCP clients, or other async libraries.

One caution: don't call run_async() from the event-loop thread itself, because waiting on .result() there can deadlock."""
# Dedicated async loop for backend tasks
_ASYNC_LOOP = asyncio.new_event_loop()
_ASYNC_THREAD = threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True)
_ASYNC_THREAD.start()


def _submit_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)


def run_async(coro):
    return _submit_async(coro).result()


def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop."""
    return _submit_async(coro)


# -------------------
# 1. LLM
# -------------------
llm = ChatOpenAI()

# -------------------
# 2. Tools
# -------------------
search_tool = DuckDuckGoSearchRun(region="us-en")


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()


client = MultiServerMCPClient(
    {
        "arith": { ## name of MCP server
            "transport": "stdio", # yeh local server so standard i/o
            "command": "python3",# usko run bhi so command 
            "args": ["/Users/nitish/Desktop/mcp-math-server/main.py"], ## path to that server
        },
        "expense": {
            "transport": "streamable_http",  # if this fails, try "sse"
            "url": "https://splendid-gold-dingo.fastmcp.app/mcp"
        }
    }
)

## ab client bna liye to server se sare tool chaiye to sare tool ka list chaiye so 
def load_mcp_tools() -> list[BaseTool]: # list oif tools return so langgraph ke base tool ka list 
    try:
        return run_async(client.get_tools()) ## async so use run_async
    except Exception:
        return []

## uss function ko use krke load kr liye sara tools of mcp servers client is connected with 
mcp_tools = load_mcp_tools()

tools = [search_tool, get_stock_price, *mcp_tools] ## mcp server ka tools ko list me dalna hai to use *
llm_with_tools = llm.bind_tools(tools) if tools else llm

# -------------------
# 3. State
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# -------------------
# 4. Nodes
# -------------------
async def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call."""
    messages = state["messages"]
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(tools) if tools else None

# -------------------
# 5. Checkpointer
# -------------------

## see this is how sqilite works when we want async 
async def _init_checkpointer():
    conn = await aiosqlite.connect(database="chatbot.db")
    return AsyncSqliteSaver(conn)

# async sqlite ka aese checkpointer bnate hai 
checkpointer = run_async(_init_checkpointer())

# -------------------
# 6. Graph
# -------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")

if tool_node:
    graph.add_node("tools", tool_node)
    graph.add_conditional_edges("chat_node", tools_condition)
    graph.add_edge("tools", "chat_node")
else:
    graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)

# -------------------
# 7. Helper
# -------------------
async def _alist_threads():
    all_threads = set()
    async for checkpoint in checkpointer.alist(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def retrieve_all_threads():
    return run_async(_alist_threads())

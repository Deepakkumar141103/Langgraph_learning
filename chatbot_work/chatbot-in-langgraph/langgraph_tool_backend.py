# backend.py

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition## yeh help find which tool to call 
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from dotenv import load_dotenv
import sqlite3
import requests

load_dotenv()

# -------------------
# 1. LLM
# -------------------
llm = ChatOpenAI()

# -------------------
# 2. Tools
# -------------------
# Tools
search_tool = DuckDuckGoSearchRun(region="us-en")## yeh langgraph k inbuilt toll to bss load kiye import k baad 


## apna toll bna rhe ab so use @tool
# one import thing tool bnane waqt detail dalna shi se ussi se llm decide ki kaunsa llm call krna hai 
@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform a basic arithmetic operation on two numbers.
    Supported operations: add, sub, mul, div
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}
        
        return {"first_num": first_num, "second_num": second_num, "operation": operation, "result": result}
    except Exception as e:
        return {"error": str(e)}




@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch latest stock price for a given symbol (e.g. 'AAPL', 'TSLA') 
    using Alpha Vantage with API key in the URL.
    """
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey=C9PE94QUEW9VWGFM"
    r = requests.get(url)
    return r.json()


## tool bnane ke bad uska ek list bnao and llm se usko bind kr doo aese 
tools = [search_tool, get_stock_price, calculator]
llm_with_tools = llm.bind_tools(tools)

# -------------------
# 3. State
# -------------------
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

# -------------------
# 4. Nodes
# -------------------
def chat_node(state: ChatState):
    """LLM node that may answer or request a tool call.""" ## bss Fstring me bta doo ki llm tool bhi call kr skta if needed to message dekh kr decide kr lega 
    messages = state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

tool_node = ToolNode(tools) ## yeh tool ka function jo tool ko execute krta hai aese hi bnate hai agr alg alg bnana hai to har toolnode me list of tool bna kr pass kro ek bhi hai to usko bhi list me dalkr pass kro so this is the function behind tool which will execute tool 

# -------------------
# 5. Checkpointer
# -------------------
conn = sqlite3.connect(database="chatbot.db", check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

# -------------------
# 6. Graph
# -------------------
graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)

graph.add_edge(START, "chat_node")

## condtional edge bnana pdta hai agr alag alg tool node hai to hame condtional edge ko define krna pdega wrna ek hai to chatnode me state pass kiye uske bad woh message k sath invoke kiye to uske sath bind tools me se woh select krke toolnode ko pass kr dega jo uss tool ko execute krega 
graph.add_conditional_edges("chat_node",tools_condition) ## jis node se chahte hai ki decide ho kaunsa toll call ho to usse tools_condition ke beech me edge then uss node me jo llm invoke hua hoga uske sath jo tools bind hua hoga usme se woh select krke t
graph.add_edge('tools', 'chat_node')## yeh edge isliye diye as maybe multiple tool ki need to ek use kiye phir wapas llm dusre k call aese and also tool ka reply not user friendly so bss 

chatbot = graph.compile(checkpointer=checkpointer)
## aese krke bnate hai tool condition and condtion edge m bhi change aata hai 

#def check_tools(state: ChatState):
    #messages = state["messages"]
    #last_message = messages[-1]

    #if last_message.tool_calls:
        #return "tools"

    #return "response"

#graph.add_conditional_edges(
    #"chat_node",## chatnode se llm ne message me dala hoga tool call ya normal message to iss function  se check kr liye uss hisab se call to direct end pr nhi gya bss ho gya 
    #check_tools,
    #{
       #"tools": "tools",
        #"response": "response"
    #}
#)

# -------------------
# 7. Helper
# -------------------
def retrieve_all_threads():
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)

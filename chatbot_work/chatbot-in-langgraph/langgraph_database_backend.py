from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
import sqlite3 ## line 5 and line 8 use jab hum sqlite use krte hai as checkpinter
## ememory saver me jab hum page refdresh kr rhe the to ram se program hat kr wapas to thread id chla jata tha means sara checkpoint jo store kiye the woh gayab to khn se load krte 
load_dotenv()

llm = ChatOpenAI()

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {"messages": [response]}


##yeh hum use when sqllite as checkpoint use krte hai 
## yeh line agr databse nhi na hoga to same directory me ek databse bna dega and false isliye as bydefault sqlite single thread pr work krta hai to agr true to error deta isliye usse false kr diye 
conn = sqlite3.connect(database='chatbot.db', check_same_thread=False)
# Checkpointer
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)
graph.add_node("chat_node", chat_node)
graph.add_edge(START, "chat_node")
graph.add_edge("chat_node", END)

chatbot = graph.compile(checkpointer=checkpointer)

def retrieve_all_threads():
    all_threads = set() ## dekho checkppinter me sare threads k mulitple checkpoints as single enter pr hi 3 checkpoint for same thread islkite set use kiye taki single bar thread id aaye 
    for checkpoint in checkpointer.list(None): # yeh bhut kuch metadata deta hai to issliye aese niklna pd rha 
        all_threads.add(checkpoint.config['configurable']['thread_id'])

    return list(all_threads)



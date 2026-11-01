import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage
## ab hum chahte stream of message to uske liye graph ko invoke nhi stream se call krna pdta and woh return generator krta hai 
# st.session_state -> dict -> 
CONFIG = {'configurable': {'thread_id': 'thread-1'}}

if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

#{'role': 'user', 'content': 'Hi'}
#{'role': 'assistant', 'content': 'Hi=ello'}

user_input = st.chat_input('Type here')

if user_input:

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})
    with st.chat_message('user'):
        st.text(user_input)

    # first add the message to message_history
    with st.chat_message('assistant'):

        ai_message = st.write_stream( ## write stream se sdtream likhte hai 
            message_chunk.content for message_chunk, metadata in chatbot.stream(# usne generator return kiya so traverse in generator 
                {'messages': [HumanMessage(content=user_input)]},
                config= {'configurable': {'thread_id': 'thread-1'}},
                stream_mode= 'messages'
            )
        )
    ## ab ai message me pura ai message k content woh message history me append kr diye 
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
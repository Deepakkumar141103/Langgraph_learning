import streamlit as st
from langgraph_backend import chatbot
from langchain_core.messages import HumanMessage

# st.session_state -> dict -> 
CONFIG = {'configurable': {'thread_id': 'thread-1'}}
## jab refresh hoga to usme message history nhi hoga 
if 'message_history' not in st.session_state: ## to ab jab enter krenge tosession history m message history hoga as woh clzar nhi hota mesge history me mere pass data rha 
    st.session_state['message_history'] = [] ## jab page refresh hog to sesion bhi khali to naya usmwe message hisoty list bnba diya bss wahi bnaya hai yhn 
## deko jab mesagew krke enter krte hai to streamlit start se ode run krta hai to mssage history phirse khali wala ban jata hai to usse bachne ke liye we use session 
## yeh tab hi restart jab hum page ko refresh krenge



# now abjab bhi enter to purana sara chaiye to wahi show k rhe 
# loading the conversation history
for message in st.session_state['message_history']:
    with st.chat_message(message['role']): ## isse hum btate hai ki kaun sa message hai yeh ai ya user 
        st.text(message['content']) # phir uska content likh diya 

#{'role': 'user', 'content': 'Hi'}
#{'role': 'assistant', 'content': 'Hi=ello'}

user_input = st.chat_input('Type here')

if user_input: ## means agr kuch user input aaya means enter hua hoha kuch 

    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'user', 'content': user_input})## message history me data dal diye as list to append kiyue 
    with st.chat_message('user'):
        st.text(user_input)

    response = chatbot.invoke({'messages': [HumanMessage(content=user_input)]}, config=CONFIG)
    
    ai_message = response['messages'][-1].content
    # first add the message to message_history
    st.session_state['message_history'].append({'role': 'assistant', 'content': ai_message})
    with st.chat_message('assistant'):
        st.text(ai_message)
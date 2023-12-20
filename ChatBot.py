import streamlit as st
import yaml
import openai
import NetworkApproach.Strategy as Strategy

openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')
participants_list = []

with st.sidebar:
    part_1 = st.text_input("First participant", "Elon Musk", key="part_1_input")
    part_2 = st.text_input("First participant", "Karl Marx", key="part_2_input")
    if part_1 and part_2:
        participant_prompt = f"This will be a conversation between {part_1} and {part_2}."
        st.write(participant_prompt)
        participants_list.append(part_1)
        participants_list.append(part_2)

st.title("💬 Chatbot")
st.caption("🚀 A streamlit chatbot powered by OpenAI LLM")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": f"How can I help you?"}]

count = 0
if st.button("Continue", type="primary", key=f"con_button_{count}"):
    if count == 0:
        response_content_str = participant_prompt
    elif count == 1:
        response_content_str = None  # jep, das is nicht zu machen mit Streamlit, son Rotz
    count += 1
    response = Strategy.get_gpt_response(response_content_str)
    response_content_str = Strategy.get_response_content(response)
    st.chat_message({"role": "assistant", "content": response_content_str})

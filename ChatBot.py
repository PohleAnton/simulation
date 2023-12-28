import json

import streamlit as st
import yaml
import openai
import stepBackStuff.StepBackGeneration as SBG

openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')
participants_list = []

with st.sidebar:
    part_1 = st.text_input("First participant", "Elon Musk", key="part_1_input")
    part_2 = st.text_input("Second participant", "Karl Marx", key="part_2_input")
    if part_1 and part_2:
        participant_prompt = f"This will be a conversation between {part_1} and {part_2}."
        participants_list.append(part_1)
        participants_list.append(part_2)

st.title("💬 ConversationsBot")
st.caption("🚀 A streamlit bot powered by OpenAI LLM")
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "assistant", "content": f"How can I help you?"}]

assistant_mes = st.chat_message("assistant")
ai_mes = st.chat_message("ai")

if st.button("Start Conversation", type="primary", key="start_con_button"):
    SBG.fill_profile_schemes_for_participants(participants_list)
    prompt_for_first_conversation = SBG.prompt_p1 + SBG.join_profiles(participants_list)
    first_conversation_res = SBG.get_gpt_response(prompt_for_first_conversation)
    first_conversation_str = SBG.get_response_content(first_conversation_res)

    assistant_mes.write(participant_prompt)
    ai_mes.write(first_conversation_str)

    extracted_topics = SBG.extract_topics_of_conversation(first_conversation_res)
    for participant in participants_list:
        SBG.add_knowledge_to_profile(participant, extracted_topics)

    if st.button("Continue Conversation", type="primary", key="continue_con_button"):
        for participant in participants_list:
            new_theme = SBG.public_discussions.query(query_texts="Ideals")
            further = new_theme['metadatas'][0][0].get('theme')
            content = further = new_theme['documents'][0][0]
            response = SBG.form_argument('Elon Musk', 'State of Society', content)
            res = json.loads(response["choices"][0]["message"]["function_call"]["arguments"])

            assistant_mes.write(f"{participant} formulated an argument")
            ai_mes.write(res)
            # TODO: Conversation weiterführen, Knowledge speichern, Conversation auswerten

    if st.button("Random topic input for conversation", type="secondary", key="random_topic_input_button"):
        assistant_mes.write("What do you like to see the participants talking about in the next conversation?"
                            "Just enter the Topic!")
        given_topic = st.chat_input
        # TODO: dieses topic an die Conversation als zufälliges Element weiterleiten

# TODO: wie endet die Conversationskette? Userinput oder automatisch?

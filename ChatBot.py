import json
import os

import openai
import streamlit as st
import yaml

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
all_on_board = False

if st.button("Start Conversation", type="primary", key="start_con_button"):
    SBG.fill_profile_schemes_for_participants(participants_list)
    first_conversation_res = SBG.get_gpt_response(SBG.prompt_for_first_conversation)
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
        chosen_topic = st.chat_input
        loop_counter = 0
        pros = []
        contras = []
        while not all_on_board and not all_against:
            loop_counter += 1
            randomizer = []
            # um nicht die ursprüngliche liste zu überschreiben:
            if loop_counter == 1:
                for item in participants_list:
                    randomizer.append(item)
                # falls es mehr als 2 participants gibt, werden diese in pro und contra sortiert:
                for item in randomizer:
                    if 'yes' in SBG.judge_concivtion(item, chosen_topic).lower():
                        pros.append(item)
                    else:
                        contras.append(item)

            for speaker in pros:
                start_number = SBG.public_discussions.count() + 1
                speaker_argument = SBG.form_argument(speaker, chosen_topic, 'yes')
                print(speaker_argument)
                for listener in contras:
                    new_listener_conviction = SBG.argument_vs_conviction(speaker_argument, listener, chosen_topic)
                    print(new_listener_conviction)
                SBG.public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                           metadatas={'theme': chosen_topic, 'issue': SBG.get_yes_or_no(chosen_topic)})

            for listener in contras:
                if 'yes' in SBG.judge_concivtion(listener, chosen_topic).lower():
                    contras.remove(listener)
                    pros.append(listener)
                listener_argument = SBG.form_argument(listener, chosen_topic, 'no')
                print(listener_argument)
                for speaker in pros:
                    new_speaker_conviction = SBG.argument_vs_conviction(listener_argument, speaker, chosen_topic)
                SBG.public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                           metadatas={'theme': chosen_topic, 'issue': SBG.get_yes_or_no(chosen_topic)})

            for speaker in pros:
                if 'no' in SBG.judge_concivtion(speaker, chosen_topic).lower():
                    pros.index(speaker)
                    contras.append(speaker)

            # #in Form von: {speaker} says: (Damit der Name zwar im Frontend, aber nicht im eigentlichen Prompt
            # auftaucht) {argument}
            new_listener_conviction = SBG.argument_vs_conviction(speaker_argument, listener, chosen_topic)

            all_on_board, all_against = SBG.lets_goooooo(participants_list, chosen_topic)
            if loop_counter > 2:
                break

        if loop_counter < 4:
            # video_path=''
            print('magic')
            if all_on_board:
                x = 0  # os.system("shutdown /s /t 1")
            if all_against:
                print('')
                # os.startfile(video_path)
        else:
            print('no magic')

# TODO: wie endet die Conversationskette? Userinput oder automatisch?

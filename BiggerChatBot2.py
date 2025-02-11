import json
import random
from datetime import datetime
from pathlib import Path

import chromadb
import openai
import streamlit as st
import yaml
from chromadb.utils import embedding_functions
from sqlalchemy.testing.plugin.plugin_base import logging

# Dieses Skript kombiniert OpenAI, Streamlit und ChromaDB, um ein interaktives System für die Generierung und Verwaltung
# von Diskussionen zu erstellen. Es ermöglicht Nutzern, durch Streamlit-basierte Oberfläche, Gespräche zwischen verschiedenen
# Teilnehmern zu simulieren und zu steuern. Hauptmerkmale des Skripts beinhalten:
# - Erzeugung von Diskussionsthemen und Teilnehmerprofilen mithilfe der OpenAI-API.
# - Speicherung und Abfrage von Diskussionsinhalten und Teilnehmerinformationen in ChromaDB.
# - Streamlit-Interface für die Nutzerinteraktion, um Diskussionen zu starten, zu steuern und zu beenden.
# - Dynamische Generierung von Gesprächsinhalten basierend auf Benutzereingaben und vordefinierten Kriterien.
# - Erweiterte Funktionen für Textanalyse und -verarbeitung, einschließlich der Extraktion von Kernthemen und Überzeugungen.
# Das Skript demonstriert eine innovative Nutzung von KI-Technologien und Datenbankmanagement zur Erstellung eines
# interaktiven und dynamischen Diskussionssimulators.



openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')
model = "gpt-3.5-turbo-1106"
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai.api_key,
    model_name="text-embedding-ada-002"
)

#chroma = chromadb.HttpClient(host='localhost', port=8000, tenant="default_tenant", database='default_database')
chroma = chromadb.HttpClient(host='server', port=8000, tenant="default_tenant", database='default_database')

@st.cache
def get_file_content_or_fetch_from_gpt(file_name, prompt, extract_function_name):
    dir_name = './FilesForDocker'
    current_dir = Path(__file__).parent
    dir_path = current_dir / dir_name
    file_path = dir_path / file_name

    dir_path.mkdir(parents=True, exist_ok=True)

    if file_path.exists():
        with open(file_path, 'r') as file:
            return file.read()

    response = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user",
                   "content": f"{extract_function_name} from {response['choices'][0]['message']['content']}"}],
        functions=functions
    )

    try:
        points_json = json.loads(raw)
    except json.JSONDecodeError:
        points_json = json.dumps(raw)

    points = points_json['headings']
    with open(file_path, 'w') as file:
        file.write(points)

    return points

@st.cache
def get_or_create_collection(client, collection_name, embedding_function=None):
    try:
        return client.get_collection(name=collection_name)
    except Exception as e:
        if embedding_function:
            return client.create_collection(name=collection_name, embedding_function=embedding_function)
        else:
            return client.create_collection(name=collection_name)


if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []

def append_to_chat(role, content):
    """ Fügt eine Nachricht dem Chatverlauf hinzu """
    st.session_state['chat_history'].append({'role': role, 'content': content})

def display_chat():
    """ Zeigt den gesamten Chatverlauf an """
    for message in st.session_state['chat_history']:
        with st.chat_message(message['role']):
            st.markdown(message['content'])

def handle_user_input(user_input, participants_list):
    # Füge die Benutzereingabe dem Chatverlauf hinzu
    append_to_chat("user", user_input)

    if user_input.lower() == "start":
        start_conversation(participants_list)
    elif user_input.lower() == "end":
        end_conversation()
        return  # Beendet die Interaktion
    else:
        next_conversation(user_input, participants_list)

    # Zeigt den aktualisierten Chatverlauf an
    display_chat()



public_discussions = get_or_create_collection(chroma, "public_discussions", openai_ef)
participant_collection = get_or_create_collection(chroma, "participants")
prior_themes_collection = get_or_create_collection(chroma, "prior_themes_collection")

# Initialisierung von Streamlit-State-Variablen
if 'first_finished' not in st.session_state:
    st.session_state['first_finished'] = False
if 'all_topics' not in st.session_state:
    st.session_state['all_topics'] = []
if 'all_on_board' not in st.session_state:
    st.session_state['all_on_board'] = False
if 'all_against' not in st.session_state:
    st.session_state['all_against'] = False

# Laden von Themen in st.session_state['all_topics']
if prior_themes_collection:
    theme_count = prior_themes_collection.count()
    if theme_count > 0:
        themes = prior_themes_collection.query(query_texts="any", n_results=theme_count)
        if 'metadatas' in themes:
            for item in themes:
                if isinstance(item, list):
                    for sub_item in item:
                        if 'theme' in sub_item:
                            st.session_state['all_topics'].append(sub_item['theme'])

criteria_prompt = ("Assume 2 people are having an intense intellectual conversation about a controversial topic. "
                   "Both of them start out with a strong conviction. Both are capable of changing their mind gradually. "
                   "Both can make good arguments. What criteria of the actual argument might help to convince them or "
                   "move their conviction a litte?")

strategies_prompt = ("What strategies might one pick to form a convincing argument?")

functions = [
    {
        "name": "extract_core_issue",
        "description": "A function that identifies the core question of topic and poses the appropriate Yes-Or-No Question",
        "parameters": {
            "type": "object",
            "properties": {
                "core_issue": {
                    "type": "string",
                    "description": "The Yes-Or-No Question at the heart of the topic"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "extract_headings",
        "description": "A function that extracts only the headings from a list of bullet points in a given text.",
        "parameters": {
            "type": "object",
            "properties": {
                "headings": {
                    "type": "string",
                    "description": "The bullet-point headings ONLY, without any accompanying explanations"
                }
            }
        }
    },
    {
        "name": "find_topics",
        "description": "A function that finds broad subtitles for each theme that was brought up in a conversation. It limits the number of subtitles to four or fewer, ensuring they are broad and encompassing, while considering the entire text",
        "parameters": {
            "type": "object",
            "properties": {
                "themes": {
                    "type": "array",
                    "description": "A list of all the themes that came up",
                    "items": {
                        "type": "string",
                        "description": "Each theme that has been brought up - what the most fitting Wikipedia-article might be called"
                    }
                }
            }
        }
    },
    {
        "name": "split_conversation",
        "description": "Splits a conversation into parts that discuss given topics, with each part including at lest 300 characters of context in each direction around it. The function ensures that the entire conversation is included in the output, with overlapping content where necessary to provide context.",
        "parameters": {
            "type": "object",
            "properties": {
                "themes": {
                    "type": "array",
                    "description": "This is a list of topics or themes. The function will use these topics to divide the conversation into relevant parts. Overlapping of conversation parts is allowed to ensure full coverage and context.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "theme": {
                                "type": "string",
                                "description": "Represents a specific topic around which a part of the conversation will be organized."
                            },
                            "content": {
                                "type": "string",
                                "description": "This is the actual segment of the conversation that pertains to the given topic, including at least 300 characters of context in each direction. This ensures that the conversation parts are coherent and understandable even when taken out of the larger conversation."
                            }
                        }
                    }
                },
            },
            "required": ["conversation", "themes"]
        }
    },
    {
        "name": "create_conviction",
        "description": "A function that generates the likely inner thoughts of a participant about a subject",
        "parameters": {
            "type": "object",
            "properties": {
                "conviction": {
                    "type": "string",
                    "description": "Use first-person pronouns only, Inner most believe of a participant about a subject. Radical, emotional and subjective. Do not mention the name of the participant"
                }
            }
        }
    },
    {
        "name": "update_conviction",
        "description": "A function that describes the inner thoughts of a participant about a subject based on prior convictions and new arguments",
        "parameters": {
            "type": "object",
            "properties": {
                "conviction": {
                    "type": "string",
                    "description": "Use first-person pronouns only,. New description of inner most thoughts about a subject. Based on prior conviction and arguments. Can be more nuanced and subtle. Do not mention the name of the participant"
                }
            },
            "required": ["participant", "subject", "prior conviction", "arguments"]
        }
    },
    {
        "name": "form_argument",
        "description": "A function that generates a convincing argument about a topic based on conviction and a strategy. Should be as convincing as possible.  ",
        "parameters": {
            "type": "object",
            "properties": {
                "argument": {
                    "type": "string",
                    "description": "An argument someone might make to convince somebody of the truth or importance of the subject"
                                   "Meant to be convincing. Based on a given strategy, maybe including prior discussion."
                }
            },
            "required": ["strategy", "conviction", "prior discussion", "topic"]
        }
    },
    {
        "name": "form_counterargument",
        "description": "A function that generates a convincing argument about the falsehood of an idea or topic based on conviction and a strategy. Should be as convincing as possible.  ",
        "parameters": {
            "type": "object",
            "properties": {
                "argument": {
                    "type": "string",
                    "description": "An argument someone might make to convince somebody of the a certain idea is false."
                                   "Meant to be convincing. Based on a given strategy, maybe including prior discussion."
                }
            },
            "required": ["strategy", "conviction", "prior discussion", "topic"]
        }
    }
]


def read_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content


def get_gpt_response(content):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": content}
            ]
        )
        return response
    except Exception as e:
        st.error(f"Fehler beim Abrufen der GPT-Antwort: {e}")
        return None


def get_response_content(given_response):
    return given_response.choices[0].message.content


def fill_profile_schemes_for_participants(participants):
    for participant in participants:
        start_number = 1 if participant_collection.count() == 0 else participant_collection.count() + 1
        input_content = profile_scheme + " for " + participant
        response = get_gpt_response(input_content)
        profile = get_response_content(response)
        participant_collection.add(documents=profile, metadatas={'name': participant}, ids=str(start_number))


def join_profiles(participants):
    profiles_of_participants = ""
    for participant in participants:
        profiles_of_participants += participant_collection.get(where={'name': participant})['documents'][0]
        profiles_of_participants += "\n\n"
    return profiles_of_participants

#vorerst deprecated. bleibt hier. safety first
# def compare_themes(prior_topic, new_topics):
#
#     updated_topics = []
#     for new in new_topics:
#         replaced = False
#         for prior in prior_topic:
#             judge = openai.ChatCompletion.create(
#                 model=model,
#                 messages=[
#                     {"role": "system",
#                      "content": "You compare 2 Strings and asses if they refer to the same concept. You only answer yes or no"},
#                     {"role": "user",
#                      "content": f"Does {prior} mean the same thing as {new}"}
#                 ],
#             )
#             if 'Yes' in judge['choices'][0]['message']['content'] or 'yes' in judge['choices'][0]['message']['content']:
#                 updated_topics.append(prior)
#                 replaced = True
#
#         if not replaced:
#             updated_topics.append(new)
#     return updated_topics


def get_gpt_response_with_function(content, functions):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": content}
            ],
            functions=functions
        )
        return response
    except Exception as e:
        st.error(f"Fehler beim Abrufen der GPT-Antwort mit Funktionen: {e}")
        logging.error(f"Fehler beim Abrufen der GPT-Antwort mit Funktionen: {e}")
        return None



def extract_timestamp(s):
    timestamp_str = s[-19:]
    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')


def get_latest_conviction_id(participant, topic):
    # print(f"HOLE ID DER ÜBERZEUGUNG für: {participant} zu {topic}")
    collection_name = participant.replace(' ', '') + 'Conviction'
    collection = None
    for collection_db in chroma.list_collections():
        if collection_db.name == collection_name:
            try:
                collection = collection_db.get(where={'theme': topic})
            except KeyError:
                print(f"KeyError beim Zugriff auf die Collection")
            break
    try:
        if collection['ids'][0]:
            ids = collection['ids']
            latest = max(ids, key=extract_timestamp)
            return latest
    except KeyError:
        print(f"KeyError beim Zugriff auf die Collection")
        return None


def get_latest_conviction(participant, topic):
    collection_name = participant.replace(' ', '') + 'Conviction'
    try:
        id = get_latest_conviction_id(participant, topic)
        if id:
            last_conviction = st.session_state['collections'][collection_name].get(ids=[id])
            return last_conviction['documents'][0]
        else:
            return ''
    except IndexError:
        return ''
    except KeyError:
        print(f"KeyError aufgetaucht bei: {collection_name}")
        return ''


def get_structured_conversation_with_gpt(given_conversation):
    vector_test = get_gpt_response_with_function('find_topics'
                                                 + get_response_content(given_conversation),
                                                 functions)

    content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
    try:
        structured_data = json.loads(content)
    except json.decoder.JSONDecodeError:
        structured_data = json.dumps(content)
    return structured_data


def write_conviction_collection(participant, topic, arguments=''):
    # Konsolidierung der Funktionalität von 'create_conviction' und 'update_conviction'
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Überprüfe, ob die Sammlung existiert und hole die letzte Überzeugung
    collection = get_or_create_collection(chroma, collection_name)
    conv = get_latest_conviction(participant, topic)

    if conv == '' or arguments != '':
        # 'update_conviction' falls Überzeugung existiert und Argumente gegeben sind
        # oder 'create_conviction' falls keine Überzeugung existiert
        function_call_name = 'update_conviction' if conv != '' else 'create_conviction'
        res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user",
                 "content": f"{function_call_name} for {participant} about subject {topic}. {arguments if arguments else ''}"}
            ],
            functions=functions,
            function_call={'name': function_call_name}
        )
        result = res["choices"][0]["message"]["function_call"]["arguments"]
        res_json = json.loads(result)
        final = make_first_person(res_json['conviction'])
    else:
        # Keine Änderung notwendig, da keine Argumente gegeben und Überzeugung bereits vorhanden
        final = conv

    # Füge die neue oder aktualisierte Überzeugung zur Sammlung hinzu
    collection.add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)


def safety_conviction(participant, topic):
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        res = openai.ChatCompletion.create(
            model=model,  # Verwende das im Rest des Codes definierte Modell
            messages=[
                {"role": "user", "content": f"create_conviction for {participant} subject {topic}."}
            ],
            functions=functions,
            function_call={'name': 'create_conviction'}
        )
        result = res["choices"][0]["message"]["function_call"]["arguments"]
        res_json = json.loads(result)
        final = make_first_person(res_json['conviction'])  # Sicherstellen, dass es in erster Person ist

        # Verwende get_or_create_collection für Konsistenz
        conviction_collection = get_or_create_collection(chroma, collection_name)
        conviction_collection.add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Fehler bei der Erstellung der Überzeugung für {participant} zum Thema {topic}: {e}")
    # maybe this:
    # chroma.get_collection(collection_name)
    # globals()[collection_name].add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)


@st.cache
def find_core_issues(topic):
    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[{"role": "user", "content": f"extract_core_issue from {topic}"}],
            functions=functions,
            function_call={'name': 'extract_core_issue'}
        )

        arguments_json = response['choices'][0]['message']['function_call']['arguments']

        parsed_arguments = json.loads(arguments_json)
        core_issue = parsed_arguments.get('core_issue', None)

        if core_issue is None:
            raise ValueError(f"Kernthema wurde nicht gefunden in der Antwort für das Thema '{topic}'")

        return core_issue

    except (KeyError, json.JSONDecodeError, ValueError) as e:
        print(f"Fehler bei der Suche nach dem Kernthema für das Thema '{topic}': {e}")
        return None



# Sucht sich die Themen der Conversation zusammen
@st.cache
def extract_topics_of_conversation(given_conversation):
    conversation_topics = []
    chroma_metadatas = []
    chroma_documents = []
    chroma_ids = []
    # zum token sparen wird mitunter direkt string übergeben:
    if isinstance(given_conversation, str):
        text = given_conversation
        vector_test = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": f"find_topics in {given_conversation}"},
            ],
            functions=functions,
            function_call={'name': 'find_topics'}
        )
        content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
        try:
            structured_data = json.loads(content)
        except json.decoder.JSONDecodeError:
            structured_data = json.dumps(content)
        given_topics = ', '.join(structured_data['themes'])
    else:
        text = get_response_content(given_conversation)
        topics = get_structured_conversation_with_gpt(given_conversation)
        given_topics = ', '.join(topics['themes'])
    start_number = 1 if public_discussions.count() == 0 else public_discussions.count() + 1

    data = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user",
             "content": f"split_conversation {text} for topics {given_topics}"}
        ],
        functions=functions,
        function_call={'name': 'split_conversation'}
    )
    data = data['choices'][0]['message']['function_call']['arguments']
    try:
        new_data = json.loads(data)
    except json.decoder.JSONDecodeError:
        new_data = json.dumps(data)

    if not st.session_state['first_finished']:
        for theme in new_data["themes"]:
            #das ist für den Fall, dass man das Chroma-Volume nicht jedes mal löscht: In dem falle wird in den vergangenen
            #Konversationen nach ähnlichen Themen geschaut und diese werden gleichgesetzt, sodass auf mehr memory Stream
            #zugegriffen werden kann. dies ist aber token intensiv und braucht relativ viele API calls, sollte also wenigstens
            #beim entwickeln vermiedern werden
            for prior_topic in st.session_state['all_topics']:
                judge = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system",
                         "content": "You compare 2 Strings and assess if they refer to the same concept. You only answer yes or no"},
                        {"role": "user",
                         "content": f"Does {prior_topic} mean the same thing as {theme['theme']}"}
                    ],
                )
                if 'yes' in judge['choices'][0]['message']['content'].lower():
                    theme['theme'] = prior_topic
                    break
            conversation_topics.append(theme['theme'])
            chroma_ids.append(start_number)
            start_number += 1
            chroma_documents.append(theme['content'])
            chroma_metadatas.append({'theme': theme['theme'], 'issue': find_core_issues(theme['theme'])})

        chroma_ids = [str(id) for id in chroma_ids]
        public_discussions.add(documents=chroma_documents, metadatas=chroma_metadatas, ids=chroma_ids)
        st.session_state['first_finished'] = True

        return conversation_topics

        #notiz: es gab hier noch einen block
        #if st.session_state['first_finished']: dieser wird aber im aktuellen setup nicht mehr benötigt




def add_knowledge_to_profile(participant, given_topics):
    #ist ein Überbleibsel aus komplexerem Code,.
    for topic in given_topics:
        write_conviction_collection(participant, topic)


def get_yes_or_no(topic):
    n = public_discussions.get(where={'theme': topic})
    t = n['metadatas'][0]['issue']
    return t


def query_public_discussions(query, results=10, precision=0.4):
    """
       Queries the public discussions database and returns a specified number of results.

       This function executes a query on the public discussions database using the provided query text.
       The number of results to return is specified by the 'results' parameter, with a default value of 1.
       Careful - throws exception when too many documents are requested

       Args:
           query (str): The query text to be used for searching the public discussions.
           results (int, optional): The number of results to return. Defaults to 1 if not specified.

       Returns:
           list: A list of results from the public discussions database based on the query.
       """
    result = public_discussions.query(query_texts=query, n_results=results)
    return result


@st.cache
def get_best_document(topic, precise=False, precision=0.4):
    r = public_discussions.query(query_texts=topic)
    if precise:
        filtered_documents = []
        for distance, document in zip(r['distances'][0], r['documents'][0]):
            if distance < precision:
                filtered_documents.append(document)
        return filtered_documents
    else:
        return r['documents']


@st.cache
def get_prior_discussion(topic):
    # ToDo: Note to self: Vielleicht kann ich die query public discussions Methoden zusammenschrumpfen. Noch sind sie einzeln. Man weiß ja nie...
    r = get_best_document(topic, True, 0.4)
    combined_string = "\n".join(r) if len(r) > 1 else r[0]
    return combined_string


def form_argument(speaker, chosen_topic, believe):
    strategy = get_file_content_or_fetch_from_gpt('Strategies.txt', strategies_prompt, "extract_headings")
    speaker_conviction = get_latest_conviction(speaker, chosen_topic)
    prior_discussions = get_prior_discussion(chosen_topic)

    function_call_name = 'form_argument' if 'yes' in believe.lower() else 'form_counterargument'
    argument_prompt = f"{function_call_name} using one or more of these techniques: {strategy} about {chosen_topic} based on {speaker_conviction}. This was said before:{prior_discussions}"

    speaker_argument = openai.ChatCompletion.create(
        model=model,
        messages=[{"role": "user", "content": argument_prompt}],
        functions=functions,
        function_call={'name': function_call_name}
    )

    try:
        argument_string = speaker_argument['choices'][0]['message']['function_call']['arguments']
        arg_json = json.loads(argument_string)
        return arg_json.get('argument', 'No argument generated.')
    except (json.JSONDecodeError, KeyError):
        return "An error occurred while generating the argument."


def judge_concivtion(participant, topic):
    try:
        iss = public_discussions.get(where={'theme': topic})
        issue = iss.get('metadatas', [{}])[0].get('issue')
        if not issue:
            return f"Issue not found for the topic '{topic}'."

        conv = get_latest_conviction(participant, topic)
        if not conv:
            return f"No conviction found for {participant} on the topic '{topic}'."

        judge = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system",
                 "content": "you are a binary judge that answers questions only with yes or no. You only say yes when you are REALLY convinced"},
                {"role": "user",
                 "content": f"Based on this conviction: {conv}, how would you answer {issue}?"}
            ],
        )
        return judge['choices'][0]['message']['content']
    except Exception as e:
        return f"An error occurred: {str(e)}"



def score_conviction(participant, topic):
    try:
        iss = public_discussions.get(where={'theme': topic})
        issue = iss.get('metadatas', [{}])[0].get('issue')
        if not issue:
            return f"Issue not found for the topic '{topic}'."

        conv = get_latest_conviction(participant, topic)
        if not conv:
            return f"No conviction found for {participant} on the topic '{topic}'."

        judge = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You only answer with a number"},
                {"role": "user",
                 "content": f"Based on {conv}, answer {issue} and rate it on a scale from 1 - 100, 1 meaning not convinced at all, 100 being totally convinced"}
            ]
        )
        return judge['choices'][0]['message']['content']
    except Exception as e:
        return f"An error occurred: {str(e)}"



def update_conviction(participant, topic, new_conviction):
    if not new_conviction or not topic:
        return "Conviction or topic cannot be empty."

    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    collection = get_or_create_collection(chroma, collection_name)

    try:
        collection.add(documents=new_conviction, metadatas={'theme': topic}, ids=topic + timestamp_string)
        return f"Conviction updated for {participant} on topic '{topic}'."
    except Exception as e:
        return f"An error occurred while updating conviction: {str(e)}"



def argument_vs_conviction(argument, listener, chosen_topic):
    # Überprüfen, ob das Argument und die Überzeugung gültig sind
    if not argument:
        return "Das Argument darf nicht leer sein."

    con = get_latest_conviction(listener, chosen_topic)
    if not con:
        return f"Keine vorhandene Überzeugung für {listener} zum Thema '{chosen_topic}' gefunden."

    list = get_file_content_or_fetch_from_gpt('ConvincingFactors.txt', criteria_prompt, "extract_headings")

    try:
        judge = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system",
                 "content": f"Sie bewerten ein Argument auf Basis von {list} und passen eine vorherige Überzeugung entsprechend an."},
                {"role": "user",
                 "content": f"Bewerten Sie dieses Argument: {argument} und formulieren Sie {con} entsprechend um. Schreiben Sie nur in der ersten Person."}
            ]
        )
        ans = judge['choices'][0]['message']['content']
        update_conviction(listener, chosen_topic, ans)
        return ans
    except Exception as e:
        return f"Ein Fehler ist aufgetreten: {str(e)}"



def lets_goooooo(participants, chosen_topic):
    all_on_board = True
    all_against = True

    for participant in participants:
        res = judge_concivtion(participant, chosen_topic)

        if 'no' in res.lower():
            all_on_board = False
            if not all_against:
                break  # Frühzeitiger Abbruch, da das Ergebnis feststeht
        elif 'yes' in res.lower():
            all_against = False
            if not all_on_board:
                break  # Frühzeitiger Abbruch, da das Ergebnis feststeht
        else:
            # Fehlerbehandlung für den Fall, dass judge_concivtion keinen klaren 'yes' oder 'no' Wert zurückgibt
            print(f"Unerwartete Antwort von judge_concivtion: {res}")
            return False, False

    return all_on_board, all_against


# selbst gpt-4 schreibt nicht zuverlässig in der 1. person - dies ist aber vonnöten, um die überzeugungen von der person lösen zu können
def make_first_person(conviction):
    # Sidenote: There was a suprising amount of step back prompting involved to get this.
    # consider this: https://chat.openai.com/share/7483b007-f019-45bd-9365-65e06f69d478
    judge = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "you are a binary judge that answers questions only with yes or no."},
            {"role": "user",
             "content": f"Does the text only use first-person pronouns (e.g., I, my, me) to express the perspective and beliefs, without any references to other individuals or third-person statements: {conviction}?"}
        ],
    )
    response = judge['choices'][0]['message']['content']
    if 'no' in response or 'No' in response:
        rewrite = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user",
                 "content": f"rewrite this text using first-person pronouns only: {conviction}"
                 }
            ]
        )
        conviction = rewrite['choices'][0]['message']['content']
    return conviction


def classify_participants(participants, topic):
    pros = []
    contras = []
    for participant in participants:
        if 'yes' in judge_concivtion(participant, topic).lower():
            pros.append(participant)
        else:
            contras.append(participant)
    return pros, contras

def update_discussions_and_convictions(argument, listeners, topic, stance):
    for listener in listeners:
        new_conviction = argument_vs_conviction(argument, listener, topic)
        update_conviction(listener, topic, new_conviction)
        add_argument_to_public_discussions(argument, topic, stance)

def add_argument_to_public_discussions(argument, topic, stance):
    start_number = public_discussions.count() + 1
    public_discussions.add(documents=argument, ids=str(start_number),
                           metadatas={'theme': topic, 'issue': get_yes_or_no(topic), 'stance': stance})

def update_positions(pros, contras, topic):
    updated_pros = pros[:]
    updated_contras = contras[:]

    for speaker in pros:
        if 'no' in judge_concivtion(speaker, topic).lower():
            updated_pros.remove(speaker)
            updated_contras.append(speaker)

    for listener in contras:
        if 'yes' in judge_concivtion(listener, topic).lower():
            updated_contras.remove(listener)
            updated_pros.append(listener)

    return updated_pros, updated_contras

def handle_conversation_outcome(loop_counter):
    if loop_counter < 4:
        print('Ergebnis der Konversation wurde innerhalb von 4 Durchläufen erreicht.')
        # Weitere Logik hier, falls nötig
    else:
        print('Keine Einigung nach 4 Durchläufen.')

def next_conversation(participants_list, given_chosen_topic=""):
    loop_counter = 0
    pros, contras = classify_participants(participants_list, given_chosen_topic)

    while not (st.session_state['all_on_board'] or st.session_state['all_against']) and loop_counter < 4:
        loop_counter += 1
        process_arguments(pros, contras, given_chosen_topic)
        pros, contras = update_positions(pros, contras, given_chosen_topic)
        st.session_state['all_on_board'], st.session_state['all_against'] = lets_goooooo(participants_list, given_chosen_topic)

    handle_conversation_outcome(loop_counter)


def process_arguments(pros, contras, topic):
    for group, stance in [(pros, 'yes'), (contras, 'no')]:
        for participant in group:
            argument = form_argument(participant, topic, stance)
            update_discussions_and_convictions(argument, contras if stance == 'yes' else pros, topic, stance)




profile_scheme = read_from_file('./FilesForDocker/scheme.txt')

prompt = (
    "Write a conversation with the following setup: "
    "1. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
    "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "2. Long and detailed conversation. "
    "3. Topics: At least two subjects in their interest. If the simulation hypothesis comes up, focus on that"
    "4. Setting: At the beach. Everybody is relaxed "
    "5. Topic: The Simulation Hypothesis and its implications"
    "6. Involved Individuals: "
)


def start_first_conversation():
    fill_profile_schemes_for_participants(participants_list)
    prompt_for_first_conversation = prompt + join_profiles(participants_list)
    first_conversation_res = get_gpt_response(prompt_for_first_conversation)
    first_conversation_str = get_response_content(first_conversation_res)

    extracted_topics = extract_topics_of_conversation(first_conversation_res)
    for participant in participants_list:
        add_knowledge_to_profile(participant, extracted_topics)

    return first_conversation_str, extracted_topics


# falls alle die gleich überzeugung haben, generiert dies solange neue überzeugungen, bis das nicht der fall ist...ich kommentiere es vorerst aus, weil hier ggf gpt-4 benutzt werden soll...
# while all_on_board or all_against:
#     for participant in initial_participants:
#         safety_conviction(participant, token_saver_topics)
#         all_on_board , all_against = lets_goooooo(initial_participants, token_saver_topics)


# --------------------------------------- Steamlit ab hier ---------------------------------------

def start_conversation(participants_list):
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        first_conv_str, extracted_topics = start_first_conversation(participants_list)
        message_placeholder.markdown(first_conv_str)


def handle_user_input(user_input, participants_list):
    if user_input.lower() == "start":
        start_conversation(participants_list)
    elif user_input.lower() == "end":
        end_conversation()  # Eine Funktion, die definiert, was bei "End" passieren soll
    else:
        next_conversation(user_input)


def end_conversation():
    with st.chat_message("assistant"):
        st.markdown("Die Konversation wurde beendet.")


# Haupt-Streamlit-Code
participants_list = []

# ...

# Haupt-Streamlit-Code
# ...

with st.sidebar:
    part_1 = st.text_input("First participant", "Elon Musk", key="part_1_input")
    part_2 = st.text_input("Second participant", "Karl Marx", key="part_2_input")
    if part_1 and part_2:
        participants_list = [part_1, part_2]

st.title("💬 ConversationsBot")
st.caption("🚀 A streamlit bot powered by OpenAI LLM")

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"
if "messages" not in st.session_state:
    st.session_state.messages = []

with st.chat_message("assistant"):
    st.markdown("Bitte geben Sie \"Start\" ein, um ein Gespräch zu beginnen. "
                "Geben Sie ein Thema ein, um das Gespräch fortzusetzen, "
                "und \"End\", um das Gespräch zu beenden.")

if user_input_prompt := st.chat_input("Enter here..."):
    handle_user_input(user_input_prompt, participants_list)



# TODO: wie endet die Conversationskette? Userinput oder automatisch?

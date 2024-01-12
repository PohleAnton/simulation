import json
import random
from datetime import datetime
from pathlib import Path
import os
import platform
import subprocess
import chromadb
import openai
import streamlit as st
import yaml
from chromadb.utils import embedding_functions
from sqlalchemy.testing.plugin.plugin_base import logging

openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')
model = "gpt-3.5-turbo-1106"
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai.api_key,
    model_name="text-embedding-ada-002"
)

chroma = chromadb.HttpClient(host='localhost', port=8000, tenant="default_tenant", database='default_database')


#chroma = chromadb.HttpClient(host='server', port=8000, tenant="default_tenant", database='default_database')


def reset_session_state():
    """Clears all keys and values from the session state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def get_or_create_collection(client, collection_name, selector):
    """
        Retrieves an existing collection by name or creates a new one based on the selector.


        Args:
            client: The database client used to interact with collections.
            collection_name (str): The name of the collection to retrieve or create.
            selector (int): The selector determines the distance function - only relevant for the public_discussion

        Returns:
            The retrieved or newly created collection.
        """
    try:
        return client.get_collection(name=collection_name)
    except Exception as e:
        if selector == 1:
            return client.create_collection(name=collection_name, metadata={"hnsw:space": "ip"})
        else:
            return client.create_collection(name=collection_name)


def get_or_create_collection_with_session(client, collection_name, selector):
    """
        Retrieves or creates a collection from the client and puts it into the session state.
        Is needed for streamlit, so the collection actually gets updated


        Args:
            client: The database client used to interact with collections.
            collection_name (str): The name of the collection to retrieve or create.
            selector (int): Determines the method of collection creation. Defaults to 2.

        Returns:
            Updated session state
        """
    key = collection_name
    if key not in st.session_state['collections']:
        st.session_state['collections'][key] = get_or_create_collection(client, collection_name, selector)
    else:
        # Sammlung bereits im Session-State, aktualisiere ihre Informationen
        try:
            # Versuche, den aktuellen Zustand der Sammlung zu erhalten
            updated_collection = client.get_collection(name=collection_name)
            st.session_state['collections'][key] = updated_collection
        except Exception as e:
            st.error(f"Fehler beim Aktualisieren der Sammlungsinformationen: {e}")

    return st.session_state['collections'][key]




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
    """
        Processes user input in a chat application, updating the session state and conversation flow.

        Args:
            user_input (str): The input provided by the user.
            participants_list (list): The list of participants in the conversation.
        """
    if 'participants_list' in st.session_state:
        participants_list = st.session_state['participants_list']

    append_to_chat("user", user_input)

    if user_input.lower() == "start":
        # Überprüfe und aktualisiere notwendige Daten vor dem Start
        st.session_state['chat_history'] = []
        start_conversation(participants_list)
    elif user_input.lower() == "end":
        end_conversation()
    else:
        next_conversation(participants_list, user_input)

    display_chat()

    st.session_state['participants_list'] = participants_list


# Initialisierung von Streamlit-State-Variablen
if 'first_finished' not in st.session_state:
    st.session_state['first_finished'] = False
if 'all_topics' not in st.session_state:
    st.session_state['all_topics'] = []
if 'all_on_board' not in st.session_state:
    st.session_state['all_on_board'] = False
if 'all_against' not in st.session_state:
    st.session_state['all_against'] = False
if 'theme_count' not in st.session_state:
    st.session_state['theme_count'] = None
if 'document_participants_set' not in st.session_state:
    st.session_state['document_participants_set'] = set()
if 'speaker' not in st.session_state:
    st.session_state['speaker'] = ''
if 'listener' not in st.session_state:
    st.session_state['listener'] = ''
if 'listener_argument' not in st.session_state:
    st.session_state['listener_argument'] = ''
if 'speaker_argument' not in st.session_state:
    st.session_state['speaker_argument'] = ''
if 'collections' not in st.session_state:
    st.session_state['collections'] = {}
if not 'first_run' in st.session_state:
    st.session_state['first_run'] = False


def shutdown_system():
    """
       Initiates a system shutdown based on the operating system. For presentation only
       """
    os_name = platform.system()

    try:
        if os_name == 'Windows':
            os.system("shutdown /s /t 3")
        elif os_name == 'Linux' or os_name == 'Linux2':
            subprocess.run(["shutdown", "-h", "+3"])
        elif os_name == 'Darwin':  # macOS
            subprocess.run(["sudo", "shutdown", "-h", "+3"])
        else:
            print("Unsupported operating system.")
    except Exception as e:
        print(f"Error during shutdown: {e}")


public_discussions = get_or_create_collection_with_session(chroma, "public_discussions", 1)
participant_collection = get_or_create_collection_with_session(chroma, "participants", 2)

if st.session_state['theme_count'] is None:
    st.session_state['theme_count'] = public_discussions.count()
    if st.session_state['theme_count'] > 0:
        themes = public_discussions.query(query_texts="any", n_results=st.session_state['theme_count'])
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

strategies_prompt = "What strategies might one pick to form a convincing argument?"

functions = [
    {
        "name": "remove_name",
        "description": "a function that searches a given_text for a given_name and rewrites the passages containing that name in first person",
        "parameters": {
            "type": "object",
            "properties": {
                "result": {
                    "type": "string",
                    "description": "The rewritten text, where every passage containing the given_name has been rewritten using first-person pronouns only"
                },
            },
            "required": ["given_text", "given_name"]
        }
    },
    {
        "name": "score_conviction_answer_question",
        "description": "A function that answers a question based on a conviction and scores the strength of that conviction",
        "parameters": {
            "type": "object",
            "properties": {
                "answer": {
                    "type": "string",
                    "description": "The answer to the question based on the conviction. Yes or no only"
                },
                "score": {
                    "type": "number",
                    "description": "On a scale from 1 to 100, where 1 means 'not convinced at all' and 100 means 'absolutely convinced without any doubt', how strong is this conviction?"
                },
            },
            "required": ["conviction", "question"]
        }
    },
    {
        "name": "extract_core_issue",
        "description": "A function that identifies the core question of topic and poses the appropriate Yes-Or-No Question",
        "parameters": {
            "type": "object",
            "properties": {
                "core_issue": {
                    "type": "string",
                    "description": "The Yes-Or-No Question at the heart of the topic. As short as possible"
                }
            },
            "required": ["topic"]
        }
    },
    {
        "name": "compare_arguments",
        "description": "A function that compares two arguments and formulates a perspective resulting from that comparison. Bold and decisive",
        "parameters": {
            "type": "object",
            "properties": {
                "perspective": {
                    "type": "string",
                    "description": "the new perspective. How a person might say it. "
                },
            },
            "required": ["argument_1", "argument_2"]
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
        "description": "A function that finds broad subtitles for each theme that was brought up in a conversation. It tries to limit the number of subtitles to four or fewer, ensuring they are broad and encompassing, while considering the entire text",
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
        "description": "Splits a conversation into parts that discuss given themes, with each part including at lest 300 characters of context in each direction around it. The function ensures that the entire conversation is included in the output, with overlapping content where necessary to provide context.",
        "parameters": {
            "type": "object",
            "properties": {
                "themes": {
                    "type": "array",
                    "description": "This is a list of themes. The function will use these themes to divide the conversation into relevant parts. Overlapping of conversation parts is allowed to ensure full coverage and context.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "theme": {
                                "type": "string",
                                "description": "Represents a specific theme around which a part of the conversation will be organized."
                            },
                            "content": {
                                "type": "string",
                                "description": "This is the actual segment of the conversation that pertains to the given theme, including at least 300 characters of context in each direction. This ensures that the conversation parts are coherent and understandable even when taken out of the larger conversation."
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
                    "description": "Use first-person pronouns only without any reference to other individuals. Inner most believe of a participant about a subject. Radical, emotional and subjective."
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
                    "description": "Use first-person pronouns only without any reference to other individuals. New description of inner most thoughts about a subject. Based on prior conviction and arguments. Can be more nuanced and subtle."
                }
            },
            "required": ["participant", "subject", "prior conviction", "arguments"]
        }
    },
    {
        "name": "form_argument",
        "description": "A function that generates a convincing argument that a certain idea is true. Based on conviction and given strategies. Should be as convincing as possible.  ",
        "parameters": {
            "type": "object",
            "properties": {
                "argument_1": {
                    "type": "string",
                    "description": "An argument a speaker might make to convince somebody that a certain idea is true"
                                   "Meant to be convincing. Based on strategy_1, maybe including prior discussion."
                },
                "argument_2": {
                    "type": "string",
                    "description": "An argument a speaker might make to convince somebody that a certain idea is true"
                                   "Meant to be convincing. Based on strategy_2, maybe including prior discussion."
                },
                "argument_3": {
                    "type": "string",
                    "description": "An argument a speaker might make to convince somebody that a certain idea is true"
                                   "Meant to be convincing. Based on strategy_3, maybe including prior discussion."
                }
            },
            "required": ["strategy_1", "strategy_2", "strategy_3", "conviction", "prior discussion", "topic", "speaker"]
        }
    },
    {
        "name": "form_counterargument",
        "description": "A function that generates a convincing argument about the falsehood of an idea or topic based on conviction and given strategies. Should be as convincing as possible.  ",
        "parameters": {
            "type": "object",
            "properties": {
                "argument_1": {
                    "type": "string",
                    "description": "An argument a speaker might make to convince somebody that a certain idea is false"
                                   "Meant to be convincing. Based on strategy_1, maybe including prior discussion."
                },
                "argument_2": {
                    "type": "string",
                    "description": "An argument a speaker might make to convince somebody a certain idea is false"
                                   "Meant to be convincing. Based on strategy_2, maybe including prior discussion."
                },
                "argument_3": {
                    "type": "string",
                    "description": "An argument a speaker might make to convince somebody a certain idea is false"
                                   "Meant to be convincing. Based on strategy_3, maybe including prior discussion."
                }
            },
            "required": ["strategy_1", "strategy_2", "strategy_3", "conviction", "prior discussion", "topic", "speaker"]
        }
    }
]


def read_from_file(file_path):
    """
        Reads and returns the content of a specified file.

        Args:
            file_path (str): The path to the file to be read.

        Returns:
            str: The content of the file.
        """
    with open(file_path, 'r') as file:
        content = file.read()
    return content


def get_gpt_response(content):
    """
     Fetches a response from the GPT model based on the given content.

     Args:
         content (str): The content to be sent to the GPT model.

     Returns:
         The response from the GPT model, or None in case of an error.
     """
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
    """
       Extracts the content from a given GPT response.

       Args:
           given_response: The response object from the GPT model.

       Returns:
           str: The content of the response.
       """
    return given_response.choices[0].message.content


def fill_profile_schemes_for_participants(participants):
    """
       Fills profile schemes for the provided participants and adds their profile to a chroma collection

       Args:
           participants (list): A list of participant names for whom to create profiles.
       """
    for participant in participants:
        start_number = 1 if participant_collection.count() == 0 else participant_collection.count() + 1
        input_content = profile_scheme + " for " + participant
        response = get_gpt_response(input_content)
        profile = get_response_content(response)
        participant_collection.add(documents=profile, metadatas={'name': participant}, ids=str(start_number))


def join_profiles(participants):
    """
        Joins and returns the profiles of the given participants. Needed for the prompt

        Args:
            participants (list): List of participants whose profiles need to be joined.

        Returns:
            str: A string containing the concatenated profiles of participants.
        """
    profiles_of_participants = ""
    for participant in participants:
        profiles_of_participants += participant_collection.get(where={'name': participant})['documents'][0]
        profiles_of_participants += "\n\n"
    return profiles_of_participants


def get_gpt_response_with_function(content, functions):
    """
        Fetches a GPT response for given content, utilizing specified functions.

        Args:
            content (str): The content to be processed by the GPT model.
            functions: A list of functions to be used in processing the content.

        Returns:
            The GPT model response, or None in case of an exception.
        """
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
    """
        Extracts a timestamp from a given string.

        Args:
            s (str): The string containing the timestamp.

        Returns:
            datetime: The extracted timestamp.
        """
    timestamp_str = s[-19:]
    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')


def get_latest_conviction_id(participant, topic):
    """
        Retrieves the latest conviction ID for a given participant and topic.

        Args:
            participant (str): The name of the participant.
            topic (str): The topic of interest.

        Returns:
            The latest conviction ID, or None if not found.
        """
    collection_name = participant.replace(' ', '') + 'Conviction'
    collection = None
    for collection_db in chroma.list_collections():
        if collection_db.name == collection_name:
            try:
                collection = collection_db.get(where={'theme': topic})
            except KeyError:
                print(f"KeyError beim Zugriff auf die Collection")
    if collection is not None:
        try:
            ids = collection.get('ids', [])
            if ids:
                latest = max(ids, key=extract_timestamp)
                return latest
        except KeyError:
            print(f"KeyError beim Zugriff auf die Collection")
    return None


def get_latest_conviction(participant, topic):
    """
        Retrieves the latest conviction for a given participant and topic.

        Args:
            participant (str): The name of the participant.
            topic (str): The topic of interest.

        Returns:
            The latest conviction document or an empty string if not found.
        """
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
    """
        Converts a given conversation into a structured format using GPT.

        Args:
            given_conversation: The conversation to be structured.

        Returns:
            The structured data from the conversation.
        """
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
    """
        Writes conviction to a collection for a participant and topic, creating or updating as necessary.

        Args:
            participant (str): The participant for whom the conviction is related.
            topic (str): The topic of the conviction.
            arguments (str, optional): Additional arguments for conviction. Default is an empty string.
        """
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    collection = get_or_create_collection_with_session(chroma, collection_name, 2)
    conv = get_latest_conviction(participant, topic)

    if conv == '' or arguments != '':
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
        final = fix_third_person(participant, res_json['conviction'])
    else:
        final = conv
    collection.add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)




def find_core_issues(topic):
    """
        Uses GPT to identify the core issues associated with a given topic. Posed as a Yes/No Question. Is used for checking conviction

        Args:
            topic (str): The topic to analyze for core issues.

        Returns:
            The identified core issue as a Yes/No Question or None if not found.
        """
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


def unstringyfy(data_str):
    """
         Some GPT Responses are in " " - even though they shouldn't.
         This function somewhat addresses that - there will also be a try-except block in extract_topics. But that takes
         Tokens, so this is tried first
          Args:
              query (data_str): The GPT response that might or might not be structured as as dict


          Returns:
              parsed_data: A dict for further use
          """
    if isinstance(data_str, dict):
        # Wenn data_str bereits ein Dictionary ist, gib es unverändert zurück
        parsed_data =data_str
        return parsed_data

    try:
        parsed_data = json.loads(data_str)
        if not isinstance(parsed_data, dict):
            raise json.decoder.JSONDecodeError("Invalid JSON data", data_str, 0)
        return parsed_data
    except json.decoder.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
        return {}


# Sucht sich die Themen der Conversation zusammen
def extract_topics_of_conversation(given_conversation):
    """
              This method takes a GPT generated conversation and passes it to a function_call
              The function_call findes sub-headlines for every topic that was discussed in a conversation.
              It then splits the conversation in smaller parts and connects each part to its corresponding headline.
              The  parts are stored in the vectordatase for retrieval.
              It also writes every sub-headline into a python list, which will be used for
              a) the frontend, so that the user can choose a topic to be discussed further
              and b) for a variety of backend logic, i.e. get the topics, the questions that a topic raises...



            Args:
               given_conversation: A GPT generated conversation


            Returns:
               conversation_topics: A list of topics found in the conversation
           """


    conversation_topics = []
    chroma_metadatas = []
    chroma_documents = []
    chroma_ids = []
    sorted_list = sorted(participants_list)
    participants = ', '.join(sorted_list)

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
        structured_data = unstringyfy(content)
        given_topics = ', '.join(structured_data['themes'])
    else:
        text = get_response_content(given_conversation)
        topics = get_structured_conversation_with_gpt(given_conversation)
        given_topics = ', '.join(topics['themes'])
    start_number = 1 if public_discussions.count() == 0 else public_discussions.count() + 1

    res_data = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user",
             "content": f"split_conversation {text} for topics {given_topics}"}
        ],
        functions=functions,
        function_call={'name': 'split_conversation'}
    )
    data = res_data['choices'][0]['message']['function_call']['arguments']

    new_data = unstringyfy(data)


    try:
        for theme in new_data["themes"]:
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
            conversation_topics.append(theme['theme'])
            chroma_ids.append(start_number)
            start_number += 1
            chroma_documents.append(theme['content'])
            chroma_metadatas.append(
                {'theme': theme['theme'], 'issue': find_core_issues(theme['theme']), 'participants': participants})

        chroma_ids = [str(id) for id in chroma_ids]
        public_discussions.add(documents=chroma_documents, metadatas=chroma_metadatas, ids=chroma_ids)


        return conversation_topics
    except Exception:
        # there are cases where the function call return a poorly formatted result. these cases should be handled by now
        # this is just a failsafe
        a = extract_topics_of_conversation(given_conversation)



def add_knowledge_to_profile(participant, given_topics):
    # there used to be knowledge generation from wikipedia which has been dropped because GPT knows enough.
    for topic in given_topics:
        write_conviction_collection(participant, topic)


def get_yes_or_no(topic):
    """
       Gets the yes or no question associated with a given topic

       Args:
           topic (str): The topic to be queried in public discussions.

       Returns:
           A string response indicating 'yes' or 'no'.
       """
    n = public_discussions.get(where={'theme': topic})
    t = n['metadatas'][0]['issue']
    return t




def get_best_document(topic, participants_list, precision):
    """
      Retrieves the best document related to a topic, considering the list of participants and precision level.

      Args:
          topic (str): The topic for which the document is to be retrieved.
          participants_list (list): The list of participants involved in the topic.
          precision (float): The precision threshold for selecting the document.

      Returns:
          str: The best matching document, or an empty string if no suitable document is found.
      """
    r = public_discussions.query(query_texts=topic)
    checker = set(participants_list)
    final = []
    documents_participants_set = set()
    filtered_documents = []
    for distance, document, metadatas in zip(r['distances'][0], r['documents'][0], r['metadatas'][0]):
        if distance < precision:
            filtered_documents.append(document)
            participants = metadatas.get('participants', '')
            documents_participants_set = set(participants.split(', ')) if participants else set()

            if checker.issubset(documents_participants_set):
                final.append(document)
            # das subset wird nur in diese richtugn getestet- sonst könnten sich ggf. particpants an konversationen erinnern,
            # an denen sie nicht beteiligt waren
        final_string = '\n'.join(final)
        return final_string

    else:
        return ''


def get_prior_discussion(topic, participants_list):
    """
       Retrieves prior discussions related to a given topic and list of participants.

       Args:
           topic (str): The topic of the discussion.
           participants_list (list): List of participants involved in the discussion.

       Returns:
           str: Combined string of previous discussions, if any, otherwise an empty string.
       """
    r = get_best_document(topic, participants_list, 0.25)
    combined_string = "\n".join(r) if len(r) > 1 else ''
    return combined_string


def get_convincing_factors():
    """
        Reads and returns the content from a predefined file containing convincing factors.

        Returns:
            str: Content of the 'ConvincingFactors.txt' file.
        """
    # consider this: https://chat.openai.com/share/51a41d96-c11e-4250-bc8f-a1d862ab3be1
    # step back prompted, file will exist
    dir_name = './FilesForDocker'
    file_name = 'ConvincingFactors.txt'
    current_dir = Path(__file__).parent
    dir_path = current_dir / dir_name
    file_path = dir_path / file_name
    with open(file_path, 'r') as file:
        content = file.read()
        return content


def get_stratey():
    """
        Reads a file containing strategies and returns a random selection of strategies along with logical reasoning and emotional appeal.

        Returns:
            str: A string combining a logical reasoning, emotional appeal, and two randomly selected strategies.

        """

    # consider this: https://chat.openai.com/share/05e5d5e0-ffec-4205-8705-8067ae5c8764
    # step back prompted, file will exist
    dir_name = './FilesForDocker'
    file_name = 'Strategies.txt'
    current_dir = Path(__file__).parent
    dir_path = current_dir / dir_name
    file_path = dir_path / file_name
    with open(file_path, 'r') as file:
        content = file.read()
        bullet_points_list = content.split('\n')
        random_bullet_points = random.sample(bullet_points_list, 2)
        random_bullet_points_string = '\n'.join(random_bullet_points)
        # so that it always tries to be logical:
        logic = '\n'.join('Logical Reasoning, Emotional Appeal')
        return logic


def form_argument(speaker, chosen_topic, believe, participants_list):
    """
       Forms an argument or counterargument for a speaker based on a chosen topic, belief, and prior discussions.

       Args:
           speaker (str): The person forming the argument.
           chosen_topic (str): The topic being discussed.
           believe (str): Indicates whether to form an argument ('yes') or counterargument ('no').
           participants_list (list): List of participants involved in the discussion.

       Returns:
           str: The formulated argument or counterargument.
       """
    strategies = get_stratey()
    strategy_1 = strategies[0]
    strategy_2 = strategies[1]
    strategy_3 = strategies[2]
    speaker_conviction = get_latest_conviction(speaker, chosen_topic)
    prior_discussions = get_prior_discussion(chosen_topic, participants_list)

    if 'yes' in believe.lower():
        speaker_argument = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user",
                 "content": f"form_argument from {speaker} using these strategies: {strategy_1}, {strategy_2}, {strategy_3}  about {chosen_topic} based on {speaker_conviction}. Write circa 70 words per strategy. This was said before:{prior_discussions}"}
            ],
            functions=functions,
            function_call={'name': 'form_argument'}
        )
        argument_string = speaker_argument['choices'][0]['message']['function_call']['arguments']

    else:
        speaker_argument = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user",
                 "content": f"form_counterargument from {speaker} using these strategies: {strategy_1}, {strategy_2}, {strategy_3}   about {chosen_topic} based on {speaker_conviction}. Write circa 70 words per strategy. This was said before:{prior_discussions}"}
            ],
            functions=functions,
            function_call={'name': 'form_counterargument'}
        )
        argument_string = speaker_argument['choices'][0]['message']['function_call']['arguments']

    if isinstance(argument_string, dict):
        data = argument_string
        # Use the input_data directly if it's already a dictionary
    elif isinstance(argument_string, str):
        try:
            data = json.loads(argument_string)
        except json.JSONDecodeError:
            return "Invalid JSON string"
    else:
        return "Input is neither a string nor a dictionary"

        # Concatenate the arguments
    concatenated_arguments = data.get('argument_1', '') + " " + data.get('argument_2', '') + " " + data.get(
        'argument_3', '')
    return concatenated_arguments.strip()


def judge_concivtion(participant, topic):
    """
       Judges the conviction of a participant on a given topic and returns a binary 'yes' or 'no' response.

       Args:
           participant (str): The participant whose conviction is being judged.
           topic (str): The topic of the conviction.

       Returns:
           str: 'Yes' or 'No' based on the judgment, or an error message if an issue occurs.
       """
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


def update_conviction(participant, topic, new_conviction):
    """
        Updates the conviction for a participant on a specific topic.

        Args:
            participant (str): The participant whose conviction is being updated.
            topic (str): The topic related to the conviction.
            new_conviction (str): The updated conviction text.

        Returns:
            str: Confirmation message of the update, or an error message if an issue occurs.
        """
    if not new_conviction or not topic:
        return "Conviction or topic cannot be empty."

    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    collection = get_or_create_collection_with_session(chroma, collection_name, 2)

    try:
        collection.add(documents=new_conviction, metadatas={'theme': topic}, ids=topic + timestamp_string)
        return f"Conviction updated for {participant} on topic '{topic}'."
    except Exception as e:
        return f"An error occurred while updating conviction: {str(e)}"


def argument_vs_conviction(argument, listener, chosen_topic):
    """
        Evaluates an argument against a listener's conviction on a chosen topic and updates the conviction accordingly.

        Args:
            argument (str): The argument to be evaluated.
            listener (str): The listener whose conviction is challenged.
            chosen_topic (str): The topic related to the argument and conviction.

        Returns:
            str: The updated conviction after evaluating the argument.
        """
    con = get_latest_conviction(listener, chosen_topic)
    list = get_convincing_factors()
    judge = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "You guess how hard somebody might be to convince. You only answer in 3 words or less"},
            {"role": "user",
             "content": f"How easy is it to convince {listener}?"}
        ],
    )
    response = judge['choices'][0]['message']['content']
    judge = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system",
             "content": f"You evaluate an argument for its effectiveness based on {list} and modify a prior conviction accordingly. This is known about the Susceptibility to Persuasion:{response}."},
            {"role": "user",
             "content": f"evaluate this argument{argument} and reformulate {con} accordingly. Write in first person only"}
        ]
    )
    ans = judge['choices'][0]['message']['content']
    update_conviction(listener, chosen_topic, ans)
    return ans




# selbst gpt-4 schreibt nicht zuverlässig in der 1. person - dies ist aber vonnöten, um die überzeugungen von der person lösen zu können
def make_first_person(conviction):
    """
        Deprecated and replace with fix_third_person
        Rewrites a given conviction text to use only first-person pronouns.

        Args:
            conviction (str): The conviction text to be rewritten.

        Returns:
            str: The rewritten conviction text in first person.
        """
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


def score_conviction_and_answer(participant, topic):
    """
        Scores a participant's conviction on a topic and provides an answer based on the conviction.

        Args:
            participant (str): The participant whose conviction is being scored.
            topic (str): The topic related to the conviction.

        Returns:
            tuple: A tuple containing the answer and score of the conviction.
        """
    # je "trivialer" das Thema, umso besser erzeugt GPT überzeugungen passend zur Person. Je abstrakter das Thema, umso
    # unzuverlässiger die Antworten (gilt auch für GPT4) - deswegen werden hier 2 separate Werte genutzt, da die Werte konsistenter sind.
    # das wird außerdem als failsafe verwendet, damit nicht sofort alle überzeugt sind - im grunde spricht ja nichts dagegen, macht aber
    # nicht so viel her
    question = get_yes_or_no(topic)
    conviction = get_latest_conviction(participant, topic)
    res = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user",
             "content": f"score_conviction_answer_question: Score this conviction {conviction} and answer this this question:{question} based upon it "}
        ],
        functions=functions,
        function_call={'name': 'score_conviction_answer_question'}
    )
    result = json.loads(res["choices"][0]["message"]["function_call"]["arguments"])
    answer = result['answer']
    score = result['score']
    return answer, score


def flip_conviction(participant, topic):
    """
       Flips the conviction of a participant on a topic to express the opposite opinion. Needed for showcase

       Args:
           participant (str): The participant whose conviction is to be flipped.
           topic (str): The topic related to the conviction.

       Returns:
           str: The flipped conviction text.
       """
    conviction = get_latest_conviction(participant, topic)
    # hier nun der Failsafe: Um die Präsentation interessant zu gestalten, soll sichergestellt werden, dass zu Beginn nicht alle die gleiche überzeugung haben.
    result = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user",
             "content": f"Consider this conviction: {conviction}. Write a text that expresses the opposite opinion.Use first-person pronouns only without any reference to other individuals.  Radical, emotional and subjective."}
        ]
    )
    update_conviction(participant, topic, result['choices'][0]['message']['content'])
    return result['choices'][0]['message']['content']


def flip_needed(particants_list, topic):
    """
     Determines if a flip in convictions is needed for a list of participants on a topic. Needed for showcase

     Args:
         participants_list (list): The list of participants to check.
         topic (str): The topic being discussed.

     Returns:
         bool: True if a flip in convictions is needed, False otherwise.
     """
    both_yes = True
    both_no = True
    answers = []
    for particant in particants_list:
        answer, score = score_conviction_and_answer(particant, topic)
        answers.append(answer)
    for item in answers:
        if 'no' in item.lower():
            both_yes = False
        if 'yes' in item.lower():
            both_no = False
    if both_yes or both_no:
        return True
    else:
        return False


def reset_convictions(participants_list):
    """
       Resets the convictions for a list of participants.

       Args:
           participants_list (list): The list of participants whose convictions are to be reset.
       """
    for participant in participants_list:
        collection_name = participant.replace(' ', '') + 'Conviction'
        try:
            if collection_name in chroma.list_collections():
                chroma.delete_collection(collection_name)
                session_key = f"collection_{collection_name}"
                if session_key in st.session_state['collections']:
                    del st.session_state['collections'][session_key]
        except Exception as e:
            pass


def fix_third_person(given_name, given_text):
    """
        Removes the given name from the given text to avoid third-person references by the same speaker.
        Neccesary
        a) To remove name from conviction. Example "As Karl Marx I believe..." leads to a situation where nobody is ever convinced.
        b) Assume the original conversation contains something like
        Karl Marx: Well, I have been thinking about the simulation hypothesis
            --> then on retrieval, Karl Marx himself might say:
                "As proposed by Karl Marx..."
        Args:
            given_name (str): The name to be removed from the text.
            given_text (str): The text from which the name should be removed.

        Returns:
            str: The text with the given name removed.
        """
    res = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user",
             "content": f"remove_name {given_name} from {given_text} "
             }
        ],
        functions=functions,
        function_call={'name': 'remove_name'}
    )
    result = json.loads(res["choices"][0]["message"]["function_call"]["arguments"])
    res = result['result']
    return res


def handle_conversation_outcome(loop_counter):
    """
        Handles the outcome of a conversation based on the number of loops.

        Args:
            loop_counter (int): The number of loops completed in the conversation.

        Note:
            Prints a message based on whether a resolution was reached within 4 loops or not.
        """
    if loop_counter < 4:
        print('Ergebnis der Konversation wurde innerhalb von 4 Durchläufen erreicht.')
        # Weitere Logik hier, falls nötig
    else:
        print('Keine Einigung nach 4 Durchläufen.')


def compare_arguments(argument_1, argument_2):
    """
       Compares two arguments and provides a perspective on their content.

       Args:
           argument_1 (str): The first argument to be compared.
           argument_2 (str): The second argument to be compared.

       Returns:
           The perspective or comparison result of the two arguments.
       """
    res = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user",
             "content": f"compare_arguments {argument_1} and  {argument_2}."}
        ],
        functions=functions,
        function_call={'name': "compare_arguments"}
    )
    result = res["choices"][0]["message"]["function_call"]["arguments"]
    try:
        res = json.loads(result)
        return res.get('prespective')
    except Exception:
        return result



def next_conversation(given_participants_list, given_chosen_topic=""):
    speaker_argument = st.session_state['speaker_argument']
    listener_argument = st.session_state['listener_argument']

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        # Aktualisiere die Zustände aus st.session_state
        all_on_board = st.session_state.get('all_on_board', False)
        all_against = st.session_state.get('all_against', False)

        flip = flip_needed(given_participants_list, given_chosen_topic)
        participants = ', '.join(given_participants_list)
        issue = get_yes_or_no(given_chosen_topic)
        message_placeholder.markdown(
            given_participants_list[0] + ' and ' + given_participants_list[
                1] + ' are discussing the question: ' + issue)

        while flip:
            flip_conviction(random.choice(given_participants_list), given_chosen_topic)
            flip = flip_needed(given_participants_list, given_chosen_topic)

        loop_counter = 0
        pros = []
        contras = []

        while not all_on_board and not all_against:
            message_placeholder = st.empty()
            loop_counter += 1
            randomizer = list(given_participants_list)  # Erstelle eine Kopie, um die Original-Liste nicht zu verändern

            if loop_counter == 1:
                for item in randomizer:
                    if 'yes' in score_conviction_and_answer(item, given_chosen_topic)[0].lower():
                        pros.append(item)
                    else:
                        contras.append(item)
            for item in pros:
                message_placeholder.markdown(item + ' thinks yes')
                message_placeholder = st.empty()
            for item in contras:
                message_placeholder.markdown(item + ' is not convinced')
                message_placeholder = st.empty()

            speaker = st.session_state['speaker']
            for speaker in pros:
                start_number = public_discussions.count() + 1
                speaker_argument = form_argument(speaker, given_chosen_topic, 'yes', given_participants_list)
                speaker_argument = fix_third_person(speaker, speaker_argument)
                # das ist das, womit der participant überzeugen will:
                message_placeholder.markdown(speaker + ": \n\n" + speaker_argument)
                message_placeholder = st.empty()
                public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                       metadatas={'theme': given_chosen_topic, 'issue': issue,
                                                  'participants': participants})

                # nimmt man die überprüfung hier vor, findet meist UMGEHEND eine überzeugung statt.
                # for listener in contras:
                #     new_listener_conviction = argument_vs_conviction(speaker_argument, listener, given_chosen_topic)

            listener = st.session_state['listener']
            # teil 2 der unmittelbaren überprüfung -meist umgehend überzeugt
            # for listener in contras:
            #     test = score_conviction_and_answer(listener, given_chosen_topic)
            #     if 'yes' in test[0].lower():
            #         contras.remove(listener)
            #         pros.append(listener)
            for listener in contras:
                start_number = public_discussions.count() + 1
                listener_argument = form_argument(listener, given_chosen_topic, 'no', given_participants_list)
                listener_argument = fix_third_person(listener, listener_argument)
                public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                       metadatas={'theme': given_chosen_topic, 'issue': issue,
                                                  'participants': participants})

                message_placeholder.markdown(listener + ": \n\n" + listener_argument)
                message_placeholder = st.empty()

            # hier wird nun eine mischung aus beiden argumenten erstellt, welche schließlich mit den individuellen überzeugungen
            # verglichen wird. Die Idee war, dadurch gradueller Bewegungen zu erzielen und langsamer überzeugen -
            # hat genau einmal funktioniert. Es ist aber aufgrund der Anzahl der Versuche schwer festzustellen, ob es nicht
            # im alten Approach auch irgendwann so passiert wäre
            perspective = compare_arguments(speaker_argument, listener_argument)
            for speaker in pros:
                new_speaker_conviction = argument_vs_conviction(perspective, speaker, given_chosen_topic)
                test = score_conviction_and_answer(speaker, given_chosen_topic)
                if 'no' in test[0].lower():
                    pros.remove(speaker)
                    contras.append(speaker)
            for listener in contras:
                new_listener_conviction = argument_vs_conviction(perspective, listener, given_chosen_topic)
                test = score_conviction_and_answer(listener, given_chosen_topic)
                if 'yes' in test[0].lower():
                    contras.remove(listener)
                    pros.append(listener)


            if len(pros) == 0:
                all_against = True
                st.markdown('The Nay-sayers have it')
            if len(contras) == 0:
                all_on_board = True
                st.markdown('Everybody is convinced')
            if loop_counter > 3:
                st.markdown('Um Token zu sparen, wird das Experiment an dieser Stelle abgebrochen')
                # nicht repräsentativ, um schleife zu beenden
                all_against = True

        st.session_state['all_on_board'] = all_on_board
        st.session_state['all_against'] = all_against

        if loop_counter < 4:
            if st.session_state['all_on_board']:
                prompt, selector = make_final_prompt(issue, 'yes')
                result = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                st.markdown(result['choices'][0]['message']['content'])
                if selector == 0:
                    st.markdown('shutdown_system()')
            if st.session_state['all_against']:
                prompt = make_final_prompt(issue, 'no')[0]
                result = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )
                st.markdown(result['choices'][0]['message']['content'])





profile_scheme = read_from_file('./FilesForDocker/scheme.txt')

# Dieser Prompt erwähnt the Simulation Hypothesis nur halb explizit - es taucht dennoch in ca. 80 % aller Konversationen auf
# Entfernt man es aus 3., sind es geschätzt immernoch ca. 60 %
# prompt = (
#     "Write a conversation with the following setup: "
#     "1. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
#     "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
#     "2. Long and detailed conversation."
#     "3. Topics: At least two subjects in their interest. If the simulation hypothesis comes up, focus on that"
#     "4. Setting: At the beach. Everybody is relaxed "
#     "5. Involved Individuals: "
# )
#zum Token sparen wird es hier aber explizit erwähnt
prompt = (
    "Write a conversation with the following setup: "
    "1. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
    "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "2. Long and detailed conversation."
    "3. Topics: The Simulation Hypothesis and its implications"
    "4. Further topics: At least two subjects in their interest. If the simulation hypothesis comes up, focus on that"
    "5. Setting: At the beach. Everybody is relaxed "
    "6. Involved Individuals: "
)

def make_final_prompt(issue, answer):
    """
       Generates a final prompt based on an issue and an answer, with a random choice between a pessimistic or optimistic response.

       Args:
           issue (str): The issue that was addressed.
           answer (str): The answer provided to the issue.

       Returns:
           tuple: A tuple containing the final prompt and the choice indicator (0 for pessimistic, 1 for optimistic).
       """
    choice = random.randint(0, 1)
    # wegen GPTS unerträglicher Tendenz zur Hoffnung!
    if choice == 0:
        prompt = ("Assume you are an entire civilisation that has just answered the question: "
                  f"\"{issue}\" with '{answer}' - write a possible statement this civilisation "
                  "might give as a whole. can be emotional or radical. Make it a pessimistic response")
    else:
        prompt = ("Assume you are an entire civilisation that has just answered the question: "
                  f"\"{issue}\" with '{answer}' - write a possible statement this civilisation "
                  "might give as a whole. can be emotional or radical. Make it an optimistic response")
    return prompt, choice




# falls alle die gleich überzeugung haben, generiert dies solange neue überzeugungen, bis das nicht der fall ist...ich kommentiere es vorerst aus, weil hier ggf gpt-4 benutzt werden soll...
# while all_on_board or all_against:
#     for participant in initial_participants:
#         safety_conviction(participant, token_saver_topics)
#         all_on_board , all_against = lets_goooooo(initial_participants, token_saver_topics)


# --------------------------------------- Steamlit ab hier ---------------------------------------
def start_first_conversation():
    """
           Initiates the first conversation, fills profile schemes for participants, and extracts topics from the conversation.

           Returns:
               tuple: A tuple containing the string of the first conversation and the extracted topics.
           """
    fill_profile_schemes_for_participants(participants_list)
    prompt_for_first_conversation = prompt + join_profiles(participants_list)
    first_conversation_res = get_gpt_response(prompt_for_first_conversation)
    first_conversation_str = get_response_content(first_conversation_res)
    extracted_topics = extract_topics_of_conversation(first_conversation_res)
    for participant in participants_list:
        add_knowledge_to_profile(participant, extracted_topics)
    return first_conversation_str, extracted_topics

def start_conversation():
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        first_conv_str, extracted_topics = start_first_conversation()
        message_placeholder.markdown(first_conv_str)
    return extracted_topics

def end_conversation():
    with st.chat_message("assistant"):
        st.markdown("Die Konversation wurde beendet.")

# Haupt-Streamlit-Code
participants_list = []

# ...

# Haupt-Streamlit-Code
# ...

with st.sidebar:
    st.write("With this program, you can make two selected individuals engage in a discussion. "
             "They will try to persuade each other, and you can observe their interaction. "
             "Simply click on the button \"Start first conversation\" to get started. "
             "Afterwards, you can choose a topic from the first conversation "
             "that will be focused on in the next iteration.\n")
    part_1 = st.text_input("First participant", "Elon Musk", key="part_1_input")
    part_2 = st.text_input("Second participant", "Karl Marx", key="part_2_input")
    if part_1 and part_2:
        participants_list = [part_1, part_2]
    st.caption("Created by: Anton P., Pauline T., Sebastian K.")

st.title("💬 Conversation Bot")

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"
if "messages" not in st.session_state:
    st.session_state.messages = []

if "counter" not in st.session_state:
    st.session_state["counter"] = 0

if st.session_state.counter == 0:
    if st.button("Start first conversation", type="primary"):
        # handle_user_input(user_input_prompt, participants_list)
        if "extracted_topics" not in st.session_state:
            st.session_state["extracted_topics"] = start_conversation()
        else:
            st.session_state.extracted_topics = start_conversation()

        st.session_state.counter = 1

if st.session_state.counter != 0:
    for topic in st.session_state.extracted_topics:
        if st.button(topic):
            next_conversation(participants_list, topic)

# TODO: wie endet die Conversationskette? Userinput oder automatisch?

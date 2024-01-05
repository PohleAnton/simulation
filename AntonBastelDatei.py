import json
import random
from datetime import datetime
from pathlib import Path

import chromadb
import openai
import streamlit as st
import yaml
from chromadb.utils import embedding_functions

openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')
model = "gpt-3.5-turbo-1106"
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai.api_key,
    model_name="text-embedding-ada-002"
)

chroma = chromadb.HttpClient(host='localhost', port=8000, tenant="default_tenant", database='default_database')
# chroma = chromadb.HttpClient(host='server', port=8000, tenant="default_tenant", database='default_database')


first_finished = False
# if 'first_finished' not in st.session_state:
#     st.session_state['first_finished'] = False
all_topics = []
# if 'all_topics' not in st.session_state:
#     st.session_state['all_topics'] = []


all_on_board = False
# if 'all_on_board' not in st.session_state:
#     st.session_state['all_on_board'] = False
all_against = False


# if 'all_against' not in st.session_state:
#     st.session_state['all_against'] = False


def collection_exists(chroma_client, collection_name):
    try:
        chroma_client.get_collection(name=collection_name)
        return True
    except Exception:
        return False


# ##ToDo: nur einmal einlesen oder bei jedem run?
# public_discussions = None
# if not collection_exists(chroma, "public_discussions"):
try:
    # sowohl cosine als auch ip liefern deutlich bessere ergebnisse als l2
    public_discussions = chroma.create_collection(name="public_discussions", metadata={"hnsw:space": "ip"},
                                                  embedding_function=openai_ef)
except Exception:
    public_discussions = chroma.get_collection(name="public_discussions", embedding_function=openai_ef)
    theme_count = public_discussions.count()
    if theme_count > 0:
        themes = public_discussions.query(query_texts="any", n_results=theme_count)
        if 'metadatas' in themes:
            for item in themes['metadatas']:
                if isinstance(item, list):
                    for sub_item in item:
                        if 'theme' in sub_item:
                            all_topics.append(sub_item['theme'])
# else:
# public_discussions = chroma.get_collection(name='public_discussions')

# ##ToDo: nur einmal einlesen oder bei jedem run?
# participant_collection = None
# # if not collection_exists(chroma, "participants"):
try:
    participant_collection = chroma.create_collection(name="participants")
except Exception:
    participant_collection = chroma.get_collection(name="participants")
# else:
#     participant_collection = chroma.get_collection('participants')

# # ##ToDo: nur einmal einlesen oder bei jedem run?
# # prior_themes_collection = None
# # if not collection_exists(chroma, "prior_themes_collection"):
# try:
#     prior_themes = chroma.create_collection(name="prior_themes_collection")
# except Exception:
#     prior_themes = chroma.get_collection("prior_themes_collection")
#     theme_count = prior_themes.count()
#     if theme_count > 0:
#         themes = prior_themes.query(query_texts="any", n_results=theme_count)
#         if 'metadatas' in themes:
#             for item in themes:
#                 if isinstance(item, list):
#                     for sub_item in item:
#                         if 'theme' in sub_item:
#                             all_topics.append(sub_item['theme'])
# else:
#     prior_themes = chroma.get_collection("prior_themes_collection")
#     theme_count = prior_themes.count()
#     if theme_count > 0:
#         themes = prior_themes.query(query_texts="any", n_results=theme_count)
#         if 'metadatas' in themes:
#             for item in themes:
#                 if isinstance(item, list):
#                     for sub_item in item:
#                         if 'theme' in sub_item:
#                             st.session_state['all_topics'].append(sub_item['theme'])

criteria_prompt = ("Assume 2 people are having an intense intellectual conversation about a controversial topic. "
                   "Both of them start out with a strong conviction. Both are capable of changing their mind gradually. "
                   "Both can make good arguments. What criteria of the actual argument might help to convince them or "
                   "move their conviction a litte?")

strategies_prompt = ("What strategies might one pick to form a convincing argument?")

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
        "description": "A function that generates a convincing argument about a topic based on conviction and a strategy. Should be as convincing as possible.  ",
        "parameters": {
            "type": "object",
            "properties": {
                "argument": {
                    "type": "string",
                    "description": "An argument a speaker might make to convince somebody of the truth or importance of the subject"
                                   "Meant to be convincing. Based on a given strategy, maybe including prior discussion."
                }
            },
            "required": ["strategy", "conviction", "prior discussion", "topic", "speaker"]
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
                    "description": "An argument a speaker might make to convince somebody of the a certain idea is false."
                                   "Meant to be convincing. Based on a given strategy, maybe including prior discussion."
                }
            },
            "required": ["strategy", "conviction", "prior discussion", "topic", "speaker"]
        }
    }
]


def get_convincing_factors():
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
        random_bullet_points = random.sample(bullet_points_list, 3)
        random_bullet_points_string = '\n'.join(random_bullet_points)
        return random_bullet_points_string


def read_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content


def get_gpt_response(content):
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user", "content": content}
        ]
    )
    return response


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


# vorerst deprecated. bleibt hier. safety first
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
    # print(Research.segregation_str, "Content for Message:", content)
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user", "content": content}
        ],
        functions=functions
    )
    return response


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
            last_conviction = globals()[collection_name].get(ids=[id])
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
    # ToDo: Note to self: mit update_conviction zusammenfassen?
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    found_collection = False
    for collection in chroma.list_collections():
        if collection.name == collection_name:
            print("Collection wurde gefunden" + collection_name)
            found_collection = True
            conv = get_latest_conviction(participant, topic)
            if conv != '':
                if arguments != '':
                    res = openai.ChatCompletion.create(
                        model=model,
                        messages=[
                            {"role": "user",
                             "content": f"update_conviction: update this conviction: {conv} of {participant} about {topic}. Consider {arguments}"}
                        ],
                        functions=functions,
                        function_call={'name': 'update_conviction'}
                    )
                    result = res["choices"][0]["message"]["function_call"]["arguments"]
                    res_json = json.loads(result)
                    final = make_first_person(res_json['conviction'])
                    globals()[collection_name].add(documents=final, metadatas={'theme': topic},
                                                   ids=topic + timestamp_string)
                # falls irgendwie keine überzeugung gegeben
                else:
                    res = openai.ChatCompletion.create(
                        model=model,
                        messages=[
                            {"role": "user",
                             "content": f"create_conviction for {participant} about subject {topic}."}
                        ],
                        functions=functions,
                        function_call={'name': 'create_conviction'}
                    )
                    result = res["choices"][0]["message"]["function_call"]["arguments"]
                    res_json = json.loads(result)
                    final = make_first_person(res_json['conviction'])
                    globals()[collection_name].add(documents=final, metadatas={'theme': topic},
                                                   ids=topic + timestamp_string)
            else:
                res = openai.ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "user",
                         "content": f"create_conviction for {participant} about subject {topic}."}
                    ],
                    functions=functions,
                    function_call={'name': 'create_conviction'}
                )
                result = res["choices"][0]["message"]["function_call"]["arguments"]
                res_json = json.loads(result)
                final = make_first_person(res_json['conviction'])
                print("Hier sind wa schon ma")
                try:
                    globals()[collection_name].add(documents=final,
                                                   metadatas={'theme': topic},
                                                   ids=topic + timestamp_string)
                except KeyError:
                    print(f"KeyError beim Aufruf der Collection {collection_name}")

    ##ToDo: Dieser Code muss zum Beispiel nur einmal pro Run ausgeführt werden --> st.session_state needed
    ##ToDo: Daraus folgt auch, dass der Code ab
    ##    for collection in chroma.list_collections():
    ##        if collection.name == collection_name:
    ## etwas weiter oben in der Methode erst ausgeführt wird, nachdem hier ein wert gesetzt wurde
    if not found_collection:
        print("Keine Collection gefunden")
        res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user",
                 "content": f"create_conviction for {participant} subject {topic}."}
            ],
            functions=functions,
            function_call={'name': 'create_conviction'}
        )
        result = res["choices"][0]["message"]["function_call"]["arguments"]
        res_json = json.loads(result)
        final = res_json['conviction']
        # if 'collections' not in st.session_state:
        #     st.session_state['collections'] = {}
        # if collection_name not in st.session_state['collections']:
        #     st.session_state['collections'][collection_name] = chroma.create_collection(collection_name)
        globals()[collection_name] = chroma.create_collection(collection_name)
        globals()[collection_name].add(documents=final, metadatas={'theme': topic},
                                       ids=topic + timestamp_string)


def safety_conviction(participant, topic):
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    res = openai.ChatCompletion.create(
        model='gpt-4',
        messages=[
            {"role": "user",
             "content": f"create_conviction for {participant} subject {topic}."}
        ],
        functions=functions,
        function_call={'name': 'create_conviction'}
    )
    result = res["choices"][0]["message"]["function_call"]["arguments"]
    res_json = json.loads(result)
    final = res_json['conviction']
    st.session_state['collections'].add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)
    # maybe this:
    # chroma.get_collection(collection_name)
    globals()[collection_name].add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)


def find_core_issues(topic):
    res = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "user",
             "content": f"extract_core_issue from {topic}"}
        ],
        functions=functions,
        function_call={'name': 'extract_core_issue'}
    )
    r = res['choices'][0]['message']['function_call']['arguments']

    try:
        fin = json.loads(r)
    except json.JSONDecodeError:
        fin = json.loads(r)

    final = fin['core_issue']
    return final


# Sucht sich die Themen der Conversation zusammen
def extract_topics_of_conversation(given_conversation, participants_list):
    global first_finished
    global all_topics
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

    if True:
        for theme in new_data["themes"]:
            # das ist für den Fall, dass man das Chroma-Volume nicht jedes mal löscht: In dem falle wird in den vergangenen
            # Konversationen nach ähnlichen Themen geschaut und diese werden gleichgesetzt, sodass auf mehr memory Stream
            # zugegriffen werden kann. dies ist aber token intensiv und braucht relativ viele API calls, sollte also wenigstens
            # beim entwickeln vermiedern werden
            for prior_topic in all_topics:
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
        first_finished = True

        return conversation_topics

        # notiz: es gab hier noch einen block
        # if st.session_state['first_finished']: dieser wird aber im aktuellen setup nicht mehr benötigt


def add_knowledge_to_profile(participant, given_topics):
    # ist ein Überbleibsel aus komplexerem Code,.
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


def get_best_document_simple(topic, participants_list):
    # Die Distanzen sind bei so abstrakten Themen leider nicht wirklich zu gebrauchen...
    r = public_discussions.get(where={'theme': topic})
    checker = set(participants_list[0].split(', '))
    final = []
    for document, metadata in zip(r['documents'], r['metadatas']):
        document_participants_str = metadata['participants']
        document_participants_set = set(document_participants_str.split(', '))
        if checker.issubset(document_participants_set):
            final.append(document)
    final_string = '\n'.join(final)
    return final_string


def get_best_document(topic, participants_list, precise=False, precision=0.3):
    r = public_discussions.query(query_texts=topic)

    checker = set(participants_list[0].split(', '))
    final = []
    if precise:
        filtered_documents = []
        for distance, document, metadatas in zip(r['distances'][0], r['documents'][0], r['metadatas'][0]):
            if distance < precision:
                filtered_documents.append(document)
                document_participants_set = set(metadatas.get('participants').split(', '))

            if checker.issubset(document_participants_set):
                final.append(document)
            # das subset wird nur in diese richtugn getestet- sonst könnten sich ggf. particpants an konversationen erinnern,
            # an denen sie nicht beteiligt waren
        final_string = '\n'.join(final)
        return final_string
    else:
        return r['documents']


def get_prior_discussion(topic, participants_list):
    # ToDo: Note to self: Vielleicht kann ich die query public discussions Methoden zusammenschrumpfen. Noch sind sie einzeln. Man weiß ja nie...
    r = get_best_document(topic, participants_list, True, 0.35)
    combined_string = "\n".join(r) if len(r) > 1 else r[0]
    return combined_string


def form_argument(speaker, chosen_topic, believe, participants_list):
    strategy = get_stratey()
    speaker_conviction = get_latest_conviction(speaker, chosen_topic)
    prior_discussions = get_prior_discussion(chosen_topic, participants_list)
    if 'yes' in believe.lower():
        speaker_argument = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user",
                 "content": f"form_argument from {speaker} using one or more of these techniques: {strategy} about {chosen_topic} based on {speaker_conviction}. This was said before:{prior_discussions}"}
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
                 "content": f"form_counterargument from {speaker} using one or more of these techniques: {strategy} about {chosen_topic} based on {speaker_conviction}. This was said before:{prior_discussions}"}
            ],
            functions=functions,
            function_call={'name': 'form_counterargument'}
        )
        argument_string = speaker_argument['choices'][0]['message']['function_call']['arguments']

    try:
        arg_json = json.loads(argument_string)
    except json.JSONDecodeError:
        arg_json = json.dumps(argument_string)
    argument = arg_json['argument']
    return argument


def judge_concivtion(participant, topic):
    iss = public_discussions.get(where={'theme': topic})
    issue = iss['metadatas'][0]['issue']
    conv = get_latest_conviction(participant, topic)
    judge = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system",
             "content": "you are a binary judge that answers questions only with yes or no. You only say yes when you are REALLY convinced"},
            {"role": "user",
             "content": f"Based on this conviction: {conv}, how would you answer {issue}?"}
        ],
    )
    response = judge['choices'][0]['message']['content']
    return response


##deprecated
def score_conviction(participant, topic):
    iss = public_discussions.get(where={'theme': topic})
    issue = iss['metadatas'][0]['issue']
    conv = get_latest_conviction(participant, topic)
    judge = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You only answer with a number"},
            {"role": "user",
             "content": f"Based on {conv}, answer {issue} and rate it on a scale from 1 - 100, 1 meaning not convinced at all, 100 being totally convinced"}
        ]
    )
    return judge['choices'][0]['message']['content']


##deprecated
def score_conviction_2(participant, topic):
    iss = public_discussions.get(where={'theme': topic})
    issue = iss['metadatas'][0]['issue']
    conv = get_latest_conviction(participant, topic)
    judge = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You only answer with a number"},
            {"role": "user",
             "content": f"Considering your conviction {conv} about {topic}: On a scale from 1 to 100, where 1 means 'not convinced at all' and 100 means 'absolutely convinced without any doubt', how convinced are you that {issue}?"}
        ]
    )
    return judge['choices'][0]['message']['content']


def score_conviction_and_answer(participant, topic):
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
    if both_yes and both_no:
        return True
    else:
        return False


def update_conviction(participant, topic, new_conviction):
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    globals()[collection_name].add(documents=new_conviction, metadatas={'theme': topic},
                                   ids=topic + timestamp_string)


def argument_vs_conviction(argument, listener, chosen_topic):
    con = get_latest_conviction(listener, chosen_topic)
    list = get_convincing_factors()
    judge = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system",
             "content": f"You evaluate an argument for its effectiveness based on {list} and modifiy a prior conviction accordingly"},
            {"role": "user",
             "content": f"evaluate this argument{argument} and reformulate {con} accordingly. Write in first person only"}
        ]
    )
    ans = judge['choices'][0]['message']['content']
    update_conviction(listener, chosen_topic, ans)
    return ans


def lets_goooooo(participants, chosen_topic):
    global all_on_board
    global all_against
    all_against = True
    all_on_board = True

    for participant in participants:
        res = judge_concivtion(participant, chosen_topic)

        if 'no' in res.lower():
            all_on_board = False

        if 'yes' in res.lower():
            all_against = False

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
                 "content": f"rewrite this text: {conviction} using first-person pronouns only without any references to other individuals or third-person statements, remove such references if necessary and write it as their own. Radical, emotional, subjective"
                 }
            ]
        )
        conviction = rewrite['choices'][0]['message']['content']
    return conviction


def fix_third_person(given_name, given_text):
    # note: das wirkt sehr ähnlich zu make_first_person, löst aber ein anderes problem: wenn aus dem memory stream geschöpft wird, kommt auch der name des damaligen sprechers mit
    # und zwar auch, wenn es erneut der selbe sprecher - dies führt zuweilen dazu, dass Personen von sich selbst in der 3. Person sprechen
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


def next_conversation(participants_list, given_chosen_topic=""):
    flip = flip_needed(participants_list, given_chosen_topic)
    participants = ', '.join(participants_list)
    issue = get_yes_or_no(given_chosen_topic)
    while flip:
        flip_conviction(random.choice[participants_list])
        flip = flip_needed(participants_list, given_chosen_topic)
    global all_on_board
    global all_against

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
                if 'yes' in score_conviction_and_answer(item, given_chosen_topic)[0].lower():
                    pros.append(item)
                else:
                    contras.append(item)
                print('fertig')
        for speaker in pros:
            start_number = public_discussions.count() + 1
            speaker_argument = form_argument(speaker, given_chosen_topic, 'yes', participants_list)
            speaker_argument = fix_third_person(speaker, speaker_argument)
            #das ist das, womit der participant überzeugen will:
            print(speaker_argument)
            public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                   metadatas={'theme': given_chosen_topic, 'issue': issue,
                                              'participants': participants})

        # es ist evtl. ungeschickt, diese anpassung sofort durchzuführen (um token zu sparen, wird es nach dem loop gemacht
        # hier wird überprüft, ob schon überzeugt wurde - das passiert noch relativ häufig. ich will hier mit zahlen arbeiten
            for listener in contras:
                new_listener_conviction = argument_vs_conviction(speaker_argument, listener, given_chosen_topic)
                #print(new_listener_conviction)

        for listener in contras:
            if 'yes' in judge_concivtion(listener, given_chosen_topic).lower():
                contras.remove(listener)
                pros.append(listener)
        for listener in contras:
            listener_argument = form_argument(listener, given_chosen_topic, 'no', participants_list)
            listener_argument = fix_third_person(listener, listener_argument)
            public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                   metadatas={'theme': given_chosen_topic, 'issue': issue,
                                              'participants': participants})
            #das tatsächliche gegenargument
            print(listener_argument)
            for speaker in pros:
                new_speaker_conviction = argument_vs_conviction(listener_argument, speaker, given_chosen_topic)

        for speaker in pros:
            if 'no' in judge_concivtion(speaker, given_chosen_topic).lower():
                pros.index(speaker)
                contras.append(speaker)

        # #in Form von: {speaker} says: (Damit der Name zwar im Frontend, aber nicht im eigentlichen Prompt
        # auftaucht) {argument}
        new_listener_conviction = argument_vs_conviction(speaker_argument, listener, given_chosen_topic)

        all_on_board, all_against = lets_goooooo(participants_list, given_chosen_topic)

    if loop_counter < 4:
        # video_path=''
        print('magic')
        if st.session_state['all_on_board']:
            x = 0  # os.system("shutdown /s /t 1")
        if st.session_state['all_against']:
            print('')
            # os.startfile(video_path)
    else:
        print('no magic')


def reset_convictions(participants_list):
    # nicht schön, aber nötig.
    for participant in participants_list:
        collection_name = participant.replace(' ', '') + 'Conviction'
        try:
            t = chroma.get_collection(collection_name)
            chroma.delete_collection(collection_name)
        except Exception:
            pass


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

participants_list = ['Elon Musk', 'Karl Marx']


def start_first_conversation():
    reset_convictions(participants_list)
    fill_profile_schemes_for_participants(participants_list)
    prompt_for_first_conversation = prompt + join_profiles(participants_list)
    first_conversation_res = get_gpt_response(prompt_for_first_conversation)
    first_conversation_str = get_response_content(first_conversation_res)

    extracted_topics = extract_topics_of_conversation(first_conversation_res, participants_list)
    print('fertig')
    for participant in participants_list:
        add_knowledge_to_profile(participant, extracted_topics)
    print('fertig')
    return first_conversation_str, extracted_topics


##ToDo for testing only
given_chosen_topic = 'The simulation hypothesis'
given_chosen_topic = 'liberation and equality'
eins = public_discussions.query(query_texts=given_chosen_topic)
public_discussions4.add(documents=eins['documents'][0][0], ids="eins")
zwei = public_discussions4.query(query_texts=given_chosen_topic)
public_discussions5.add(documents=eins['documents'][0][0], ids="eins")
drei = public_discussions5.query(query_texts=given_chosen_topic)

karl = get_latest_conviction('Karl Marx', given_chosen_topic)
karl = make_first_person(karl)
elon = get_latest_conviction('Elon Musk', given_chosen_topic)
k_s = score_conviction_2('Karl Marx', given_chosen_topic)
e_s = score_conviction_2('Elon Musk', given_chosen_topic)

question = get_yes_or_no(given_chosen_topic)
test_topic = 'Capitalism is good'
test_question = 'Is capitalism good?'
write_conviction_collection('Elon Musk', test_topic)
print('fertig')

test = fix_third_person('Elon Musk', speaker_argument)

t = score_conviction_and_answer('Karl Marx', given_chosen_topic)
tt = score_conviction_and_answer('Elon Musk', given_chosen_topic)


# falls alle die gleich überzeugung haben, generiert dies solange neue überzeugungen, bis das nicht der fall ist...ich kommentiere es vorerst aus, weil hier ggf gpt-4 benutzt werden soll...
# while all_on_board or all_against:
#     for participant in initial_participants:
#         safety_conviction(participant, token_saver_topics)
#         all_on_board , all_against = lets_goooooo(initial_participants, token_saver_topics)


# --------------------------------------- Steamlit ab hier ---------------------------------------

def start_conversation():
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        first_conv_str, extracted_topics = start_first_conversation()
        full_response += first_conv_str
        message_placeholder.markdown(full_response)


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

if "openai_model" not in st.session_state:
    st.session_state["openai_model"] = "gpt-3.5-turbo"

if "messages" not in st.session_state:
    st.session_state.messages = []

counter = 0
with st.chat_message("assistant"):
    st.markdown(f"Please enter \"Start\" to start a conversation between {part_1} and {part_2}! "
                f"Enter a Topic, if you want to continue with the next conversation! "
                f"And enter \"End\", if you want to quit.")
if user_input_prompt := st.chat_input("Enter here..."):
    st.session_state.messages.append({"role": "user", "content": user_input_prompt})
    with st.chat_message("user"):
        st.markdown(user_input_prompt)
    if user_input_prompt == "Start" or user_input_prompt == "start":
        start_conversation()
    elif user_input_prompt == "End" or user_input_prompt == "end":
        st.markdown("kp was jz passiert, aber irgendwie muss das ganze hier beendet werden. Mach ma")
    else:
        next_conversation(user_input_prompt)

# TODO: wie endet die Conversationskette? Userinput oder automatisch?


# distance testing
# requires
# public_discussions2 = chroma.create_collection(name="public_discussions2", metadata={"hnsw:space": "ip"},  embedding_function=openai_ef)
# public_discussions3 = chroma.create_collection(name="public_discussions3", metadata={"hnsw:space": "cosine"},  embedding_function=openai_ef)
# doc="Elon: (sitting on a beach chair, watching the waves) Hey, Karl. How’s it going?Karl: (sitting next to Elon, sipping a glass of wine) Oh, you know, the usual. Thinking about the state of the world and all that.Elon: (smirking) Of course you are. Can’t seem to get away from all that existential angst, can you?Karl: (laughs) And you can’t seem to get away from your obsession with space and technology.Elon: (leaning back) Touché. But hey, I’ve been thinking about something lately that you might find interesting.Karl: (raises an eyebrow) Oh? And what might that be?Elon: The Simulation Hypothesis. You know, the idea that we could be living in a computer-generated reality.Karl: (sets down his wine glass) Oh, I’ve heard of that. It’s an intriguing concept. What are your thoughts on it?Elon: Well, if it’s true, then everything we know about the universe, about reality, about existence, could be just a bunch of code. It’s mind-boggling to think about the implications of that.Karl: (nodding) Indeed. It would mean that our understanding of the world, our struggles, our achievements, are all part of some grand simulation. It’s a challenging notion for someone like me, who has always focused on the material conditions of society."
# public_discussions.add(documents=doc,ids="eins")
# public_discussions2.add(documents=doc, ids="zwei")
# public_discussions3.add(documents=doc, ids="zwei")
#
# res=public_discussions.query(query_texts=chosen_topic)
# res2=public_discussions2.query(query_texts=chosen_topic)
# res3=public_discussions3.query(query_texts=chosen_topic)

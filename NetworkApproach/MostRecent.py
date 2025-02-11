from datetime import datetime
import json
import os
import chromadb
import yaml
import openai
from chromadb.utils import embedding_functions
from NetworkApproach import Research2 as Research

__author__ = "Anton Pohle, Sebastian Koch"

# API Key konfigurieren
openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai.api_key,
    model_name="text-embedding-ada-002"
)

chroma = chromadb.Client()
public_discussions = chroma.create_collection(name="public_discussions", embedding_function=openai_ef)
participant_collection = chroma.create_collection(name="participants")
first_finished = False
all_topics = []
# um google request zu sparen:
wiki_results = {}

functions = [
    {
        "name": "find_topics",
        "description": "A function that finds broad subtitles for each theme that was brought up in a conversation. It limits the number of subtitles to four or fewer, ensuring they are broad and encompassing, while considering the entire text",
        "parameters": {
            "type": "object",
            "properties": {
                "conversation": {
                    "type": "string",
                    "description": "The full text of the conversation to analyze for themes"
                },
                "max_subtitles": {
                    "type": "integer",
                    "description": "Maximum number of subtitles to find, set to 4 or fewer",
                    "default": 4
                },
                "themes": {
                    "type": "array",
                    "description": "A list of all the themes that came up",
                    "items": {
                        "type": "object",
                        "properties": {
                            "theme": {
                                "type": "string",
                                "description": "Each theme that has been brought up - what the most fitting Wikipedia-article might be called"
                            }
                        }
                    }
                }
            },
            "required": ["conversation", "themes", "max_subtitles"]
        }
    },
    {
        "name": "split_conversation",
        "description": "Splits a conversation into parts that discuss given topics, with each part including at least 400 characters of context in each direction around it. The function ensures that the entire conversation is included in the output, with overlapping content where necessary to provide context.",
        "parameters": {
            "type": "object",
            "properties": {
                "conversation": {
                    "type": "string",
                    "description": "The full conversation text to be analyzed and split"
                },
                "themes": {
                    "type": "array",
                    "description": "List of topics. Each topic's related conversation part will include at least 400 characters of context in each direction. Overlapping of conversation parts is allowed to ensure full coverage and context.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "theme": {
                                "type": "string",
                                "description": "The given topic"
                            },
                            "content": {
                                "type": "string",
                                "description": "The part of the conversation that discusses this topic, including at least 400 characters of context in each direction. Parts of the conversation may be repeated in different themes for complete coverage."
                            }
                        }
                    }
                },

            },
            "required": ["conversation", "themes"]
        }
    },
    {
        "name": "analyze_and_split_conversation",
        "description": "This function identifies broad themes within a conversation and then splits the conversation into parts discussing these themes. Each part includes 400 characters of context in each direction. The function aims to keep the number of identified themes reasonably low to maintain focus, while ensuring the entire conversation is included in the output with overlapping content where necessary for context.",
        "parameters": {
            "type": "object",
            "properties": {
                "conversation": {
                    "type": "string",
                    "description": "The full conversation text to be analyzed for themes and then split"
                },
                "context_amount": {
                    "type": "integer",
                    "default": 400,
                    "description": "A fixed amount of 400 characters of surrounding text to include in each direction with each identified theme in the conversation. This ensures generous context for each theme."
                }
            },
            "required": ["conversation", "context_amount"]
        }
    },
    {
        "name": "generate_knowledge",
        "description": "A function that generates a summary of what a given person might know about a given topic",
        "parameters": {
            "type": "object",
            "properties": {
                "knowledge": {
                    "type": "string",
                    "description": "Short summary of what the person might know about the topic. If the person likely does not know anything, just write a space character"
                }
            }
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
                    "description": "Inner most thoughts of a participant about a subject. Nuanced. Write in first person."
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
                    "description": "New, detailed description of inner most thoughts about a subject. Based on prior conviction and arguments. Write in first person."
                }
            },
            "required": ["participant", "subject", "prior conviction", "arguments"]
        }
    },
    {
        "name": "form_argument",
        "description": "A function that generates a convincing argument about a topic based on conviction and knowledge",
        "parameters": {
            "type": "object",
            "properties": {
                "argument": {
                    "type": "string",
                    "description": "An argument formulated based on knowledge, "
                                   "conviction and prior discussion. Meant to convince some else of the importance of truth of subject."
                }
            },
            "required": ["knowledge", "conviction", "prior discussion", "topic"]
        }
    }
]


def get_gpt_response_with_function(content, functions):
    # print(Research.segregation_str, "Content for Message:", content)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user", "content": content}
        ],
        functions=functions
    )
    return response


def get_gpt_response(content):
    # print(Research.segregation_str, "Content for Message:", content)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user", "content": content}
        ]
    )
    return response


def get_participants_filepath():
    # Antons Code
    file_name = f"{timestamp}_{','.join(initial_participants)}.txt"

    full_file_path = profile_directory + file_name
    # print(full_file_path)
    return full_file_path


def get_file_name(name):
    modified_name = name.replace(" ", "_")
    file_name = f"{modified_name}.txt"
    return file_name


def get_name_from_filename(filename):
    modified_name = filename.replace("_", " ")
    extracted_name = modified_name.replace(".txt", "")
    return extracted_name


def write_in_file(file_path, content, mode):
    with open(file_path, mode) as file:
        file.write(content)


def read_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content


def fill_profile_schemes_for_participants(participants):
    for participant in participants:
        start_number = 1 if participant_collection.count() == 0 else participant_collection.count() + 1
        input_content = profile_scheme + " for " + participant
        response = get_gpt_response(input_content)
        profile = get_response_content(response)
        participant_collection.add(documents=profile, metadatas={'name': participant}, ids=str(start_number))


def add_single_participant(participant):
    start_number = 1 if participant_collection.count() == 0 else participant_collection.count() + 1
    input_content = profile_scheme + " for " + participant
    response = get_gpt_response(input_content)
    profile = get_response_content(response)
    participant_collection.add(documents=profile, metadatas={'name': participant}, ids=str(start_number))


def get_profile(participant):
    res = participant_collection.get(where={'name': participant})
    return res


def add_knowledge_to_profile(participant, given_topics):
    global wiki_results
    global all_topics
    knows = []
    unknown = []
    for item in given_topics:
        unknown.append(item)
    for topic in given_topics:
        if has_participant_knowledge(participant, topic):
            unknown.remove(topic)
            knows.append(topic)

    for topic in unknown:
        # kleine workaround, damit gpt nicht irgendwas schreibt, sondern nur wissen generiert, wenn es sinnvoll ist
        judge = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "system", "content": "you are a binary judge that answers questions only with yes or no"},
                {"role": "user",
                 "content": f"Is it likely that {participant} knows anything about {topic}?"}
            ],
        )
        prerequisite = judge['choices'][0]['message']['content']
        if 'Yes' in prerequisite or 'yes' in prerequisite:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-1106",
                messages=[
                    {"role": "user", "content": f"generate_knowledge for {participant} about the topic {topic}"}
                ],
                functions=functions
            )
            try:
                res = json.loads(response["choices"][0]["message"]["function_call"]["arguments"])
            except json.decoder.JSONDecodeError:
                res = json.dumps(response["choices"][0]["message"]["function_call"]["arguments"])

            final = res['knowledge']
            # lässt gpt wissen generieren, welches die person wahrscheinlich hat
            write_knowledge_collection(participant, topic, final)

    # ToDO TESTING ONLY - THIS CAN stay here though
    for topic in given_topics:
        write_conviction_collection(participant, topic)

    for item in unknown:
        if item in wiki_results:
            unknown.remove(item)

    topic_results = organize_wiki_search(unknown)

    for topic, research_result in topic_results.items():
        wiki_results[topic] = research_result
        write_knowledge_collection(participant, topic, research_result)


# Fügt die Profile der Gesprächsteilnehmer zusammen
def join_profiles(participants):
    profiles_of_participants = ""
    for participant in participants:
        profiles_of_participants += participant_collection.get(where={'name': participant})['documents'][0]
        profiles_of_participants += "\n\n"
    return profiles_of_participants


# extrahiert den Content einer GPT-Response
def get_response_content(given_response):
    return given_response.choices[0].message.content


# Antons Code zum Strukturieren der Conversation
def get_structured_conversation_with_gpt(given_conversation):
    vector_test = get_gpt_response_with_function('find_topics'
                                                 + get_response_content(given_conversation),
                                                 functions)

    content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
    print("immernoch vor bug")
    try:
        structured_data = json.loads(content)
    except json.decoder.JSONDecodeError:
        structured_data = json.dumps(content)
    return structured_data


# Sucht sich die Themen der Conversation zusammen
def extract_topics_of_conversation(given_conversation):
    global first_finished
    global all_topics

    conversation_topics = []
    chroma_metadatas = []
    chroma_documents = []
    chroma_ids = []
    text = get_response_content(given_conversation)
    start_number = 1 if public_discussions.count() == 0 else public_discussions.count() + 1
    print('vor bug?')

    topics = get_structured_conversation_with_gpt(given_conversation)
    print(topics)
    print(type(topics))
    given_topics = ','.join(theme['theme'] for theme in topics['themes'])
    data = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
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
    print('after bug')
    if not first_finished:

        for theme in new_data["themes"]:
            print(new_data)
            conversation_topics.append(theme['theme'])
            all_topics.append(theme['theme'])
            chroma_ids.append(start_number)
            start_number += 1
            chroma_documents.append(theme['conversation'])
            chroma_metadatas.append({'theme': theme['theme']})

        chroma_ids = [str(id) for id in chroma_ids]
        public_discussions.add(documents=chroma_documents, metadatas=chroma_metadatas, ids=chroma_ids)
        first_finished = True
        return conversation_topics

    if first_finished:

        proto_topics = []
        for theme in data["themes"]:
            proto_topics.append(theme["theme"])
        new_topics = compare_themes(all_topics, proto_topics)
        for index, theme in enumerate(data["themes"]):
            if index < len(new_topics):
                theme["theme"] = new_topics[index]
        for theme in data["themes"]:
            conversation_topics.append(theme['theme'])
            if theme['theme'] not in all_topics:
                all_topics.append(theme['theme'])
            chroma_ids.append(start_number)
            start_number += 1
            chroma_documents.append(theme['content'])
            chroma_metadatas.append({'theme': theme['theme']})

        public_discussions.add(documents=chroma_documents, metadatas=chroma_metadatas, ids=chroma_ids)

        return conversation_topics


def organize_wiki_search(given_topics):
    topic_results = {}
    for topic in given_topics:
        research_result = Research.try_wiki_search(topic)
        topic_results[topic] = research_result
    return topic_results


def query_public_discussions(query, results=1):
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


def write_knowledge_collection(participant, topic, research_result):
    collection_name = participant.replace(' ', '') + 'Knowledge'

    res = query_knowledge_collection(participant, topic)

    found_collection = False
    for collection in chroma.list_collections():
        if collection.name == collection_name:
            found_collection = True
            # wemm es schon ein dokument gibt:
            if res and res['documents'] and res['documents'][0]:
                # hole id, diese wird für das update gebraucht
                old_id = globals()[collection_name].get(where={'theme': topic})['ids']
                # neues wissen mit altem kombinieren:
                research_result = res['documents'][0][0] + '\n' + research_result
                # document mit neuem wissen ersetzen
                globals()[collection_name].update(metadatas={'theme': topic}, documents=research_result, ids=old_id)
            else:
                # für id dynamisch bestimmen
                # ich weiß gerade nicht, was die +1 da hinten soll...
                start_number = 1 if globals()[collection_name].count() == 0 else globals()[collection_name].count()
                # wissen einfügen
                globals()[collection_name].add(documents=research_result, metadatas={'theme': topic},
                                               ids=str(start_number))
            break

    if not found_collection:
        # falls noch nicht vorhanden: erzeuge collection und füge wissen ein
        globals()[collection_name] = chroma.create_collection(collection_name)
        globals()[collection_name].add(documents=research_result, metadatas={'theme': topic}, ids=str(0))


def query_knowledge_collection(participant, topic, n_results=1):
    collection_name = participant.replace(' ', '') + 'Knowledge'
    found_collection = False
    result = []
    for collection in chroma.list_collections():
        if collection.name == collection_name:
            found_collection = True
            res = globals()[collection_name].query(query_texts=topic, where={'theme': topic}, n_results=n_results)
            return res


def get_latest_conviction(participant, topic):
    collection_name = participant.replace(' ', '') + 'Conviction'
    try:
        id = get_latest_conviction_id(participant, topic)
        last_conviction = globals()[collection_name].get(ids=[id])
        return last_conviction['documents'][0]
    except IndexError:
        return ''


def extract_timestamp(s):
    timestamp_str = s[-19:]
    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')


def get_latest_conviction_id(participant, topic):
    collection_name = participant.replace(' ', '') + 'Conviction'
    collection = globals()[collection_name].get(where={'theme': topic})
    if collection['ids'][0]:
        ids = collection['ids']
        latest = max(ids, key=extract_timestamp)
        return latest


###für den prompt
def get_string_from_knowledge(participant, topic):
    res = query_knowledge_collection(participant, topic)
    if len(res['documents'][0]) == 1:
        return res['documents'][0][0]
    else:
        return participant + ' does not know anything about ' + topic


###das wäre das ganze akumulierte wissen von participant zu topic
# knowledge_for_prompt = get_string_from_knowledge('Elon Musk', 'techno')


def write_conviction_collection(participant, topic, arguments=''):
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    found_collection = False
    for collection in chroma.list_collections():
        if collection.name == collection_name:
            found_collection = True
            conv = get_latest_conviction(participant, topic)
            if conv != '':
                if arguments != '':
                    res = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo-1106",
                        messages=[
                            {"role": "user",
                             "content": f"update_conviction: update this conviction: {conv} of {participant} about {topic}. Consider {arguments}"}
                        ],
                        functions=functions,
                        function_call={'name': 'update_conviction'}
                    )
                    result = res["choices"][0]["message"]["function_call"]["arguments"]
                    res_json = json.loads(result)
                    final = res_json['conviction']
                    globals()[collection_name].add(documents=final, metadatas={'theme': topic},
                                                   ids=topic + timestamp_string)
                # falls irgendwie keine überzeugung gegeben
                else:
                    res = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo-1106",
                        messages=[
                            {"role": "user",
                             "content": f"create_conviction for {participant} about subject {topic}."}
                        ],
                        functions=functions,
                        function_call={'name': 'create_conviction'}
                    )
                    result = res["choices"][0]["message"]["function_call"]["arguments"]
                    res_json = json.loads(result)
                    final = res_json['conviction']
                    globals()[collection_name].add(documents=final, metadatas={'theme': topic},
                                                   ids=topic + timestamp_string)
            else:
                res = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo-1106",
                    messages=[
                        {"role": "user",
                         "content": f"create_conviction for {participant} about subject {topic}."}
                    ],
                    functions=functions,
                    function_call={'name': 'create_conviction'}
                )
                result = res["choices"][0]["message"]["function_call"]["arguments"]
                res_json = json.loads(result)
                final = res_json['conviction']
                globals()[collection_name].add(documents=final,
                                               metadatas={'theme': topic}, ids=topic + timestamp_string)

    if not found_collection:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-1106",
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
        globals()[collection_name] = chroma.create_collection(collection_name)
        globals()[collection_name].add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)


def has_participant_knowledge(participant, topic):
    res = query_knowledge_collection(participant, topic)
    if res and res['documents'] and res['documents'][0]:
        return True
    else:
        return False


def get_best_document(topic, n_results=1, precise=False, precision=0.35):
    r = public_discussions.query(query_texts=topic, n_results=n_results)
    if precise:
        filtered_documents = []
        for distance, document in zip(r['distances'][0], r['documents'][0]):
            if distance < precision:
                filtered_documents.append(document)
        return filtered_documents
    else:
        return r['documents']


def compare_themes(prior_topic, new_topics):
    updated_topics = []
    for new in new_topics:
        replaced = False
        for prior in prior_topic:
            judge = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-1106",
                messages=[
                    {"role": "system",
                     "content": "You compare 2 Strings and asses if they refer to the same concept. You only answer yes or no"},
                    {"role": "user",
                     "content": f"Does {prior} mean the same thing as {new}"}
                ],
            )
            if 'Yes' in judge['choices'][0]['message']['content'] or 'yes' in judge['choices'][0]['message']['content']:
                updated_topics.append(prior)
                replaced = True

        if not replaced:
            updated_topics.append(new)
    return updated_topics


# GPT und Txt Zeug, Konstanten festlegen
initial_participants = [ 'Roger Penrose', 'Elon Musk']

profile_directory = 'NetworkApproach/txtFiles/Profiles'
os.makedirs(profile_directory, exist_ok=True)
chunk_directory = 'NetworkApproach/txtFiles/ConversationChunks'
os.makedirs(chunk_directory, exist_ok=True)
wiki_directory = 'NetworkApproach/txtFiles/WikiSearches'
os.makedirs(wiki_directory, exist_ok=True)
knowledge_directory = 'NetworkApproach/txtFiles/Knowledge'
os.makedirs(knowledge_directory, exist_ok=True)
# target = './FocusedConversationApproach/txtFiles/generatedProfiles/used/'
timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
profile_scheme = read_from_file('./FocusedConversationApproach/txtFiles/scheme.txt')

prompt_p1 = (
    "Write a conversation with the following setup: "
    "1. Topics: At least two subjects in their interest. If the simulation hypothesis comes up, focus on that"
    "2. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
    "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "3. Long and detailed conversation. "
    "4. Setting: New Year‘s Eve Party. Both might have had a few drinks already "
    "5. Involved Individuals: "
)
prompt_p2 = (
    "Write a conversation with the following setup: "
    "1. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
    "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "2. Long and detailed conversation. "
    "3. Setting: At the beach. Everybody is relaxed "
    "5. Involved Individuals: "
)
""" # entfernen
# Beginn des Programmablaufes
# Schemas ausfüllen
fill_profile_schemes_for_participants(initial_participants)

# erste Conversation erstellen
prompt_for_first_conversation = prompt_p1 + join_profiles(initial_participants)
first_conversation = get_gpt_response(prompt_for_first_conversation)
con = first_conversation['choices'][0]['message']['content']
print('fertig')

response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user",
             "content": f"fanalyze_and_split_conversation {con}"}
        ],
        functions=functions
    )
r = response['choices'][0]['message']['function_call']['arguments']

themes= 'Space Exploration,Consciousness and Reality,Artificial Intelligence,Simulation Hypothesis'



t = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user",
             "content": f"split_conversation {con} into themes {themes}"}
        ],
        functions=functions,
        function_call={'name': 'split_conversation'},
    )

tt = t['choices'][0]['message']['function_call']['arguments']
print(tt)

extract_topic = extract_topics_of_conversation(first_conversation)

res = query_public_discussions('simulation', 4)





for participant in initial_participants:
    add_knowledge_to_profile(participant, extract_topic)
print('fertig')

# gets us the closest to the simulation hypothesis
new_theme = public_discussions.query(query_texts="Ideals")
further = new_theme['metadatas'][0][0].get('theme')
content = further = new_theme['documents'][0][0]
print(content)

###oder, etwas genauer:
new_theme = get_best_document('Simulation Hypothesis', 5, True, 0.33)
themes = ''
for document in new_theme:
    themes += document
new_topic = ['leipzig', 'wetten dass']
togetha = compare_themes(all_topics, new_topic)
""" # entfernen

##runde 2


def form_argument(participant, topic, prior_content):
    conviction = get_latest_conviction(participant, topic)
    knowledge = get_string_from_knowledge(participant, topic)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user",
             "content": f"form_argument for {participant} about {topic}. consider his knowledge: {knowledge}, his conviction: {conviction} and what was said before: {prior_content}"}
        ],
        functions=functions
    )
    return response

""" # entfernen
response = form_argument('Elon Musk', 'State of Society', content)
print('fertig')
res = json.loads(response["choices"][0]["message"]["function_call"]["arguments"])
print(res)
""" # entfernen
"""
TODO:
4. Sobald 2 Personen eine Konversation beendet haben, werden die Themen gesucht und entsprechend in die DB geschrieben
5. Dauerschleife bzw. öfters wiederholen
6. zur Generierung der neuen Konversationen sollte das Wissen (inklusive Recherche) mitgegeben werden -> sehr langer Prompt
8. GPT soll Gesprächspartner anhand der Profile finden udn wieder von vorn (Sprechen, Suchen, Meinung)
"""
""" # entfernen
##example use für chroma queries:
##nimm an, ein Participant heißt "Elon Musk", das topic ist "Techno" , das research_result ist "Techno ist geil")
write_knowledge_collection("Elon Musk", "techno", "techno ist geil")
###das erzeugt die collection: ElonMuskKnowledge - Collections dürfen keine Sonderzeichen enthalten. Die Leerzeichen im Namen werden in der Methode entfernt
###das namensscheme wird immer so sein: VornameNachnameKnowledge
###diese collection kann wie folgt angefragt werden:
result = query_knowledge_collection('Elon Musk', 'techno', 'Knowledge')
###merke: der name kann mit leerzeichen übergeben werden. auch ist kenntnis vom namen der collection (bisher) unnötig
###wegen der verarbeitung in einer anderen methode muss das ergebnis noch extrahiert werden
print(result['documents'][0])
print(len(result['documents'][0]))
###gibt: ['techno ist geil']
###ACHTUNG: die Strings sind case - sensitive: schreibe ich 'Techno'statt 'techno' kommt nichts zurück
###noch im prototyp status: sammelt der participant noch mehr wissen zu dem thema:
write_knowledge_collection("Elon Musk", "techno", "auf technoparties werden viele drogen genommen")
result = query_knowledge_collection('Elon Musk', 'techno', 'Knowledge')
print(result['documents'][0])

###wertet aus zu: ['techno ist geil\nauf technoparties werden viele drogen genommen']
### der participant erweitert also sein wissen - dieses wissen könnte in einen prompt gegeben werden.
### ich werde versuchen, das mit der convictions collection ähnlich zu machen - aber da braucht es noch einen kniff für die
###überzeugung
""" # entfernen

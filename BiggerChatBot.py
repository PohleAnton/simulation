import streamlit as st
import json
import os
from datetime import datetime
import chromadb
import openai
import yaml
from pathlib import Path
import random
from chromadb.utils import embedding_functions


openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')
model = "gpt-3.5-turbo-1106"
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=openai.api_key,
    model_name="text-embedding-ada-002"
)


#chroma = chromadb.Client()
chroma = chromadb.HttpClient(host='localhost', port=8000, tenant="default_tenant", database='default_database')

def collection_exists(chroma_client, collection_name):
    try:
        chroma_client.get_collection(name=collection_name)
        return True
    except Exception:
        return False
public_discussions=None
if not collection_exists(chroma, "public_discussions"):
    public_discussions = chroma.create_collection(name="public_discussions", embedding_function=openai_ef)
else:
    public_discussions = chroma.get_collection(name='public_discussions')
participant_collection=None
if not collection_exists(chroma, "participants"):
    participant_collection = chroma.create_collection(name="participants")
else:
    participant_collection = chroma.get_collection('participants')

first_finished = False
all_topics = []
# um google request zu sparen:
wiki_results = {}
all_on_board = False
all_against = False

token_saver = ({
    "conversation": "Roger: (approaching Elon at the New Year's Eve party) Well, well, well, if it isn't the man who believes he's going to colonize Mars before I figure out the true nature of the universe.\n\nElon: (smirking) Always a pleasure to see you, Roger. I see you're still trying to crack the code of consciousness and the cosmos. Good luck with that.\n\nRoger: (rolling his eyes) Oh please, don't act like your endeavors in space exploration and artificial intelligence are any less ambitious or quixotic. You may get to Mars, but I will unravel the mysteries of the universe before you even set foot on the red planet.\n\nElon: (leaning in, a glint of determination in his eye) You may be a genius in mathematical physics, but I'm the one making history with SpaceX and Tesla. My innovations will change the world as we know it.\n\nRoger: (chuckling) Change the world? I'm more interested in understanding the very fabric of reality itself. Have you ever considered the possibility that we could be living in a simulation?\n\nElon: (frowning) Ah, the old simulation hypothesis. It's an intriguing idea, but I prefer to focus on tangible, practical advancements. Who cares if we're living in a simulation if we can't even make sustainable energy a reality?\n\nRoger: (leaning back, taking a sip of his drink) Ah, there it is - your obsession with practicality and material progress. But what about the deeper questions, Elon? What about the nature of our consciousness and its connection to the universe?\n\nElon: (leaning in, his voice low and intense) Consciousness is just a byproduct of our neural networks. It's all about the algorithms and code. Once we crack the code, we can enhance and even manipulate consciousness itself. It's all about the tech, Roger.\n\nRoger: (shaking his head, a hint of frustration creeping into his voice) You can't reduce consciousness to mere algorithms and code, Elon. There's something deeper at play here, something that transcends the physical world. We need to look beyond the material and embrace the mysteries of the cosmos.\n\nElon: (raising an eyebrow) Mysteries of the cosmos, you say? Well, while you're off pondering the mysteries, I'll be out there in the real world, making things happen. Let's agree to disagree, shall we?\n\nRoger: (sighing) Fine, Elon. But just remember, while you're focused on Mars and AI, I'll be here, pushing the boundaries of human understanding. Here's to another year of our intellectual sparring, old friend.\n\nElon: (smirking) Cheers to that, Roger. Let's see who comes out on top in the end.",
    "themes": [
        {
            "theme": "Space Exploration",
            "content": "Roger: (approaching Elon at the New Year's Eve party) Well, well, well, if it isn't the man who believes he's going to colonize Mars before I figure out the true nature of the universe. Elon: (leaning in, a glint of determination in his eye) You may be a genius in mathematical physics, but I'm the one making history with SpaceX and Tesla. My innovations will change the world as we know it."
        },
        {
            "theme": "Consciousness and Reality",
            "content": "Elon: I see you're still trying to crack the code of consciousness and the cosmos. Good luck with that. Roger: What about the nature of our consciousness and its connection to the universe? Elon: Consciousness is just a byproduct of our neural networks. It's all about the algorithms and code. Once we crack the code, we can enhance and even manipulate consciousness itself. It's all about the tech, Roger. Roger: You can't reduce consciousness to mere algorithms and code, Elon. There's something deeper at play here, something that transcends the physical world. We need to look beyond the material and embrace the mysteries of the cosmos."
        },
        {
            "theme": "Artificial Intelligence",
            "content": "Roger: Oh please, don't act like your endeavors in space exploration and artificial intelligence are any less ambitious or quixotic. Elon: Consciousness is just a byproduct of our neural networks. It's all about the algorithms and code. Once we crack the code, we can enhance and even manipulate consciousness itself."
        },
        {
            "theme": "Simulation Hypothesis",
            "content": "Roger: Have you ever considered the possibility that we could be living in a simulation? Elon: Ah, the old simulation hypothesis. It's an intriguing idea, but I prefer to focus on tangible, practical advancements. Who cares if we're living in a simulation if we can't even make sustainable energy a reality?"
        }
    ]
})

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
                    "description": "First person perspective of the participant, Inner most believe of a participant about a subject. Radical, emotional and subjective"
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
                    "description": "First person perspective of the participant. New description of inner most thoughts about a subject. Based on prior conviction and arguments. Can be more nuanced and subtle."
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


def get_convincing_factors():
    dir_name = 'stepBackStuff/txtFiles/ConvincingFactors'
    file_name = 'ConvincingFactors.txt'
    current_dir = Path(__file__).parent
    dir_path = current_dir / dir_name
    file_path = dir_path / file_name

    if not dir_path.exists():
        dir_path.mkdir(parents=True)

    if file_path.exists():
        with open(file_path, 'r') as file:
            content = file.read()
            return content
    else:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": criteria_prompt}
            ]
        )
        raw = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": f"extract_headings from {response['choices'][0]['message']['content']}"}
            ],
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


def get_stratey():
    dir_name = 'stepBackStuff/txtFiles/ConvincingStrategies'
    file_name = 'Strategies.txt'
    current_dir = Path(__file__).parent
    dir_path = current_dir / dir_name
    file_path = dir_path / file_name

    if not dir_path.exists():
        dir_path.mkdir(parents=True)

    if file_path.exists():
        with open(file_path, 'r') as file:
            content = file.read()
            bullet_points_list = content.split('\n')
            random_bullet_points = random.sample(bullet_points_list, 3)
            random_bullet_points_string = '\n'.join(random_bullet_points)
            return random_bullet_points_string
    else:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": strategies_prompt}
            ]
        )
        raw = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user", "content": f"extract_headings from {response['choices'][0]['message']['content']}"}
            ],
            functions=functions
        )
        try:
            points_json = json.loads(raw)
        except json.JSONDecodeError:
            points_json = json.dumps(raw)
        points = points_json['headings']
        with open(file_path, 'w') as file:
            file.write(points)
        bullet_points_list = points.split('\n')
        random_bullet_points = random.sample(bullet_points_list, 3)
        random_bullet_points_string = '\n'.join(random_bullet_points)
        return random_bullet_points_string


def read_from_file(file_path):
    with open(file_path, 'r') as file:
        content = file.read()
    return content


def get_gpt_response(content):
    # print(Research.segregation_str, "Content for Message:", content)
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


def compare_themes(prior_topic, new_topics):
    updated_topics = []
    for new in new_topics:
        replaced = False
        for prior in prior_topic:
            judge = openai.ChatCompletion.create(
                model=model,
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
    print(f"HOLE ID DER ÜBERZEUGUNG für: {participant} zu {topic}")
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
    print("immernoch vor bug")
    try:
        structured_data = json.loads(content)
    except json.decoder.JSONDecodeError:
        structured_data = json.dumps(content)
    return structured_data


def write_conviction_collection(participant, topic, arguments=''):
    #ToDo: Note to self: mit update_conviction zusammenfassen?
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    found_collection = False
    for collection in chroma.list_collections():
        if collection.name == collection_name:
            print("Collection wurde gefunden")
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
                    final = res_json['conviction']
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
                    final = res_json['conviction']
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
                final = res_json['conviction']
                print("Hier sind wa schon ma")
                try:
                    globals()[collection_name].add(documents=final,
                                               metadatas={'theme': topic}, ids=topic + timestamp_string)
                except KeyError:
                    print(f"KeyError beim Aufruf der Collection {collection_name}")

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
        if 'collections' not in st.session_state:
            st.session_state['collections'] = {}
        if collection_name not in st.session_state['collections']:
            st.session_state['collections'][collection_name] = chroma.create_collection(collection_name)
        st.session_state['collections'][collection_name].add(documents=final, metadatas={'theme': topic},
                                                             ids=topic + timestamp_string)
        #globals()[collection_name] = chroma.create_collection(collection_name)
        #globals()[collection_name].add(documents=final, metadatas={'theme': topic}, ids=topic + timestamp_string)


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
def extract_topics_of_conversation(given_conversation):
    global first_finished
    global all_topics
    conversation_topics = []
    chroma_metadatas = []
    chroma_documents = []
    chroma_ids = []
    #zum token sparen wird mitunter direkt string übergeben:
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
        #given_topics = ','.join(theme['theme'] for theme in structured_data['themes'])
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

    if not first_finished:
        print(new_data)
        for theme in new_data["themes"]:
            conversation_topics.append(theme['theme'])
            all_topics.append(theme['theme'])
            chroma_ids.append(start_number)
            start_number += 1
            chroma_documents.append(theme['content'])
            chroma_metadatas.append({'theme': theme['theme'], 'issue': find_core_issues(theme['theme'])})

        chroma_ids = [str(id) for id in chroma_ids]
        public_discussions.add(documents=chroma_documents, metadatas=chroma_metadatas, ids=chroma_ids)
        first_finished = True

        return conversation_topics

    if first_finished:

        proto_topics = []
        for theme in new_data["themes"]:
            proto_topics.append(theme["theme"])
        new_topics = compare_themes(all_topics, proto_topics)
        print(data)
        for index, theme in enumerate(data["themes"]):
            if index < len(new_topics):
                theme["theme"] = new_topics[index]
        for theme in new_data["themes"]:
            conversation_topics.append(theme['theme'])
            if theme['theme'] not in all_topics:
                all_topics.append(theme['theme'])
            chroma_ids.append(start_number)
            start_number += 1
            chroma_documents.append(theme['content'])
            chroma_metadatas.append({'theme': theme['theme'], 'issue': find_core_issues(theme['theme'])})

        public_discussions.add(documents=chroma_documents, metadatas=chroma_metadatas, ids=chroma_ids)

        return conversation_topics

def add_knowledge_to_profile(participant, given_topics):
    global wiki_results
    global all_topics
    knows = []
    unknown = []
    for item in given_topics:
        unknown.append(item)
    for topic in given_topics:
        if topic in wiki_results:
            unknown.remove(topic)
            knows.append(topic)

    # ToDO TESTING ONLY - THIS CAN stay here though
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


def get_prior_discussion(topic):
    # ToDo: Note to self: Vielleicht kann ich die query public discussions Methoden zusammenschrumpfen. Noch sind sie einzeln. Man weiß ja nie...
    r = get_best_document(topic, True, 0.4)
    combined_string = "\n".join(r) if len(r) > 1 else r[0]
    return combined_string


def form_argument(speaker, chosen_topic, believe):
    strategy = get_stratey()
    speaker_conviction=get_latest_conviction(speaker, chosen_topic)
    prior_discussions=get_prior_discussion(chosen_topic)
    if 'yes' in believe.lower():
        speaker_argument = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "user",
                "content": f"form_argument using one or more of these techniques: {strategy} about {chosen_topic} based on {speaker_conviction}. This was said before:{prior_discussions}"}
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
                 "content": f"form_counterargument using one or more of these techniques: {strategy} about {chosen_topic} based on {speaker_conviction}. This was said before:{prior_discussions}"}
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
            {"role": "system", "content": "you are a binary judge that answers questions only with yes or no. You only say yes when you are REALLY convinced"},
            {"role": "user",
             "content": f"Based on this conviction: {conv}, how would you answer {issue}?"}
        ],
    )
    response = judge['choices'][0]['message']['content']
    return response

def update_conviction(participant, topic, new_conviction):
    collection_name = participant.replace(' ', '') + 'Conviction'
    timestamp_string = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(collection_name + topic +topic + timestamp_string )
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

def lets_goooooo(participants,chosen_topic):
    global all_on_board
    global all_against
    all_against = True
    all_on_board = True
    for participant in participants:
        res = judge_concivtion(participant,chosen_topic)

        if 'no' in res.lower():
            all_on_board = False

        if 'yes' in res.lower():
            all_against = False

    return all_on_board, all_against


def next_conversation(given_chosen_topic=""):
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
                if 'yes' in judge_concivtion(item, given_chosen_topic).lower():
                    pros.append(item)
                else:
                    contras.append(item)

        for speaker in pros:
            start_number = public_discussions.count() + 1
            speaker_argument = form_argument(speaker, given_chosen_topic, 'yes')
            print(speaker_argument)
            for listener in contras:
                new_listener_conviction = argument_vs_conviction(speaker_argument, listener, given_chosen_topic)
                print(new_listener_conviction)
            public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                   metadatas={'theme': given_chosen_topic, 'issue': get_yes_or_no(given_chosen_topic)})

        for listener in contras:
            if 'yes' in judge_concivtion(listener, given_chosen_topic).lower():
                contras.remove(listener)
                pros.append(listener)
            listener_argument = form_argument(listener, given_chosen_topic, 'no')
            print(listener_argument)
            for speaker in pros:
                new_speaker_conviction = argument_vs_conviction(listener_argument, speaker, given_chosen_topic)
            public_discussions.add(documents=speaker_argument, ids=str(start_number),
                                   metadatas={'theme': given_chosen_topic, 'issue': get_yes_or_no(given_chosen_topic)})

        for speaker in pros:
            if 'no' in judge_concivtion(speaker, given_chosen_topic).lower():
                pros.index(speaker)
                contras.append(speaker)

        # #in Form von: {speaker} says: (Damit der Name zwar im Frontend, aber nicht im eigentlichen Prompt
        # auftaucht) {argument}
        new_listener_conviction = argument_vs_conviction(speaker_argument, listener, given_chosen_topic)

        all_on_board, all_against = lets_goooooo(participants_list, given_chosen_topic)
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

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

all_on_board = False
profile_scheme = read_from_file('./FocusedConversationApproach/txtFiles/scheme.txt')

prompt = (
    "Write a conversation with the following setup: "
    "1. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
    "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "2. Long and detailed conversation. "
    "3. Setting: At the beach. Everybody is relaxed "
    "4. Topic: The Simulation Hypothesis and its implications"
    "5. Involved Individuals: "
)


def start_first_conversation():
    fill_profile_schemes_for_participants(participants_list)
    prompt_for_first_conversation = prompt + join_profiles(participants_list)
    first_conversation_res = get_gpt_response(prompt_for_first_conversation)
    first_conversation_str = get_response_content(first_conversation_res)

    extracted_topics = extract_topics_of_conversation(first_conversation_res)
    for participant in participants_list:
        add_knowledge_to_profile(participant, extracted_topics)

    return first_conversation_str


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
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            first_conv_str = start_first_conversation()
            full_response += first_conv_str
            message_placeholder.markdown(full_response)
    if user_input_prompt == "End" or user_input_prompt == "end":
        st.markdown("kp was jz passiert, aber irgendwie muss das ganze hier beendet werden. Mach ma")
    else:
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""
            first_conv_str = start_first_conversation()
            full_response += first_conv_str
            message_placeholder.markdown(full_response)
        next_conversation(user_input_prompt)

# TODO: wie endet die Conversationskette? Userinput oder automatisch?

import datetime
import json
import os
import random
import chromadb
import openai
import yaml
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma

# from FocusedConversationApproach.GeneratePersons import functions as gp_functions

# Teile des GPT-Codes und der ganze Chroma und txt Code kommt von Anton (hier reinkopiert)
# Logik, Ablauf, Kürzungen, Methoden etc. von mir
__author__ = "Sebastian Koch"
__credits__ = ["Sebastian Koch", "Anton Pohle"]

from NetworkApproach import Research2 as Research

# API Key konfigurieren
openai.api_key = yaml.safe_load(open("config.yml")).get('KEYS', {}).get('openai')
chroma = chromadb.Client()
public_discussions = chroma.create_collection(name="public_discussions")
participant_collection = chroma.create_collection(name="participants")

functions = [
    {
        "name": "structure_conversation",
        "description": "A function divides a conversation by its themes, finds subtitles for each theme, and summarizes what each participant had to say about that subject",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Brief description of the conversation and who took part"
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
                            },
                            "content": {
                                "type": "array",
                                "description": "What each participant said about that subject",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name of the participant. Write like this: {name} thinks:"
                                        },
                                        "summary": {
                                            "type": "string",
                                            "description": "Summary of what they said about that topic. Start like this: \"I think...\""
                                        },
                                        "liking": {
                                            "type": "string",
                                            "description": "How much the participant liked that part of the conversation on a scale from 1 - 5, 1 being the lowest, 5 the highest score. Always write like this:  {name} gives it a {rating}"
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
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
                    "description": "Write a short text what this person might know about this subject. Write in first person perspective."
                }
            }
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


"""
def get_filled_knowledge_scheme_for_participant(participant, given_topics):
    # file_path = knowledge_directory + "/" + get_file_name(participant)
    input_content = (f"organize_knowledge of {given_topics} for {participant}")
    response = get_gpt_response_with_function(input_content, functions)
    filled_knowledge_scheme = get_response_content(response)
    # write_in_file(file_path, knowledge, "x") # erstellt neue Datei
    print(Research.segregation_str, f"Knowledge scheme for : {participant}\n\n", filled_knowledge_scheme)
    return filled_knowledge_scheme
"""


def add_knowledge_to_profile(participant, given_topics):
    knows = []
    unknown = given_topics
    for topic in given_topics:
        if has_participant_knowledge(participant, topic):
            unknown.remove(topic)
            knows.append(topic)

    for topic in unknown:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-1106",
            messages=[
                {"role": "user", "content": f"generate_knowledge for {participant} about the topic {topic}"}
            ],
            functions=functions
        )
        print(response["choices"][0]["message"]["function_call"]["arguments"])

        make_and_or_use_knowledge_collection(participant, topic, clean_knowledge(response["choices"][0]["message"]["function_call"]["arguments"]) )

    topic_results = organize_wiki_search(unknown)
    print(participant)
    print(topic_results)
    for topic, research_result in topic_results.items():
        make_and_or_use_knowledge_collection(participant, topic, research_result)




# Sucht sich die Themen raus, über die der participant zusätzliches Wissen hat.
# Zustäzliches Wissen ist alles, was der participant auf jeden Fall kennt
# (alle Gesprächsthemen, von denen die GPT glaubt, der participant mit dem Profil könnte sie kennen,
# und dann auch die worüber er nicht so viel wissen sollte, weil er diese ja dann bei Wikipedia sucht)
def get_additional_knowledge_of_participant(participant):
    knowledge_file_path = knowledge_directory + "/" + get_file_name(participant)
    participant_profile = read_from_file(knowledge_file_path)
    knowledge = participant_profile.split("Additional Knowledge:")[1]
    topic_list = knowledge.split(",")
    topic_list = [topic.strip() for topic in topic_list]
    # print(Research.segregation_str, f"Necessary Wiki Files:\n{topic_list}")
    return topic_list


# ruft den Inhalt aller benötigter Wiki-Files ab
def get_content_of_wiki_files(given_topics):
    end_content = []

    # Wiki-Artikel abrufen
    for topic in given_topics:
        wiki_file_path = wiki_directory + "/" + get_file_name(topic)
        if does_file_exists(wiki_file_path):
            end_content.append(read_from_file(wiki_file_path))
    # print(Research.segregation_str, f"Content of necessary Wiki Files:\n")
    for content in end_content:
        print('')

    return "\n\n".join(end_content)


def does_file_exists(file_path):
    exists = os.path.isfile(file_path)
    return exists


# Fügt die Profile der Gesprächsteilnehmer zusammen
def join_profiles(participants):
    profiles_of_participants = ""
    for participant in participants:
        file_path = profile_directory + "/" + get_file_name(participant)
        profile_to_add = "("
        if does_file_exists(file_path):
            profile_to_add = read_from_file(file_path)
        profiles_of_participants += profile_to_add
        profiles_of_participants += ")\n\n"
    return profiles_of_participants


# sucht das passendste Dokument zur query raus
def get_best_document(given_query):
    documents = unsplit_for_retrieval.similarity_search(given_query)
    return documents[0].page_content


# ehrlich kp was das macht, frag mal Anton
def create_and_write_chroma_for_conversation(given_conversation):
    conversation = text_splitter.split_text(get_response_content(given_conversation))
    # print(Research.segregation_str, "Conversation - Splitter\n", conversation)
    return Chroma.from_texts(texts=given_conversation, embedding=embeddings)


# extrahiert den Content einer GPT-Response
def get_response_content(given_response):
    return given_response.choices[0].message.content


# Extrahiert die Arguments (nach Function Call) aus GPT-Response
def get_response_arguments(given_response):
    return given_response.choices[0].message.function_call.arguments


# baut ein Prompt mit allen nötigen Infos zusammen, das muss noch getestet und ausgewertet werden, nur ne Idee
def build_prompt_to_continue_conversation(given_participants):
    relationships = ["have known each other for a long time", "have known each other for one day"]
    liking = ["don’t like", "like", "tolerate", "hate"]
    linking_strength = ["very much", "", "much", "a bit", "on professional level"]
    place = ["At the beach", "At a small bar", "At university"]
    feeling = ["relaxed", "aggressive"]

    chosen_relationship = get_random_element_from_list(relationships)
    chosen_liking = get_random_element_from_list(liking)
    chosen_liking_strength = get_random_element_from_list(linking_strength)
    chosen_place = get_random_element_from_list(place)
    chosen_feeling = get_random_element_from_list(feeling)

    necessary_topics = []
    for participant in given_participants:
        necessary_topics += get_additional_knowledge_of_participant(participant)

    necessary_content = get_content_of_wiki_files(necessary_topics)

    participants_str = join_profiles(given_participants)
    necessary_content_str = f"Here are some summaries for the additional knowledge:\n {necessary_content}"

    builded_prompt = " ".join([
        "Write a conversation with the following setup:"
        "1. Informal, emotional conversation between people who",
        chosen_relationship,
        "and",
        chosen_liking,
        "each other",
        chosen_liking_strength,
        ". They enjoy intense intellectual arguments and do not hold back. Deep Talk"
        "2. Long and detailed conversation."
        "3. Setting:",
        chosen_place,
        ". Everybody is",
        chosen_feeling,
        ". 5. Involved Individuals:",
        participants_str,
        necessary_content_str]
    )

    return builded_prompt


# nur für den Bau eines zufälligen Prompts benötigt, sucht halt irgendein Element aus der Liste raus
def get_random_element_from_list(given_list):
    chosen = given_list[random.randrange(len(given_list))]
    return chosen


# Antons Code zum Strukturieren der Conversation
def get_structured_conversation_with_gpt(given_conversation):
    vector_test = get_gpt_response_with_function('structure_conversation'
                                                 + get_response_content(given_conversation),
                                                 functions)

    content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
    print("immernoch vor bug")
    # print(content)
    structured_data = json.loads(content)
    # print(Research.segregation_str, "structured_data - Content:\n", content)
    return structured_data


# Sucht sich die Themen der Conversation zusammen
def extract_topics_of_conversation(given_conversation):
    print('vor bug?')
    data = get_structured_conversation_with_gpt(given_conversation)
    # print_json_in_pretty(data)
    print('after bug')
    conversation_topics = []
    chroma_metadatas = []
    chroma_documents = []
    chroma_ids = []
    # möglicherweise muss es else public_discussions.count() + 1 sein
    start_number = 1 if public_discussions.count() == 0 else public_discussions.count() + 1

    # print(Research.segregation_str, "Themes:\n")
    for theme in data["themes"]:
        conversation_topics.append(theme['theme'])
        # print(theme, ", ")
        chroma_ids.append(start_number)
        start_number += 1
        if 'liking' in theme['content'][0]:
            chroma_documents.append(
                '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]} {entry["liking"]}' for entry in theme["content"]]))
        else:
            chroma_documents.append(
                '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]}' for entry in theme["content"]]))

        chroma_metadatas.append({'theme': theme['theme']})

        # add chroma stuff:
    chroma_ids = [str(id) for id in chroma_ids]
    # print(chroma_ids)
    public_discussions.add(documents=chroma_documents, metadatas=chroma_metadatas, ids=chroma_ids)
    return conversation_topics


# Gibt n Json einfach schöner aus
def print_json_in_pretty(given_json):
    pretty_json_str = json.dumps(given_json, indent=4)
    # print(Research.segregation_str, "JSON in pretty:\n\n", pretty_json_str)


def organize_wiki_search(given_topics):
    topic_results = {}
    for topic in given_topics:
        researched_with_wiki, research_result = Research.try_wiki_search(topic)
        if researched_with_wiki:
            topic_results[topic] = research_result
        else:
            print(Research.segregation_str,
                  f"There will be no file for {topic} due to lack of a Wikipedia-article.")
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


def make_and_or_use_knowledge_collection(participant, topic, research_result):
    collection_name = participant.replace(' ', '') + 'Knowledge'

    # suche, ob der participant bereits wissen zu dem thema hat:
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
    ###wahrscheinlich überflüssig, es kommt sonst ohnehin leeres array zurück
    # if not found_collection or not result['documents'][0]:
    # result = participant + ' does not know anything about ' + topic
    # return result


###für den prompt
def get_string_from_knowledge(participant, topic):
    res = query_knowledge_collection(participant, topic)
    if len(res['documents'][0]) == 1:
        return res['documents'][0][0]
    else:
        return participant + ' does not know anything about ' + topic


###das wäre das ganze akumulierte wissen von participant zu topic
# knowledge_for_prompt = get_string_from_knowledge('Elon Musk', 'techno')


def make_and_or_use_conviction_collection(participant):
    collection_name = participant.replace(' ', '') + 'Conviction'
    for collection in chroma.list_collections():
        if collection.name == collection_name:
            globals()[collection_name].add()
            globals()[collection_name].add()
        else:
            globals()[collection_name] = chroma.create_collection(collection_name)
            globals()[collection_name].add()


def has_participant_knowledge(participant, topic):
    res = query_knowledge_collection(participant, topic)
    if res and res['documents'] and res['documents'][0]:
        return True
    else:
        return False


def clean_knowledge(original_string):
    substrings_to_remove = ["}", ":", "\"knowledge\"", "{"""]

    for substring in substrings_to_remove:
        original_string = original_string.replace(substring, "")

    return original_string


##example use:
##nimm an, ein Participant heißt "Elon Musk", das topic ist "Techno" , das research_result ist "Techno ist geil")
make_and_or_use_knowledge_collection("Elon Musk", "techno", "techno ist geil")
###das erzeugt die collection: ElonMuskKnowledge - Collections dürfen keine Sonderzeichen enthalten. Die Leerzeichen im Namen werden in der Methode entfernt
###das namensscheme wird immer so sein: VornameNachnameKnowledge
###diese collection kann wie folgt angefragt werden:
result = query_knowledge_collection('Elon Musk', 'techno')
###merke: der name kann mit leerzeichen übergeben werden. auch ist kenntnis vom namen der collection (bisher) unnötig
###wegen der verarbeitung in einer anderen methode muss das ergebnis noch extrahiert werden
print(result['documents'][0])
print(len(result['documents'][0]))
###gibt: ['techno ist geil']
###ACHTUNG: die Strings sind case - sensitive: schreibe ich 'Techno'statt 'techno' kommt nichts zurück
###noch im prototyp status: sammelt der participant noch mehr wissen zu dem thema:
make_and_or_use_knowledge_collection("Elon Musk", "techno", "auf technoparties werden viele drogen genommen")
result = query_knowledge_collection('Elon Musk', 'techno')
print(result['documents'][0])

###wertet aus zu: ['techno ist geil\nauf technoparties werden viele drogen genommen']
### der participant erweitert also sein wissen - dieses wissen könnte in einen prompt gegeben werden.
### ich werde versuchen, das mit der convictions collection ähnlich zu machen - aber da braucht es noch einen kniff für die
###überzeugung


# GPT und Txt Zeug, Konstanten festlegen
initial_participants = ['Karl Marx', 'Peter Thiel', 'Elon Musk']
test_participants = ['Horst Schlemmer', 'Rainer Zufall']
profile_directory = 'NetworkApproach/txtFiles/Profiles'
os.makedirs(profile_directory, exist_ok=True)
chunk_directory = 'NetworkApproach/txtFiles/ConversationChunks'
os.makedirs(chunk_directory, exist_ok=True)
wiki_directory = 'NetworkApproach/txtFiles/WikiSearches'
os.makedirs(wiki_directory, exist_ok=True)
knowledge_directory = 'NetworkApproach/txtFiles/Knowledge'
os.makedirs(knowledge_directory, exist_ok=True)
# target = './FocusedConversationApproach/txtFiles/generatedProfiles/used/'
timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
profile_scheme = read_from_file('FocusedConversationApproach/txtFiles/scheme.txt')

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

# Beginn des Programmablaufes
# Schemas ausfüllen
fill_profile_schemes_for_participants(initial_participants)

# erste Conversation erstellen
prompt_for_first_conversation = prompt_p1 + join_profiles(initial_participants)
first_conversation = get_gpt_response(prompt_for_first_conversation)
print(Research.segregation_str, "Response - Content", get_response_content(first_conversation))

# Suche bei Wikipedia anstoßen
extracted_topic = extract_topics_of_conversation(first_conversation)

top = ["Mushrooms"]
fill_profile_schemes_for_participants(initial_participants)

# Knowledge hinzufügen
for participant in initial_participants:
    add_knowledge_to_profile(participant, top)
print('fertig')

res=query_knowledge_collection('Elon Musk', 'Mushrooms')

# weiteres Gespräch vorbereiten
# ... (das unten ist noch aus der ersten Version, kp ob das noch funzt

# das erste - also am besten passende dokument - aus dieser Suche ist:
query = "What was said about simulation hypothesis?"
document = get_best_document(query)

# zweite Conversation erstellen (alt)
prompt_p3 = (
        build_prompt_to_continue_conversation(initial_participants)
        + " consider what they talked about before: ' + document")
# Number of participant in participant Array needed
sequel = get_gpt_response(prompt_p3)
print(Research.segregation_str, "Response - Content", get_response_content(sequel))

"""
TODO:
1. Ergebnisse zu den Themen (research_result_list) als eine Collection speichern
2. Metadaten der gesuchten Themen aus Liste (Thema + Namen all derer, die es recherchiert haben)
3. Inhalt der einzelnen Dokumente: Content aus Liste
4. Sobald 2 Personen eine Konversation beendet haben, werden die Themen gesucht und entsprechend in die DB geschrieben
5. Dauerschleife bzw. öfters wiederholen
6. zur Generierung der neuen Konversationen sollte das Wissen (inklusive Recherche) mitgegeben werden -> sehr langer Prompt
7. Conversation Chunks werden im Format "timpestamp_<participants>" gespeichert, dann werden alle Gespräche rausgesucht, in denen das gesuchte Thema vorgekommen ist und geprüft, was die letzte Meinung (likin) zu diesem Thema war"
8. GPT soll Gesprächspartner anhand der Profile finden udn wieder von vorn (Sprechen, Suchen, Meinung)
"""

# altes Datenbank Zeug
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
directory = 'FocusedConversationApproach/txtFiles/ConversationChunks'
target_dir = 'FocusedConversationApproach/txtFiles/ConversationChunks/used/'
os.makedirs(directory, exist_ok=True)
loader = DirectoryLoader(directory, glob="./*.txt", loader_cls=TextLoader)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
# Konversation in Chunks packen
unsplit_for_retrieval = create_and_write_chroma_for_conversation(first_conversation)

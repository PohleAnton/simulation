import datetime
import json
import os
import random

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

gp_functions = [
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
]


def get_gpt_response_with_function(content, functions):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user", "content": content}
        ],
        functions=functions
    )
    return response


def get_gpt_response(content):
    print(Research.segregation_str, "Content for Message:", content)
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


def get_file_name(participant):
    modified_name = participant.replace(" ", "_")
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
        # Prüfen, ob bereits ein Profil für denjenigen vorliegt, falls nein, dann wir eines erzeugt
        file_path = profile_directory + "/" + get_file_name(participant)
        print(Research.segregation_str, f"File path: {file_path}")
        if not does_file_exists(file_path):
            # GPT generiert neues Profil
            input_content = profile_scheme + " for " + participant
            response = get_gpt_response(input_content)
            profile = get_response_content(response)
            write_in_file(file_path, profile, "x")
            print(Research.segregation_str, f"New profile for: {participant}\n", profile)
        else:
            print(Research.segregation_str, f"Profile for {participant} already exists")


def get_filled_knowledge_scheme_for_participant(participant, given_topics):
    # file_path = knowledge_directory + "/" + get_file_name(participant)
    input_content = (f"Organize these topics {given_topics} into the following scheme for {participant}!\n"
                     + knowledge_scheme)
    response = get_gpt_response(input_content)
    filled_knowledge_scheme = get_response_content(response)
    # write_in_file(file_path, knowledge, "x") # erstellt neue Datei
    print(Research.segregation_str, f"Knowledge scheme: {participant}\n\n", filled_knowledge_scheme)
    return filled_knowledge_scheme


def add_knowledge_to_profile(participant, given_knowledge):
    old_file_path = profile_directory + "/" + get_file_name(participant)
    new_file_path = knowledge_directory + "/" + get_file_name(participant)
    profile = read_from_file(old_file_path)
    do_know_str = "Topics with knowledge:"
    dont_know_str = "Topics without knowledge:"
    extracted_knowledge = given_knowledge.split(do_know_str)[1]
    extracted_knowledge = extracted_knowledge.split(dont_know_str)[0]
    research_knowledge = given_knowledge.split(dont_know_str)[1]
    extracted_knowledge = extracted_knowledge + ", " + research_knowledge

    research_list = [s.strip() for s in research_knowledge.split(",")]

    organize_wiki_search(research_list)

    additional_str = "Additional Knowledge:"
    if does_file_exists(new_file_path):
        to_write = ", " + extracted_knowledge
        write_in_file(new_file_path, to_write, "a")
    elif does_file_exists(old_file_path):
        to_write = profile + "\n" + additional_str + " " + extracted_knowledge
        write_in_file(new_file_path, to_write, "x")
    else:
        print(f"File doesn't exists, whether here {new_file_path} nor here {old_file_path}")


def does_file_exists(file_path):
    exits = os.path.isfile(file_path)
    if exits:
        print(Research.segregation_str, f"File \"{file_path}\" does exist")
    else:
        print(Research.segregation_str, f"File \"{file_path}\" doesn't exist")
    return exits


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


def get_best_document(given_query):
    documents = unsplit_for_retrieval.similarity_search(given_query)
    return documents[0].page_content


def create_and_write_chroma_for_conversation(given_conversation):
    conversation = text_splitter.split_text(get_response_content(given_conversation))
    print(Research.segregation_str, "Conversation - Splitter\n", conversation)
    return Chroma.from_texts(texts=given_conversation, embedding=embeddings)


def get_response_content(given_response):
    return given_response.choices[0].message.content


def build_prompt_for_conversation(given_participants):
    relationships = ["’ve known each other for a long time", "’ve known each other for one day"]
    liking = ["don’t like", "like", "tolerate", "hate"]
    linking_strength = ["very much", "", "much", "a bit", "on professional level"]
    place = ["At the beach", "At a small bar", "At university"]
    feeling = ["relaxed", "aggressive"]

    chosen_relationship = get_random_element_from_list(relationships)
    chosen_liking = get_random_element_from_list(liking)
    chosen_liking_strength = get_random_element_from_list(linking_strength)
    chosen_place = get_random_element_from_list(place)
    chosen_feeling = get_random_element_from_list(feeling)

    participants_str = ""
    for index in range(len(given_participants)):
        if index == 0:
            participants_str = given_participants[index]
        else:
            participants_str = participants_str + ", " + given_participants[index]

    builded_prompt = "".join([
        "Write a conversation with the following setup: "
        "1. Informal, emotional conversation between people who",
        chosen_relationship,
        " and ",
        chosen_liking,
        " each other ",
        chosen_liking_strength,
        ". They enjoy intense intellectual arguments and do not hold back. Deep Talk "
        "2. Long and detailed conversation. "
        "3. Setting: ",
        chosen_place,
        ". Everybody is ",
        chosen_feeling,
        ". 5. Involved Individuals: ",
        participants_str]
    )

    return builded_prompt


def get_random_element_from_list(given_list):
    chosen = given_list[random.randrange(len(given_list))]
    return chosen


def get_structured_conversation_with_gpt(given_conversation):
    vector_test = get_gpt_response_with_function('structure_conversation'
                                                 + get_response_content(given_conversation),
                                                 gp_functions)

    content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
    structured_data = json.loads(content)
    print(Research.segregation_str, "structured_data - Content:\n", content)
    return structured_data


def extract_possible_topics_for_wikipedia():
    conversation_topics = []

    print(Research.segregation_str, "Themes:\n")
    for theme in data["themes"]:
        conversation_topics.append(theme['theme'])
        print(theme, ", ")

    return conversation_topics


def print_json_in_pretty(given_json):
    pretty_json_str = json.dumps(given_json, indent=4)
    print(Research.segregation_str, "JSON in pretty:\n\n", pretty_json_str)


def organize_wiki_search(given_topics):

    for topic in given_topics:
        file_name = get_file_name(topic)
        file_path = wiki_directory + "/" + file_name

        # Falls das Thema noch nicht gespeichert ist
        if not does_file_exists(file_path):
            # Suche mit Research Klasse
            researched_with_wiki, research_result = Research.try_wiki_search(topic)
            print(Research.segregation_str, "Wiki Seite gefunden:", researched_with_wiki,
                  "\nResearch Result:", research_result)
            if researched_with_wiki:
                # Textfile erstellen
                write_in_file(file_path, f"Explanation:\n{research_result}\n", "w")
                print(Research.segregation_str, f"File {file_name} was created.")
            else:
                print(Research.segregation_str,
                      f"There will be no file for {topic} due to lack of a Wikipedia-article.")


# GPT und Txt Zeug
initial_participants = ['Karl Marx', 'Peter Thiel', 'Elon Musk']
test_participants = ['Horst Schlemmer', 'Rainer Zufall']
profile_directory = 'NetworkApproach/txtFiles/Profiles'
chunk_directory = 'NetworkApproach/txtFiles/ConversationChunks'
wiki_directory = 'NetworkApproach/txtFiles/WikiSearches'
knowledge_directory = 'NetworkApproach/txtFiles/Knowledge'
# target = './FocusedConversationApproach/txtFiles/generatedProfiles/used/'
timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
profile_scheme = read_from_file('FocusedConversationApproach/txtFiles/scheme.txt')
knowledge_scheme = read_from_file('NetworkApproach/txtFiles/knowledge_scheme.txt')
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
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
# Datenbank Zeug
directory = 'FocusedConversationApproach/txtFiles/ConversationChunks'
target_dir = 'FocusedConversationApproach/txtFiles/ConversationChunks/used/'
os.makedirs(directory, exist_ok=True)
loader = DirectoryLoader(directory, glob="./*.txt", loader_cls=TextLoader)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

# Beginn des Programmablaufes
# Schemas ausfüllen
fill_profile_schemes_for_participants(initial_participants)

# erste Conversation erstellen
prompt_for_first_conversation = prompt_p1 + join_profiles(initial_participants)
first_conversation = get_gpt_response(prompt_for_first_conversation)
print(Research.segregation_str, "Response - Content", get_response_content(first_conversation))

# Konversation in Chunks packen
data = get_structured_conversation_with_gpt(first_conversation)
print_json_in_pretty(data)

unsplit_for_retrieval = create_and_write_chroma_for_conversation(first_conversation)

# Suche bei Wikipedia anstoßen
extracted_topic = extract_possible_topics_for_wikipedia()
test_topics = ["Simulation Hypothesis", "Java programming language", "Marxism", "Pay Pal"]

# Knowledge hinzufügen
for participant_member in initial_participants:
    knowledge = get_filled_knowledge_scheme_for_participant(participant_member, test_topics)
    add_knowledge_to_profile(participant_member, knowledge)

# das erste - also am besten passende dokument - aus dieser Suche ist:
query = "What was said about simulation hypothesis?"
document = get_best_document(query)

# zweite Conversation erstellen
prompt_p3 = build_prompt_for_conversation(initial_participants) + ' consider what they talked about before: ' + document
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

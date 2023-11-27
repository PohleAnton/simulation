import json
import os
import random

import openai
import datetime

import yaml
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma

import Research

# from FocusedConversationApproach.GeneratePersons import functions as gp_functions

# Teile des GPT-Codes und der ganze Chroma und txt Code kommt von Anton (hier reinkopiert)
# Logik, Ablauf, Kürzungen, Methoden etc. von mir
__author__ = "Sebastian Koch"
__credits__ = ["Sebastian Koch", "Anton Pohle"]

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


def get_response_message(response):
    response_message = response.choices[0].message
    return response_message


def get_gpt_response(content):
    print(Research.segregation, "Content für Message:", content)
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user", "content": content}
        ]
    )
    return response


def get_participants_filepath():
    file_name = f"{timestamp}_{','.join(participants)}.txt"

    full_file_path = path + file_name
    # print(full_file_path)
    return full_file_path


def create_and_write_participants_file():
    full_file_path = get_participants_filepath()
    # Create and open the text file
    with open(full_file_path, 'w') as file:
        # Write some content to the file (optional)
        file.write("")


def fill_schemes_for_participants():
    for participant in participants:
        input_content = scheme + " for " + participant
        intro = get_gpt_response(input_content)
        with open(get_participants_filepath(), 'a') as file:
            file.write('\n')
            file.write('\n')
            file.write(intro.choices[0].message.content)


def get_scheme():
    with open('./FocusedConversationApproach/txtFiles/scheme.txt', 'r') as file:
        return file.read()


def read_participants_file():
    with open(get_participants_filepath(), 'r') as file:
        content = file.read()
        print(Research.segregation, "File Content:", content)
    return content


def get_best_document(given_query):
    documents = unsplit_for_retrieval.similarity_search(given_query)
    return documents[0].page_content


def create_and_write_chroma_for_conversation(given_conversation):
    conversations = text_splitter.split_text(given_conversation['choices'][0]['message']['content'])
    print(Research.segregation, "Conversation - Splitter", conversations)
    return Chroma.from_texts(texts=given_conversation, embedding=embeddings)


def get_response_content(given_conversation):
    return given_conversation.choices[0].message.content


def build_prompt_for_conversation(given_participants):
    relationships = ["’ve known each other for a long time", "’ve known each other for one day"]
    liking = ["don’t like", "like", "tolerate", "hate"]
    linking_strength = ["very much", "", "much", "a bit", "on professional level"]
    place = ["At the beach", "At a small bar", "At university"]
    feeling = ["relaxed"]

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
                                                 + given_conversation["choices"][0]["message"]["content"],
                                                 gp_functions)

    content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
    structured_data = json.loads(content)
    print(Research.segregation, "structured_data - Content:", content)
    return structured_data


def extract_possible_topics_for_wikipedia():
    conversation_topics = []

    print(Research.segregation, "Themes:\n")
    for theme in data["themes"]:
        conversation_topics.append(theme['theme'])
        print(theme, ", ")

    return conversation_topics


def write_wiki_in_file(file_path, wiki_content):
    with open(file_path, 'w') as file:
        file.write(wiki_content)


# GPT und Txt Zeug
participants = ['Karl Marx', 'Peter Thiel', 'Elon Musk']
path = './FocusedConversationApproach/txtFiles/generatedProfiles/'
target = './FocusedConversationApproach/txtFiles/generatedProfiles/used/'
timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
scheme = get_scheme()
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

# Schemas ausfüllen
fill_schemes_for_participants()
file_content = read_participants_file()

# erste Conversation erstellen
first_conversation = get_gpt_response(prompt_p1 + file_content)

print(Research.segregation, "Response - Content", get_response_content(first_conversation))

data = get_structured_conversation_with_gpt(first_conversation)
# zum Benennen
base_title = data["title"].replace(' ', '_')

# zum Extrahieren der Themen nötig
directory = './FocusedConversationApproach/txtFiles/ConversationChunks'
target_dir = './FocusedConversationApproach/txtFiles/ConversationChunks/used/'
os.makedirs(directory, exist_ok=True)

# Datenbank Zeug
loader = DirectoryLoader('./FocusedConversationApproach/txtFiles/ConversationChunks', glob="./*.txt",
                         loader_cls=TextLoader)
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
unsplit_for_retrieval = create_and_write_chroma_for_conversation(first_conversation)

# das erste - also am besten passende dokument - aus dieser Suche ist:
query = "What was said about simulation hypothesis?"
document = get_best_document(query)

# zweite Conversation erstellen
prompt_p3 = build_prompt_for_conversation(participants) + ' consider what they talked about before: ' + document
sequel = get_gpt_response(prompt_p3)
print(Research.segregation, "Response - Content", get_response_content(sequel))

extracted_topic = extract_possible_topics_for_wikipedia()

# Liste aus Dictionaries der Wiki-Suchen
research_result_list = Research.get_response_for_every_topic(extracted_topic, participants)
print(Research.segregation, "Suchergebnisse mit Metadaten", research_result_list)

"""
TODO:
1. Ergebnisse zu den Themen (research_result_list) als eine Collection speichern
2. Metadaten der gesuchten Themen aus Liste (Thema + Namen all derer, die es recherchiert haben)
3. Inhalt der einzelnen Dokumente: Content aus Liste
4. Sobald 2 Personen eine Konversation beendet haben, werden die Themen gesucht und entsprechend in die DB geschrieben
5. Dauerschleife bzw. öfters wiederholen
6. zur Generierung der neuen Konversationen sollte das Wissen (inklusive Recherche) mitgegeben werden -> sehr langer Prompt
"""
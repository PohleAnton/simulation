import json
import random

import chromadb
from chromadb.config import Settings
import os
import yaml
import openai

# KANN GELÖSCHT WERDEN WENN DAS SINNLOS IST WAS ZU VectorDB.py ERGÄNZT WURDE (ab 152 und zwischendurch was)


# zum Mitdenken:

#so funktioniert das mit dem Persistieren nicht, wohl aber die ausführung
client = chromadb.Client(Settings(

    persist_directory="musk_jobs"
))

collection = client.create_collection(name="musk_jobs")

with open('./Conversations/musk_jobs.txt', 'r') as file:
    conversation = file.read()

config = yaml.safe_load(open("config.yml"))
openai.api_key = config.get('openai')

print(openai.api_key)

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
                                "description": "Each theme that has been brought up"
                            },
                            "content": {
                                "type": "array",
                                "description": "What each participant said about that subject",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string",
                                            "description": "Name of the participant"
                                        },
                                        "summary": {
                                            "type": "string",
                                            "description": "Summary of what they said about that topic"
                                        }
                                    }
                                }
                            },
                            "evaluation": {
                                "type": "string",
                                "description": "Evaluate the importance of that topic",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "importance": {
                                            "type": "string",
                                            "description": "Was that topic important, neutral or irrelevant"
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

vector_test = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": conversation}
    ]
    ,
    functions=functions,
    function_call={'name': 'structure_conversation'},

)

content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
data = json.loads(content)
print(content)

base_title = data["title"].replace(' ', '_')

directory = './Conversations/txtfiles'
os.makedirs(directory, exist_ok=True)

importance_list = []
for theme in data["themes"]:
    theme_title = theme["theme"].replace(' ', '_').replace('\'', '').replace('\"', '').replace('?', '')
    filename = f"{base_title}_{theme_title}.txt"
    file_path = os.path.join(directory, filename)
    content = '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]}' for entry in theme["content"]])
    importance_list.append(theme["theme"]["evaluation"]["importance"])

    # Saving to a file
    with open(file_path, 'w') as file:
        file.write(content)


def read_files_from_folder(folder_path):
    file_data = []

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".txt"):
            with open(os.path.join(folder_path, file_name), 'r') as file:
                content = file.read()
                file_data.append({"file_name": file_name, "content": content})

    return file_data


file_data = read_files_from_folder(directory)

documents = []
metadatas = []
ids = []

for index, data in enumerate(file_data):
    documents.append(data['content'])
    metadatas.append({'source': data['file_name'], 'importance': data['importance_list'][index]})
    ids.append(str(index + 1))

#so funktioniert das mit dem Persistieren nicht, wohl aber die ausführung
test_collection= client.create_collection("test_collection")

test_collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids
)

result = test_collection.query(
    query_texts=["What does Steve Jobs like about Berlin?"],
    n_results=1
)


# Für den Fall, dass bereits txtfiles im Ordner existieren, soll das für neue Anfrage genutzt werden
# eig. muss das nach ganz oben, um nicht den Code immer doppelt zu haben, sondern solange wir als Nutzer
# weitere Konversationen generiert haben wollen, werden neue generiert, ausgewertet und gespeichert
file_data = read_files_from_folder(directory)
if len(file_data) > 0:
    importance_list = []
    for index, file in enumerate(file_data):
        importance_list.append(metadatas[index]["importance"])

    # Liste aus der später das Thema der neuen Konversation gewählt wird
    # Da das die gesamten Konversationen sind, muss da mal geschaut werden wie das umsetzbar ist
    important_documents = []

    # Alle Dokumente mit der Wichtigkeit "important" in die Liste tun
    for index, importance_value in enumerate(importance_list):
        if importance_value == "important":
            important_documents.append(documents[index])

    # Sollte entgegen der Erwartung kein Dokument "important" sein, packt man alle "neutralen" rein
    if len(important_documents) == 0:
        for index, importance_value in enumerate(importance_list):
            if importance_value == "neutral":
                important_documents.append(documents[index])

    # Hier MUSS ein besserer Content übergeben werden um die Anweisung klein und spezifisch zu halten.
    # Außerdem muss mit ein paar Testläufen geschaut werden,
    # ob der Wert "importance" bzw. "evaluation" lieber nicht mitgegeben wird,
    # weil das bei der GPT ggf. zu Verwirrung führt

    # Dieser Fall ist äußerst ungünstig
    if len(important_documents) == 0:
        print("ja blöd nh, gibt keine wichtigen oder wenigstens neutrale Themen")
    # Das ist das Beste was passieren kann
    elif len(important_documents) == 1:
        content = important_documents[0]
    # Sonst muss eben per Zufallsprinzip eines der wichtigeren Themen herausgesucht werden
    else:
        random_index = random.choice(range(len(important_documents)))
        content = important_documents[random_index]
else:
    print()
    # Die Datei von oben übergeben, um die erste Konversation zu starten, andernfalls würde dann mit
    # den Daten der Chroma DB alles durchlaufen


vector_continue = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": content}
    ]
    ,
    functions=functions,
    function_call={'name': 'structure_conversation'},

)

content = vector_continue["choices"][0]["message"]["function_call"]["arguments"]
data = json.loads(content)
print(content)


print(result)

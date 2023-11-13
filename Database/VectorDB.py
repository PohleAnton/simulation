import json

import chromadb
from chromadb.config import Settings
import os
import yaml
import openai

# zum Mitdenken:

#so funktioniert das mit dem Persistieren nicht, wohl aber die ausführung
client = chromadb.Client(Settings(

    persist_directory="musk_jobs"
))

collection = client.create_collection(name="musk_jobs")

with open('./Conversations/musk_jobs.txt', 'r') as file:
    conversation = file.read()

config = yaml.safe_load(open("config.yml"))
openai.api_key = os.getenv('openai')

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

for theme in data["themes"]:
    theme_title = theme["theme"].replace(' ', '_').replace('\'', '').replace('\"', '').replace('?', '')
    filename = f"{base_title}_{theme_title}.txt"
    file_path = os.path.join(directory, filename)
    content = '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]}' for entry in theme["content"]])

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
    metadatas.append({'source': data['file_name']})
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

print(result)

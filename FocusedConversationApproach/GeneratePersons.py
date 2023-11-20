import json

import yaml
import openai
import chromadb
import datetime
import os


#print(os.getcwd())
#os.path.isdir('./FocusedConversationApproach')
#os.path.isfile('config.yml')

with open('./FocusedConversationApproach/txtFiles/scheme.txt', 'r') as file:
    scheme = file.read()

#print(scheme)

with open('../config.yml', 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)
openai.api_key = cfg.get('openai')

participants = ['Karl Marx', 'Peter Thiel', 'Elon Musk']
path = './FocusedConversationApproach/txtFiles/generatedProfiles/'

timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

file_name = f"{timestamp}_{','.join(participants)}.txt"

full_file_path = path + file_name
#print(full_file_path)
# Create and open the text file
with open(full_file_path, 'w') as file:
    # Write some content to the file (optional)
    file.write("")

for participant in participants:
    intro = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        messages=[
            {"role": "user", "content": scheme + 'for' + participant}
        ]
    )
    with open(full_file_path, 'a') as file:
        file.write('\n')
        file.write('\n')
        file.write(intro.choices[0].message.content)

with open(full_file_path, 'r') as file:
    content = file.read()
    print("File Content:")
#print(content)

prompt_p1 = (
    "Write a conversation with the following setup: "
    "1. Topics: Bring up naturally what might be in their interest. "
    "2. Informal, emotional conversation between two people who’ve known each other for a long time and don’t like each other "
    "very much. They both enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "3. Detailed, LONG conversation. "
    "4. Setting: New Year‘s Eve Party. Both might have had a few drinks already "
    "5. Involved Individuals: "
)

conversation = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": prompt_p1 + content}
    ]
)
print(conversation['choices'][0]['message']['content'])

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
                                            "description": "Summary of what they said about that topic."
                                        },
                                        "liking": {
                                            "type": "string",
                                            "description": "How much the participant liked that part of the conversation on this scale: Loves it. Likes it. Does not care about it. Does not like it. Hates it. Don't be to kind in your rating. Write like this:  {name} {scale}"
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

#ich nehme hier vorerst GPT-4, weil 3.5 kein vernünftiges JSON zurückgiobt...
vector_test = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": conversation["choices"][0]["message"]["content"]}
    ]
    ,
    functions=functions,
    function_call={'name': 'structure_conversation'},

)

content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
data = json.loads(content)
print(content)

print(conversation['choices'][0]['message']['content'])

##ToDo
#hier könnte man sowas einbauen wie:
if 'Simulation' or 'simulated' in content:
    print('')
    #do something with google api...vielleicht  irgendetwas, was roger penrose ins gespräch bringt?
    # dann extend conversation with roger penrose

# ergebnis ist eine map bzw. ein string, in dem die konversationen in subthemen gegliedert sind und bewertungen der teilnehmer enthalten
# beides mache ich für die vektordatenbank

# um die datei zu benennen...
base_title = data["title"].replace(' ', '_')

directory = './FocusedConversationApproach/txtFiles/ConversationChunks'
os.makedirs(directory, exist_ok=True)

# um die einzelnen dokumente für die chromadb zu erstellen:
for theme in data["themes"]:
    # sowohl titel
    theme_title = theme["theme"].replace(' ', '_').replace('\'', '').replace('\"', '').replace('?', '')
    # als auch der dateiname sind moment vielleicht "etwas" sperrig - aber das ist ja makulatur
    filename = f"{base_title}_{theme_title}.txt"
    file_path = os.path.join(directory, filename)
    # hier wird der inhalt erzeugt und die zusammenfassung des gesagten mit der einschätzung konkateniert. ist nicht so schnell erklärt, schaut euch am besten mal einen der strings an
    content = '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]} {entry["liking"]}' for entry in theme["content"]])

    with open(file_path, 'w') as file:
        # speichern als txt, damit die dokumente in die datenbank können
        file.write(content)


##ToDo
#hier könnte man sowas einbauen wie:
if 'Simulation' or 'simulated' in content:
        print('')
        #do something with google api...vielleicht  irgendetwas, was roger penrose ins gespräch bringt?


# print(data)

# liest die datein ein, um diese in die DB packen zu können
def read_files_from_folder(folder_path):
    files = []
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".txt"):
            with open(os.path.join(folder_path, file_name), 'r') as file:
                contents = file.read()
                files.append({"file_name": file_name, "content": contents})

    return files


file_data = read_files_from_folder(directory)

documents = []
metadata = []
ids = []

for index, data in enumerate(file_data):
    documents.append(data['content'])
    metadata.append({'source': data['file_name']})
    ids.append(str(index + 1))

gpt_split_db = chromadb.Client()
gpl_split_chunks = gpt_split_db.create_collection("gpt_split2")

# packt die eingelesenen daten in die DB
gpl_split_chunks.add(
    documents=documents,
    metadatas=metadata,
    ids=ids
)

test_gpl_split = gpl_split_chunks.query(
    query_texts=["Which part of the conversation Elon Musk likes the most?"],
    n_results=2
)
print(test_gpl_split['documents'][0])

test_gpl_split = gpl_split_chunks.query(
    query_texts=["Was there talk about simulated Reality or the simulation?"],
    n_results=2
)
print(test_gpl_split['documents'][0])

##ODER einfach die chromaDB splitten lassen:

chroma_split_db = chromadb.Client()
chroma_split_chunks = chroma_split_db.create_collection("chroma_split")

chroma_split_chunks.add(
    documents=[content],
    metadatas=[{"source": "{full_file_path}"}],
    ids=["doc1"]
)

test_chroma_split = chroma_split_chunks.query(
    query_texts=["What was said about the simulation argument?"]
)

test_chroma_split_2 = chroma_split_chunks.query(
    query_texts=["What was said about materialism?"]
)

print(test_chroma_split_2['documents'][0])

##toDo
# after creation of file: for each participant in participants: run prompt, file created txt files,
# from that, execute prompt in how to initialize. store in chromaDb. May run a few times with different participants.
# then pick conversation where simulation came up, maybe get names of people out. next conversation with that memory

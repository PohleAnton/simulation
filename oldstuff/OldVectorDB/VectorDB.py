import json

import chromadb
from chromadb.config import Settings
import os
import yaml
import openai
from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import DirectoryLoader
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma

# zum Mitdenken:

# Datenbank hier entfernt. Zum Mitdenken nach unten geschoben

# lädt die konversation. diese nehme ich jetzt, damit ich nicht so viele tokens benutze
with open('./Conversations/musk_jobs.txt', 'r') as file:
    conversation = file.read()

config = yaml.safe_load(open("config.yml"))
openai.api_key = config.get('openai')

# hier wird eine funktion beschrieben, welche die konversation aufteilt und auch auswertet, die die Teilnehmer den jeweiligen Teil der Konversation finden. Es gilt noch herauszufinden, wie man ein möglichst breites Spektrum an Einschätzung hat.
# sowohl diese Skala Loves it. Likes it. Does not care about it. Does not like it. Hates it als auch 1 - 5 führen bisher nur zu einer der beiden höchsten bewertungen.
# könnte aber auch an der quellkonversation liegen
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
                                            "description": "How much the participant liked that part of the conversation on this scale: Loves it. Likes it. Does not care about it. Does not like it. Hates it. Don't be to kind in your rating. Write like this:  {name} {scale} + this part of the conversation"
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

# nimmt die bereits vorhandene konversation und führt den function call darauf aus
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

# ergebnis ist eine map bzw. ein string, in dem die konversationen in subthemen gegliedert sind und bewertungen der teilnehmer enthalten
# beides mache ich für die vektordatenbank

# um die datei zu benennen...
base_title = data["title"].replace(' ', '_')

directory = './Conversations/txtfiles'
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

# so funktioniert das mit dem persistieren. ich weiß nur gar nicht, ob das so wünschenswert ist. so werden nämlich
# jedes mal die collections gespeichert und der code muss entsprechend modifiziert werden :(
db = chromadb.PersistentClient(path='./Conversations/db')

test_collection_3 = db.create_collection("test_collection_5")

# packt die eingelesenen daten in die DB
test_collection_3.add(
    documents=documents,
    metadatas=metadata,
    ids=ids
)

# nun können wir mit dieser query dokumente anhand des ratings holen. Zahlenskala hat leider nicht funktioniert...
result = test_collection_3.query(
    query_texts=["Which part of the conversation Elon Musk likes the most?"],
    n_results=2
)

print(result['documents'][0][0])

# man könnte einfach dieses dokument nehmen....
to_add = result['documents'][0][0]

with open('./Conversations/musk_jobs_again.txt', 'r') as file:
    conversation = file.read()

# das startet eine neue konversation mit der aus der DB entnommen info. das ist aber alles irgendwie ganz schön unscharf.
# vielleicht ist es ja tatsäch sinnvoll, einen like-score einzuführen, diesen in eine traditionelle datenbank zu packen
# und dem prompt irgendwie als harten fakt mitzugeben?
rerun = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": conversation + to_add}
    ]
)

# damit würde sie an der letzten konversation anknüpfen. das beruht jetzt ein bisschen auf der annahme, dass die bewertung
# der konversation tatsächlich differenziert genug ist und das die chromaDB ein richtiges ergebnis zurückliefert...
print(rerun.choices[0].message.content)

# ODER wir machen das:


directory = './Conversations/txtfiles'


#lädt die dokumente
def load_docs(directory):
    loader = DirectoryLoader(directory)
    documents = loader.load()
    return documents


documents = load_docs(directory)

#teilt sie für die Datenbank in chunks.
def split_docs(documents, chunk_size=1000, chunk_overlap=20):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = text_splitter.split_documents(documents)
    return docs


docs = split_docs(documents)

#ist für diese form nötig
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
new_db = Chroma.from_documents(
    documents=docs, embedding=embeddings
)

#hier wird es spannend: mit dem parameter k können wir angeben, wie viele dokumente wir mitnehmen wollen
matching_docs2 = new_db.similarity_search("Which part of the conversation Elon Musk likes the most?", k=2)

os.environ['OPENAI_API_KEY'] = config.get('openai')

model_name = "gpt-3.5-turbo"
llm = ChatOpenAI(model_name=model_name)
#der chain_type sagt in dem falle, dass einfach alle dokumente mitsollen.
# ich habe mich noch nicht näher informiert, mehr dazu hier:
# https://python.langchain.com/docs/modules/chains/document/
chain = load_qa_chain(llm, chain_type="stuff")

answer = chain.run(input_documents=matching_docs2, question=conversation)
print(answer)

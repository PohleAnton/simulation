import json

import yaml
import openai
import chromadb
import datetime
import os
import shutil

from langchain.chains import RetrievalQA
from langchain.chains.question_answering import load_qa_chain
from langchain.chat_models import ChatOpenAI
from langchain.document_loaders import DirectoryLoader, TextLoader
from langchain.embeddings import OpenAIEmbeddings, SentenceTransformerEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores.chroma import Chroma
from langchain.llms import OpenAI
from chromadb.utils import embedding_functions
from nltk import deprecated

with open('./FocusedConversationApproach/txtFiles/scheme.txt', 'r') as file:
    scheme = file.read()

# print(scheme)

with open('config.yml', 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)
openai.api_key = cfg.get('openai')

persist_directory = './FocusedConversationApproach/persistedDBs'
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

##ToDo
##wenn die persitierte Chroma geladen werden soll. Diese wird später im Code auch als "for_retrieval" angesprochen:
# for_retrieval = Chroma(persist_directory=persist_directory,
#                        embedding_function=embeddings)
##ToDo


participants = ['Karl Marx', 'Peter Thiel', 'Elon Musk']
path = './FocusedConversationApproach/txtFiles/generatedProfiles/'
target = './FocusedConversationApproach/txtFiles/generatedProfiles/used/'

timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

file_name = f"{timestamp}_{','.join(participants)}.txt"

full_file_path = path + file_name
# print(full_file_path)
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

if not os.path.exists(target):
    os.makedirs(target)

for filename in os.listdir(path):
    if filename.endswith('.txt'):
        shutil.move(os.path.join(path, filename), os.path.join(target, filename))

print(content)

prompt_p1 = (
    "Write a conversation with the following setup: "
    "1. Topics: At least two subjects in their interest. If the simulation hypothesis comes up, focus on that"
    "2. Informal, emotional conversation between people who’ve known each other for a long time and don’t like each other "
    "very much. They enjoy intense intellectual arguments and do not hold back.Deep Talk "
    "3. Long and detailed conversation. "
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
                                            "description": "How much the participant liked that part of the conversation on this scale: very much, a little, very little, not at all. Always write like this:  {name} likes it {rating}"
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

# gpt 4 gibt zuverlässiger ein gutes json zurück - aber ich versuche mal, mich drumrumzuhacken
vector_test = openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": 'structure_conversation' + conversation["choices"][0]["message"]["content"]}
    ]
    ,
    functions=functions,
    # ich versuche es mal ohne den expliziten call
    # function_call={'name': 'structure_conversation'},

)

content = vector_test["choices"][0]["message"]["function_call"]["arguments"]
data = json.loads(content)
print(content)

print(conversation['choices'][0]['message']['content'])

##ToDo
# hier könnte man sowas einbauen wie:
if 'Simulation' or 'simulated' in content:
    print('')
    # do something with google api...vielleicht  irgendetwas, was roger penrose ins gespräch bringt?
    # dann extend conversation with roger penrose

# ergebnis ist eine map bzw. ein string, in dem die konversationen in subthemen gegliedert sind und bewertungen der teilnehmer enthalten
# beides mache ich für die vektordatenbank

# um die datei zu benennen...
base_title = data["title"].replace(' ', '_')

directory = './FocusedConversationApproach/txtFiles/ConversationChunks'
target_dir = './FocusedConversationApproach/txtFiles/ConversationChunks/used/'
os.makedirs(directory, exist_ok=True)

for theme in data["themes"]:
    theme_title = theme["theme"].replace(' ', '_').replace('\'', '').replace('\"', '').replace('?', '')
    filename = f"{base_title}_{theme_title}.txt"
    file_path = os.path.join(directory, filename)

    # hier wird der inhalt erzeugt und die zusammenfassung des gesagten mit der einschätzung konkateniert. ist nicht so schnell erklärt, schaut euch am besten mal einen der strings an
    if 'linking' in theme['content'][0]:
        content = '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]} {entry["liking"]}' for entry in theme["content"]])
    else:
        content = '\n\n'.join([f'{entry["name"]}:\n{entry["summary"]}' for entry in theme["content"]])

    with open(file_path, 'w') as file:
        file.write(content)

##ToDo
# hier könnte man sowas einbauen wie:
if 'Simulation' or 'simulated' in content:
    print('')
    # do something with google api...vielleicht  irgendetwas, was roger penrose ins gespräch bringt?
##ToDo


loader = DirectoryLoader('./FocusedConversationApproach/txtFiles/ConversationChunks', glob="./*.txt",
                         loader_cls=TextLoader)
retriever_docs = loader.load()

##damit nicht in jede Vector-Collection geladen wird:
if not os.path.exists(target_dir):
    os.makedirs(target_dir)

for filename in os.listdir(directory):
    if filename.endswith('.txt'):
        shutil.move(os.path.join(directory, filename), os.path.join(target_dir, filename))

text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
texts = text_splitter.split_documents(retriever_docs)

with open('config.yml', 'r') as ymlfile:
    cfg = yaml.safe_load(ymlfile)
openai.api_key = cfg.get('openai')
os.environ['OPENAI_API_KEY'] = cfg.get('openai')
##ToDo
### anderes embedding, geht gerade nicht
embeddings_alt = OpenAIEmbeddings()
##ToDo

for_retrieval = Chroma.from_documents(documents=texts, embedding=embeddings)


##ToDo
# when persisting:
# for_retrieval = Chroma.from_documents(documents=texts, embedding=embeddings, persist_directory=persist_directory)
# for_retrieval.persist()
# when persisting:
##ToDo
test = for_retrieval.similarity_search("What was said about human consciousness?", k=2)

to_add = ''.join([index.page_content for index in test])
print(to_add)


sequel=  openai.ChatCompletion.create(
    model="gpt-3.5-turbo-1106",
    messages=[
        {"role": "user", "content": 'Write a dialogue between Peter Thiel, Elon Musk and Karl Marx. They have met before and talked about this:' + to_add}
    ]
)

print(sequel['choices'][0]['message']['content'])

# nur bedingt sinnvoll:
# ##mit search_kwargs lassen sich die wichtigsten 2 dokumente holen
# retriever = for_retrieval.as_retriever(search_kwargs={"k": 2})
#
# check = retriever.get_relevant_documents("simulation")
#
# llm = ChatOpenAI(
#     model_name="gpt-3.5-turbo-1106"
# )
#
# qa_chain = RetrievalQA.from_chain_type(llm=OpenAI(),
#                                        chain_type="stuff",
#                                        retriever=retriever,
#                                        return_source_documents=True)
#
# chain = load_qa_chain(llm, chain_type="stuff")
#
#
# ## Cite sources
# def process_llm_response(llm_response):
#     print(llm_response['result'])
#     print('\n\nSources:')
#     for source in llm_response["source_documents"]:
#         print(source.metadata['source'])
#
#
# # full example
# query = "What does Elon Musk think about the simulation?"
# llm_response = qa_chain(query)
# process_llm_response(llm_response)

# @deprecated
# liest die dateien ein, um diese in die DB packen zu können
# def read_files_from_folder(folder_path):
#     files = []
#     for file_name in os.listdir(folder_path):
#         if file_name.endswith(".txt"):
#             with open(os.path.join(folder_path, file_name), 'r') as file:
#                 contents = file.read()
#                 files.append({"file_name": file_name, "content": contents})
#
#     return files
#
#
# file_data = read_files_from_folder(directory)
#
# documents = []
# metadata = []
# ids = []
#

# for index, data in enumerate(file_data):
#         documents.append(data['content'])
#         metadata.append({'source': data['file_name']})
#         ids.append(str(index + 1))
#
# # falls datenbank exisiert: bereits embedded dokumente zählen und auf index rechnen
# if 'gpt_split_db' in globals():
#     for index, data in enumerate(file_data):
#         documents.append(data['content'])
#         metadata.append({'source': data['file_name']})
#         ids.append(str(index + 1 + gpt_split_db.list_collections()[1].count()))
#
# print(gpt_split_db.list_collections())
# print(gpt_split_db.list_collections()[1].count())
#
#
#
# gpt_split_db = chromadb.Client()
# new = chromadb.Client()
# gpt_split_chunks = gpt_split_db.create_collection("gpt_split")
# chroma_split = new.create_collection("chroma_split")
# # packt die eingelesenen daten in die DB
# gpt_split_chunks.add(
#     documents=documents,
#     metadatas=metadata,
#     ids=ids
# )
#
#
#
# chroma_split.add(
#     documents=conversation['choices'][0]['message']['content'],
#     metadatas=[{"source": "{full_file_path}"}],
#     ids=["doc1"]
# )
#
# c = chroma_split.query(
#     query_texts=["simulation"],
#     n_results=2
# )
#
# test_gpl_split = gpt_split_chunks.query(
#     query_texts=["inequality"],
#     n_results=2
# )
# print(test_gpl_split['documents'][0][0])
##deprecated
####
## ich habe jetzt nochmal eine ganze menge mit Liking score gearbeitet - das leistet die chroma irgendwie nicht, weder als
## Zahl noch in Worten. Vielleicht ist das ja auch gar nicht so wichtig, vielleicht kann man ja im Prompt ein bisschen
## was explizites mitgeben. Gerade habe ich "Bring up Metaphysics"

##toDo
# after creation of file: for each participant in participants: run prompt, file created txt files,
# from that, execute prompt in how to initialize. store in chromaDb. May run a few times with different participants.
# then pick conversation where simulation came up, maybe get names of people out. next conversation with that memory
##ToDo

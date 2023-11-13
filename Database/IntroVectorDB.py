import chromadb
from chromadb.config import Settings
import os

#so funktioniert das mit dem Persistieren nicht, wohl aber die ausführung
client = chromadb.Client(Settings(

    persist_directory="test_db"
))
#sollte die DB im entsprechenden Ordner persitieren, das versuche ich jetzt nich mehr
client2 = chromadb.PersistentClient(path='./Conversations/db')

collection = client.create_collection(name="sample_collection")

collection.add(
    documents=["This is a document about cat", "This is a document about car", "this is about Ford",
               "this is about GM"],
    metadatas=[{"category": "animal"}, {"category": "vehicle"}, {"category": "vehicle"}, {"category": "vehicle"}],
    ids=["id1", "id2", "id3", "id4"]
)

results1 = collection.query(
    query_texts=["vehicle"],
    n_results=3
)

results1


def read_files_from_folder(folder_path):
    file_data = []

    for file_name in os.listdir(folder_path):
        if file_name.endswith(".txt"):
            with open(os.path.join(folder_path, file_name), 'r') as file:
                content = file.read()
                file_data.append({"file_name": file_name, "content": content})

    return file_data


folder_path = './pets'
file_data = read_files_from_folder(folder_path)

documents = []
metadatas = []
ids = []

for index, data in enumerate(file_data):
    documents.append(data['content'])
    metadatas.append({'source': data['file_name']})
    ids.append(str(index + 1))

pet_collection = client.create_collection("pet_collection")

pet_collection.add(
    documents=documents,
    metadatas=metadatas,
    ids=ids
)

results = pet_collection.query(
    query_texts=["What are the different kinds of pets people commonly own?"],
    n_results=1
)
print(results)


results2 = pet_collection.query(
    query_texts=["What are the emotional benefits of owning a pet?"],
    n_results=1,
    where={"source": "Training and Behaviour of Pets.txt"}
)
print(results2)

results3 =pet_collection.query(
    query_texts=["What are the emotional benefits of owning a pet?"],
    n_results=1,
    where_document={"$contains":"reptiles"}
)
print(results3)

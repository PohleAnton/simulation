"""
weitere Versuche mit Vektordatenbanken, hier auch mit dem Langchain Framework. Der praktische Nutzen schien sich allerdings
nicht zu erschließen, wenn man ausschließlich mit einer ChromaDB arbeitet

"""

import os
import openai
import langchain
from langchain.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import SentenceTransformerEmbeddings
from langchain.vectorstores import Chroma
from langchain.chat_models import ChatOpenAI
import yaml
from langchain.chains.question_answering import load_qa_chain
from langchain.chains import RetrievalQA

directory = './pets'


def load_docs(directory):
    loader = DirectoryLoader(directory)
    documents = loader.load()
    return documents


documents = load_docs(directory)
print(len(documents))


def split_docs(documents, chunk_size=1000, chunk_overlap=20):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    docs = text_splitter.split_documents(documents)
    return docs


docs = split_docs(documents)
print(len(docs))

# optional, chromaDB hat einen default
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
db = Chroma.from_documents(docs, embeddings)

query = "What are the different kinds of pets people commonly own?"
matching_docs = db.similarity_search(query)

matching_docs[0]

matching_docs = db.similarity_search_with_score(query, k=2)

print(matching_docs[0])


query2 = "Do people like animals?"
t = db.similarity_search(query2)

persist_directory = "langchain_db"
vectordb = Chroma.from_documents(
    documents=docs, embedding=embeddings, persist_directory=persist_directory
)
# persistiert DB
vectordb.persist()

# lädt db
new_db = Chroma( embedding_function=embeddings)
matching_docs = new_db.similarity_search_with_score(query, k=2)

config = yaml.safe_load(open("./config.yml"))
os.environ['OPENAI_API_KEY'] = config.get('openai')

model_name = "gpt-3.5-turbo"
llm = ChatOpenAI(model_name=model_name)

chain = load_qa_chain(llm, chain_type="stuff")

query = "What are the different kinds of pets people commonly own?"

matching_docs = new_db.similarity_search(query)
answer = chain.run(input_documents=matching_docs, question=query)
print(answer)

retrieval_chain = RetrievalQA.from_chain_type(llm, chain_type="stuff", retriever=new_db.as_retriever())
print(retrieval_chain.run(query))
print(retrieval_chain.llm)
query = "What are the different kinds of pets people commonly own?"

matching_docs = new_db.similarity_search(query)
matching_docs[0]
len(retrieval_chain)

matching_docs[0]

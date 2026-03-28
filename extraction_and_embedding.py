from langchain_groq import ChatGroq
from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import Qdrant
from qdrant_client import QdrantClient
import os
from qdrant_client.models import VectorParams, Distance

folder = r"C:\Users\YOG\OneDrive\Desktop\FastAPI Financial Document Management With Semantic Analysis\uploads"

all_text=""

for file_name in os.listdir(folder):
    if file_name.endswith(".pdf"):
        file_path = os.path.join(folder, file_name)

        loader = PDFPlumberLoader(file_path)
        documents = loader.load()

        for doc in documents:
            text = doc.page_content

            if text:
                all_text += text

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=250,
    chunk_overlap =100
)

texts = text_splitter.split_text(all_text)

embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-l6-v2")
client = QdrantClient(path=r"C:\Users\YOG\OneDrive\Desktop\FastAPI Financial Document Management With Semantic Analysis\api\qdrant_storage")

if not client.collection_exists("mycollection"):
    client.create_collection(
        collection_name="mycollection",
        vectors_config=VectorParams(
            size=384,
            distance=Distance.COSINE
        )
    )

db = Qdrant(
    client=client,
    collection_name="mycollection",
    embeddings=embeddings
)

db.add_texts(texts)

print("Extraction and Embedding Successfully Completed!")









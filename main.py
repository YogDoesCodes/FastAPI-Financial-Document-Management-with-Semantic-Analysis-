from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from schema import User
from user_roles import roles
from users_db import user_details, engine
from sqlalchemy.orm import sessionmaker
import os
from document_metdata_db import document_metadata
from datetime import datetime, timezone
from schema import Login
from langchain_qdrant import Qdrant
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from jwt_handler import create_token
from jwt_handler import verify_token

load_dotenv()

UPLOAD_DIR = r"C:\Users\YOG\OneDrive\Desktop\FastAPI Financial Document Management With Semantic Analysis\uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

Session = sessionmaker(bind=engine)
session = Session()

app = FastAPI()

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-l6-v2"
)

client = QdrantClient(path=r"C:\Users\YOG\OneDrive\Desktop\FastAPI Financial Document Management With Semantic Analysis\api\qdrant_storage")

vector_db = Qdrant(
    client=client,
    collection_name="mycollection",
    embeddings=embeddings
)

def get_current_user(token: str):
    user = verify_token(token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Token")
    return user

@app.post("/auth/register-user")
def register_new_user(user: User):
    if user.role not in roles:
        raise HTTPException(status_code=400, detail="Invalid Role")
    expected_role_id = roles[user.role]
    if user.role_id != expected_role_id:
        raise HTTPException(status_code=400, detail="Invalid Role ID")
    user_info = user_details(
        name=user.name,
        email=user.email,
        password=user.password,
        role=user.role,
        role_id=user.role_id
    )
    session.add(user_info)
    session.commit()
    return {"message": "User details added successfully to the database"}

@app.post("/auth/login")
def user_login(user: Login):
    db_user = session.query(user_details).filter_by(
        name=user.name,
        password=user.password,
        role_id=user.role_id
    ).one_or_none()

    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_token({
        "user_id": db_user.id,
        "name": db_user.name,
        "role": db_user.role
    })

    return {"access_token": token}

@app.post("/documents/upload")
async def document_upload(
    file: UploadFile = File(...),
    company_name: str = Form(...),
    document_type: str = Form(...),
    token: str = Form(...)
):
    user = get_current_user(token)

    if user["role"] not in ["Client", "Admin"]:
        raise HTTPException(status_code=401, detail="Access denied")

    file_path = os.path.join(UPLOAD_DIR, file.filename)

    with open(file_path, 'wb') as f:
        content = await file.read()
        f.write(content)

    new_doc = document_metadata(
        title=file.filename,
        company_name=company_name,
        document_type=document_type,
        uploaded_by=user["name"],
        created_at=datetime.now(timezone.utc)
    )

    session.add(new_doc)
    session.commit()

    return {"message": "Uploaded Successfully!", "id": new_doc.id}

@app.get("/documents")
def get_all_documents():
    docs = session.query(document_metadata).all()
    return [
        {
            "id": doc.id,
            "title": doc.title,
            "company_name": doc.company_name,
            "document_type": doc.document_type,
            "uploaded_by": doc.uploaded_by,
            "created_at": doc.created_at
        }
        for doc in docs
    ]

@app.get("/documents/search")
def search_document_by_metadata(
    token: str,
    id: str = None,
    title: str = None,
    company_name: str = None,
    document_type: str = None
):
    user = get_current_user(token)

    if user["role"] not in ["Client", "Admin"]:
        raise HTTPException(status_code=401, detail="Access denied")

    query = session.query(document_metadata)

    if id:
        query = query.filter_by(id=id)
    if title:
        query = query.filter_by(title=title)
    if company_name:
        query = query.filter_by(company_name=company_name)
    if document_type:
        query = query.filter_by(document_type=document_type)

    results = query.all()

    return [
        {
            "id": doc.id,
            "title": doc.title,
            "company_name": doc.company_name,
            "document_type": doc.document_type,
            "uploaded_by": doc.uploaded_by,
            "created_at": doc.created_at
        }
        for doc in results
    ]

@app.get("/documents/{document_id}")
def get_documents_by_id(document_id: int):
    doc = session.query(document_metadata).filter_by(id=document_id).one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return [{
        "id": doc.id,
        "title": doc.title,
        "company_name": doc.company_name,
        "document_type": doc.document_type,
        "uploaded_by": doc.uploaded_by,
        "created_at": doc.created_at
    }]

@app.delete("/documents/{document_id}")
def delete_documents_by_id(document_id: int):
    doc = session.query(document_metadata).filter_by(id=document_id).one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(UPLOAD_DIR, doc.title)
    if os.path.exists(file_path):
        os.remove(file_path)

    session.delete(doc)
    session.commit()

    return {"message": f"Document {doc.title} deleted successfully"}

def reranking_chunks(query, docs, llm):
    scored_docs = []

    for doc in docs:
        prompt = f"""
        Question: {query}

        Context: {doc.page_content}

        Is this context relevant to answer the question?
        Give score from 0 to 10. Only return number.
        """

        response = llm.invoke(prompt)
        try:
            score = float(response.content.strip())
        except:
            score = 0

        scored_docs.append((score, doc))

    scored_docs.sort(key=lambda x: x[0], reverse=True)
    top_docs = [doc for score, doc in scored_docs[:5]]

    return top_docs

@app.post("/roles/create")
def create_role(role: str, role_id: str):
    roles[role] = role_id
    return {"message": "Role created"}

@app.post("/users/assign-role")
def assign_role(user_id: int, role: str):
    user = session.query(user_details).filter_by(id=user_id).one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if role not in roles:
        raise HTTPException(status_code=400, detail="Invalid role")

    user.role = role
    user.role_id = roles[role]

    session.commit()

    return {"message": "Role assigned"}

@app.get("/users/{id}/roles")
def get_roles(id: int):
    user = session.query(user_details).filter_by(id=id).one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"role": user.role}

@app.get("/users/{id}/permissions")
def get_permissions(id: int):
    user = session.query(user_details).filter_by(id=id).one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    role_permissions = {
        "Admin": "Full access",
        "Financial Analyst": "Upload and edit documents",
        "Auditor": "Review documents",
        "Client": "View company documents"
    }

    return {
        "role": user.role,
        "permissions": role_permissions.get(user.role, "No permissions")
    }

@app.post("/rag/search")
def rag_search(query: str, token: str):
    user = get_current_user(token)

    if user["role"] not in ["Client", "Admin"]:
        raise HTTPException(status_code=401, detail="Access denied")

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0
    )

    results = vector_db.similarity_search(query, k=20)

    results = reranking_chunks(query, results, llm)

    context = "\n".join([doc.page_content for doc in results])

    prompt = f"""
    Answer the question based only on the context below.

    Context:
    {context}

    Question:
    {query}
    """

    response = llm.invoke(prompt)

    return {
        "query": query,
        "answer": response.content,
        "retrieved_chunks": [doc.page_content for doc in results]
    }

@app.get("/rag/context/{document_id}")
def get_rag_context(document_id: int, token: str):
    user = get_current_user(token)

    doc = session.query(document_metadata).filter_by(id=document_id).one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "title": doc.title,
        "company_name": doc.company_name,
        "document_type": doc.document_type,
        "uploaded_by": doc.uploaded_by,
        "created_at": doc.created_at
    }
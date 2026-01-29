# app/api.py
from fastapi import FastAPI
from pydantic import BaseModel
from app.rag import ask_llm

app = FastAPI(title="HMUN RAG Consultant")

class Query(BaseModel):
    question: str
    top_k: int = 5

@app.post("/chat")
async def chat(q: Query):
    result = ask_llm(q.question, q.top_k)
    return result

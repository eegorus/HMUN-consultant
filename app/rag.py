# app/rag.py
import os
import json
import requests
from typing import List, Dict
from pathlib import Path
import chromadb
from textwrap import shorten
from dotenv import load_dotenv

load_dotenv()

CHROMA_DIR = "db"
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemma-3-4b-it:free")

def get_collection():
    """Получить ChromaDB коллекцию (новый API)"""
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    return client.get_collection("obsidian_hmun")

def retrieve_context(query: str, top_k: int = 5) -> List[Dict]:
    """Поиск релевантных документов по запросу"""
    try:
        coll = get_collection()
        res = coll.query(
            query_texts=[query],
            n_results=top_k,
        )
        
        if not res["documents"] or not res["documents"][0]:
            return []
        
        docs = res["documents"][0]
        metas = res["metadatas"][0]
        distances = res["distances"][0] if res.get("distances") else [0] * len(docs)
        
        return [
            {
                "text": d,
                "meta": m,
                "distance": dist,
                "source_id": f"[{i+1}]"  # Нужно для ссылок в тексте
            }
            for i, (d, m, dist) in enumerate(zip(docs, metas, distances))
        ]
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        return []

def build_prompt(question: str, contexts: list) -> str:
    """Собрать промпт с контекстом и инструкциями по цитированию"""
    
    # Форматировать контекст с числовыми ссылками
    parts = []
    for i, c in enumerate(contexts, 1):
        src = c["meta"].get("source", "unknown")
        parts.append(f"[{i}] ({src}):\n{c['text']}\n")
    
    context_block = "\n\n".join(parts) if parts else "Контекст не найден"
    
    return (
        "Ты — эксперт по химическим методам увеличения нефтеотдачи (ХМУН). "
        "Отвечай строго по приведённым источникам.\n\n"
        "ВАЖНО: Когда ты используешь информацию из источника, "
        "ОБЯЗАТЕЛЬНО указывай номер источника в формате [N] сразу после предложения или фразы. "
        "Например: 'Температура воды составляет 40–80°C [1]' или 'По данным исследования [2], эффективность...'.\n\n"
        "Если информация в источниках отсутствует, скажи это честно.\n\n"
        "ИСТОЧНИКИ:\n"
        f"{context_block}\n\n"
        f"ВОПРОС: {question}\n\n"
        "Ответь, не забывая про ссылки [1], [2] и т.д. на источники."
    )

def ask_llm(question: str, top_k: int = 100) -> dict:
    """Получить ответ от LLM через OpenRouter"""
    
    # Поиск контекста
    contexts = retrieve_context(question, top_k=top_k)
    
    if not contexts:
        return {
            "answer": "⚠️ В базе знаний не найдено релевантной информации по вашему вопросу.",
            "sources": [],
            "error": "no_context"
        }
    
    # Подготовка промпта
    prompt = build_prompt(question, contexts)
    
    # Вызов OpenRouter
    try:
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": OPENROUTER_MODEL,
            "messages": [
                {"role": "user", "content": prompt}
            ],
        }
        
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
    
    except requests.exceptions.Timeout:
        answer = "⏱️ Превышено время ожидания ответа от LLM. Попробуйте позже."
    except requests.exceptions.HTTPError as e:
        answer = f"❌ Ошибка API: {e.response.status_code} - {e.response.text[:200]}"
    except Exception as e:
        answer = f"❌ Ошибка при вызове LLM: {str(e)[:200]}"
    
    # Подготовка источников с индексами
    sources = [
        {
            "index": i + 1,
            "preview": shorten(c["text"], 200),
            "meta": c["meta"],
            "source_file": c["meta"].get("source", "unknown")
        }
        for i, c in enumerate(contexts)
    ]
    
    return {"answer": answer, "sources": sources}

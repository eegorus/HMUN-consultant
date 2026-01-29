# app/ingest.py
import os
from pathlib import Path
from langchain_community.document_loaders import ObsidianLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
import chromadb
from chromadb.utils import embedding_functions

VAULT_PATH = "vault"
CHROMA_DIR = "db"

def load_documents():
    """Загрузить все .md файлы из Obsidian vault"""
    loader = ObsidianLoader(path=VAULT_PATH, collect_metadata=True)
    docs = loader.load()
    print(f"✅ Загружено {len(docs)} документов")
    return docs

def split_documents(docs):
    """Разбить документы на chunks"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n## ", "\n### ", "\n", " "],
    )
    chunks = splitter.split_documents(docs)
    print(f"✅ Создано {len(chunks)} chunks")
    return chunks

def build_chroma_index(chunks):
    """Индексировать chunks в ChromaDB (новый API)"""
    
    # Создать директорию если её нет
    Path(CHROMA_DIR).mkdir(exist_ok=True)
    
    # Инициализировать ChromaDB с новым API
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    
    # Удалить старую коллекцию если существует
    try:
        client.delete_collection(name="obsidian_hmun")
    except:
        pass
    
    # Создать новую коллекцию
    collection = client.get_or_create_collection(
        name="obsidian_hmun",
        metadata={"hnsw:space": "cosine"}
    )
    
    # Подготовить данные
    texts = [c.page_content for c in chunks]
    metadatas = [c.metadata for c in chunks]
    ids = [f"doc_{i}" for i in range(len(chunks))]
    
    # Добавить в коллекцию
    collection.add(
        documents=texts,
        metadatas=metadatas,
        ids=ids,
    )
    
    print(f"✅ Индекс сохранён в {CHROMA_DIR}/")

if __name__ == "__main__":
    print("🔄 Индексирование Obsidian Vault...")
    docs = load_documents()
    chunks = split_documents(docs)
    build_chroma_index(chunks)
    print("✅ Готово!")

# ui.py
import requests
import streamlit as st
from datetime import datetime
import json

API_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="ХМУН Консультант", layout="wide")
st.title("🔧 Консультант по методам увеличения нефтеотдачи")

# ============================================================================
# SIDEBAR: История чатов и управление
# ============================================================================
with st.sidebar:
    st.markdown("### 💬 Мои чаты")
    
    # Инициализировать список чатов если его нет
    if "chats" not in st.session_state:
        st.session_state.chats = []
    
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None
    
    # Кнопка создать новый чат
    if st.button("➕ Новый чат", use_container_width=True, type="primary"):
        new_chat_id = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.chats.append({
            "id": new_chat_id,
            "title": "Новый чат",
            "messages": [],
            "created": datetime.now().isoformat()
        })
        st.session_state.current_chat_id = new_chat_id
        st.rerun()
    
    st.markdown("---")
    
    # Список сохраненных чатов
    if st.session_state.chats:
        st.markdown("### 📚 История чатов")
        
        for chat in reversed(st.session_state.chats):  # Новые сверху
            # Вычислить краткое название из первого вопроса
            title = chat["title"]
            if chat["messages"]:
                first_q = chat["messages"][0].get("content", "")[:50]
                if first_q:
                    title = first_q + "..."
            
            # Кнопка для выбора чата
            col1, col2 = st.columns([4, 1])
            
            with col1:
                if st.button(
                    f"💭 {title}",
                    use_container_width=True,
                    key=f"chat_{chat['id']}"
                ):
                    st.session_state.current_chat_id = chat["id"]
                    st.rerun()
            
            with col2:
                if st.button(
                    "🗑️",
                    key=f"delete_{chat['id']}",
                    help="Удалить чат"
                ):
                    st.session_state.chats = [c for c in st.session_state.chats if c["id"] != chat["id"]]
                    if st.session_state.current_chat_id == chat["id"]:
                        st.session_state.current_chat_id = None
                    st.rerun()
    else:
        st.info("📭 История чатов пуста. Создайте новый чат!")
    
    st.markdown("---")
    st.markdown("### 📖 О системе")
    st.markdown("""
    Это RAG-система на базе Obsidian Vault с документами по ХМУН.
    
    Система автоматически ищет все релевантные документы и формирует ответы на их основе, с прямыми ссылками на источники в тексте.
    """)

# ============================================================================
# ГЛАВНАЯ ОБЛАСТЬ: Чат
# ============================================================================

# Если нет активного чата, предложить создать
if st.session_state.current_chat_id is None:
    st.info("👈 Выберите чат слева или создайте новый!")
else:
    # Найти текущий чат
    current_chat = None
    for chat in st.session_state.chats:
        if chat["id"] == st.session_state.current_chat_id:
            current_chat = chat
            break
    
    if current_chat is None:
        st.warning("Чат не найден")
    else:
        # Заголовок с инфо о чате
        st.markdown(f"### Чат от {current_chat['id']}")
        
        # Контейнер для истории (scrollable)
        chat_container = st.container()
        
        # Вывести историю сообщений сверху вниз
        with chat_container:
            if not current_chat["messages"]:
                st.info("💭 Начните разговор — задайте свой первый вопрос!")
            
            for message in current_chat["messages"]:
                if message["role"] == "user":
                    st.markdown(f"### 👤 Вопрос")
                    st.markdown(f"> {message['content']}")
                else:  # assistant
                    st.markdown(f"### 🤖 Ответ")
                    st.markdown(message['content'])
                    
                    # Показать источники если они есть
                    if message.get('sources'):
                        # Извлечь номера источников из ответа
                        sources_referenced = []
                        answer_text = message['content']
                        
                        # Проверить какие источники упомянуты в ответе
                        for src in message['sources']:
                            source_ref = f"[{src['index']}]"
                            if source_ref in answer_text:
                                sources_referenced.append(src)
                        
                        # Если ничего не найдено в тексте, показать все
                        if not sources_referenced:
                            sources_referenced = message['sources']
                        
                        with st.expander(f"📚 Использованные источники ({len(sources_referenced)})"):
                            for src in sources_referenced:
                                st.markdown(f"**[{src['index']}] {src['source_file']}**")
                                st.caption(src['preview'])
                    
                    st.markdown("---")
        
        # Input для нового вопроса (внизу)
        st.markdown("### 💬 Введите ваш вопрос")
        question = st.chat_input(
            "Например: 'Какая температура воды при горячем заводнении?'",
            key=f"input_{st.session_state.current_chat_id}"
        )
        
        if question:
            # Добавить вопрос в текущий чат
            current_chat["messages"].append({
                "role": "user",
                "content": question
            })
            
            # Показать спиннер во время загрузки
            with st.spinner("⏳ Ищу информацию в базе знаний..."):
                try:
                    # Использовать все доступные источники (высокое значение top_k)
                    resp = requests.post(
                        API_URL,
                        json={"question": question, "top_k": 100},  # Все источники
                        timeout=60,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    
                    # Добавить ответ в текущий чат
                    current_chat["messages"].append({
                        "role": "assistant",
                        "content": data['answer'],
                        "sources": data.get('sources', [])
                    })
                    
                    # Обновить чат в списке
                    for i, chat in enumerate(st.session_state.chats):
                        if chat["id"] == st.session_state.current_chat_id:
                            st.session_state.chats[i] = current_chat
                            break
                    
                    # Перезагрузить страницу для отображения нового сообщения
                    st.rerun()
                
                except requests.exceptions.ConnectionError:
                    st.error("❌ Не удаётся подключиться к API. Убедитесь, что сервер запущен на http://localhost:8000")
                except requests.exceptions.Timeout:
                    st.error("⏱️ Превышено время ожидания ответа. Попробуйте позже.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"❌ Ошибка сервера: {e.response.status_code}")
                except Exception as e:
                    st.error(f"❌ Ошибка: {str(e)}")

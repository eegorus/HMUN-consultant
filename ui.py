import requests
import streamlit as st

API_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="ХМУН-консультант", layout="wide")
st.title("ХМУН-консультант по Obsidian-базе")

top_k = st.sidebar.slider("Количество источников", 1, 10, 5)

if "history" not in st.session_state:
    st.session_state.history = []

question = st.chat_input("Введите вопрос...")

if question:
    resp = requests.post(API_URL, json={"question": question, "top_k": top_k}).json()
    st.session_state.history.append({"q": question, "a": resp})

for item in st.session_state.history[::-1]:
    st.markdown(f"**Вопрос:** {item['q']}")
    st.markdown(f"**Ответ:** {item['a']['answer']}")
    with st.expander("Источники"):
        for s in item["a"]["sources"]:
            st.write(s["meta"].get("source", "unknown"))
            st.caption(s["preview"])
    st.markdown("---")

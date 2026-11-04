"""Interface web opcional (Streamlit) para o mesmo agente usado no CLI.

Reaproveita src/agent.py inteiramente - zero lógica duplicada. Rodar com:
    streamlit run streamlit_app.py
"""

from __future__ import annotations

import uuid

import streamlit as st

from src.agent import Agente
from src.history import carregar_sessao

st.set_page_config(page_title="Empório da Música - Atendimento", page_icon="🎸")

if "sessao_id" not in st.session_state:
    st.session_state.sessao_id = str(uuid.uuid4())

if "agente" not in st.session_state:
    st.session_state.agente = Agente(st.session_state.sessao_id)

st.title("🎸 Empório da Música")
st.caption(f"Sessão: `{st.session_state.sessao_id}`")

with st.sidebar:
    st.subheader("Continuar sessão")
    sessao_informada = st.text_input("ID de uma sessão salva")
    if st.button("Carregar") and sessao_informada:
        st.session_state.sessao_id = sessao_informada
        st.session_state.agente = Agente(sessao_informada)
        st.rerun()

historico = carregar_sessao(st.session_state.sessao_id)
for msg in historico:
    conteudo = msg["content"]
    if isinstance(conteudo, str):
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(conteudo)
    elif isinstance(conteudo, list):
        texto = next((b.get("text") for b in conteudo if isinstance(b, dict) and b.get("type") == "text"), None)
        if texto:
            with st.chat_message("assistant"):
                st.markdown(texto)

pergunta = st.chat_input("Digite sua mensagem...")
if pergunta:
    with st.chat_message("user"):
        st.markdown(pergunta)
    with st.chat_message("assistant"):
        with st.spinner("Rico está digitando..."):
            resposta = st.session_state.agente.responder(pergunta)
        st.markdown(resposta)

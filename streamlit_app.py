import os

import requests
import streamlit as st

WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://localhost:8001")
RESEARCHER_AGENT_URL = os.getenv("RESEARCHER_AGENT_URL", "http://localhost:8002")

st.set_page_config(page_title="A2A Multi-Agent Demo", layout="wide")
st.title("Researcher → Writer Agent Demo")

with st.sidebar:
    st.header("Configuration")
    topic = st.text_input("Research topic", "open source agent frameworks")
    task_name = st.selectbox("Writer capability", ["format-report", "summarize", "cite-sources", "adjust-tone"])
    tone = st.selectbox("Tone", ["professional", "technical", "executive"], disabled=task_name != "adjust-tone")
    run_button = st.button("Run workflow")

if run_button:
    with st.spinner("Running the agent workflow..."):
        writer_card = requests.get(f"{WRITER_AGENT_URL.rstrip('/')}/.well-known/agent-card.json", timeout=10).json()
        researcher_response = requests.get(
            f"{RESEARCHER_AGENT_URL.rstrip('/')}/research/{topic}",
            params={"task_name": task_name, "tone": tone},
            timeout=20,
        ).json()

    st.subheader("Discovered Writer Agent Card")
    st.json(writer_card)

    st.subheader("Workflow Result")
    st.json(researcher_response)

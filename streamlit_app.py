import os

import requests
import streamlit as st

WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://localhost:8001")
RESEARCHER_AGENT_URL = os.getenv("RESEARCHER_AGENT_URL", "http://localhost:8002")


def _extract_result_items(research_summary: str):
    items = []
    for line in research_summary.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


st.set_page_config(page_title="A2A Multi-Agent Demo", layout="wide")
st.title("Researcher → Writer Agent Demo")

with st.sidebar:
    st.header("Configuration")
    topic = st.text_input("Research topic", "open source agent frameworks")
    task_name = st.selectbox("Writer capability", ["format-report", "summarize", "cite-sources", "adjust-tone"])
    tone = st.selectbox("Tone", ["professional", "technical", "executive"], disabled=task_name != "adjust-tone")
    run_button = st.button("Run workflow", use_container_width=True)

if run_button:
    with st.spinner("Running the agent workflow..."):
        writer_card = requests.get(f"{WRITER_AGENT_URL.rstrip('/')}/.well-known/agent-card.json", timeout=10).json()
        researcher_response = requests.get(
            f"{RESEARCHER_AGENT_URL.rstrip('/')}/research/{topic}",
            params={"task_name": task_name, "tone": tone},
            timeout=20,
        ).json()

    topic_value = researcher_response.get("topic", topic)
    research_summary = researcher_response.get("research_summary", "") or ""
    writer_response = researcher_response.get("writer_response", {}) or {}
    result_text = writer_response.get("result", "") if isinstance(writer_response, dict) else ""
    result_items = _extract_result_items(research_summary)

    st.subheader("Workflow overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Search term", topic_value)
    col2.metric("Requested capability", task_name)
    col3.metric("Tone", tone)

    st.markdown("---")

    left_col, right_col = st.columns([1.2, 1.0])
    with left_col:
        st.markdown("### 1. Search term")
        st.info(topic_value)

        st.markdown("### 2. Research results shown in the UI")
        if result_items:
            for item in result_items:
                st.markdown(f"- {item}")
        else:
            st.caption("No structured search results were returned.")

    with right_col:
        st.markdown("### 3. Payload sent to the writer")
        st.code(research_summary, language="text")

    st.markdown("---")
    st.markdown("### 4. Writer response")
    if isinstance(writer_response, dict):
        st.success(writer_response.get("status", "success"))
        st.markdown(result_text)
    else:
        st.code(str(writer_response))

    with st.expander("Discovered writer agent card"):
        st.json(writer_card, expanded=False)

    with st.expander("Raw workflow payload"):
        st.json(researcher_response, expanded=False)

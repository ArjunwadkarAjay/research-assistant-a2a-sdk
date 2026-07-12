import os

import requests
import streamlit as st

from apps.ui_helpers import parse_research_items

WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://localhost:8001")
RESEARCHER_AGENT_URL = os.getenv("RESEARCHER_AGENT_URL", "http://localhost:8002")


def _render_agent_card(card):
    st.caption("Discovered agent card")
    st.markdown(f"**Name:** {card.get('name', 'Unknown')}")
    st.markdown(f"**Description:** {card.get('description', 'No description available')}")

    capabilities = card.get("capabilities", [])
    if capabilities:
        st.markdown("**Capabilities:**")
        for capability in capabilities:
            st.markdown(f"- {capability}")

    endpoints = card.get("endpoints", {}) or {}
    if endpoints:
        st.markdown("**Endpoints:**")
        for name, endpoint in endpoints.items():
            st.markdown(f"- {name}: {endpoint}")


st.set_page_config(page_title="A2A Multi-Agent Demo", layout="wide")
st.title("Researcher → Writer Agent Demo")

if "show_full_research" not in st.session_state:
    st.session_state.show_full_research = False

with st.sidebar:
    st.header("Configuration")
    topic = st.text_input("Research topic", "open source agent frameworks")
    task_name = st.selectbox("Writer capability", ["format-report", "summarize", "cite-sources", "adjust-tone"])
    tone = st.selectbox("Tone", ["professional", "technical", "executive"])
    result_count = st.slider(
        "Search results to include",
        min_value=1,
        max_value=10,
        value=3,
        help="Number of search result items the researcher will include in the workflow.",
    )
    run_button = st.button("Run workflow", use_container_width=True)

if run_button:
    with st.spinner("Running the agent workflow..."):
        try:
            writer_card_response = requests.get(f"{WRITER_AGENT_URL.rstrip('/')}/.well-known/agent-card.json", timeout=10)
            writer_card_response.raise_for_status()
            writer_card = writer_card_response.json()

            researcher_response = requests.get(
                f"{RESEARCHER_AGENT_URL.rstrip('/')}/research/{topic}",
                params={"task_name": task_name, "tone": tone, "count": result_count},
                timeout=20,
            )
            researcher_response.raise_for_status()
            researcher_response = researcher_response.json()
        except requests.RequestException as exc:
            st.error(f"The workflow could not complete: {exc}")
            st.stop()

    topic_value = researcher_response.get("topic", topic)
    research_summary = researcher_response.get("research_summary", "") or ""
    writer_response = researcher_response.get("writer_response", {}) or {}
    result_text = writer_response.get("result", "") if isinstance(writer_response, dict) else ""
    result_items = parse_research_items(research_summary)

    st.subheader("Workflow overview")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Search term", topic_value)
    col2.metric("Requested capability", task_name)
    col3.metric("Tone", tone)
    col4.metric("Research items", result_count)

    st.markdown("---")
    st.info("The researcher sent the prepared research to the writer, and the writer returned a transformed response.")

    st.markdown("### Status")
    status_text = writer_response.get("status", "success") if isinstance(writer_response, dict) else "completed"
    st.success(f"Post sent to writer: {task_name}")
    st.success(f"Writer responded: {status_text}")

    st.markdown("### Search results")
    if result_items:
        for item in result_items:
            with st.expander(item["title"]):
                if item.get("content"):
                    st.write(item["content"])
                if item.get("url"):
                    st.link_button("Open source", item["url"])
    else:
        st.caption("No structured search results were returned.")

    if st.button("View complete research summary", use_container_width=True, key="view_full_research"):
        st.session_state.show_full_research = not st.session_state.show_full_research

    if st.session_state.show_full_research:
        with st.expander("Complete research summary", expanded=True):
            st.text_area("Raw research summary", research_summary, height=280)

    st.markdown("---")
    st.markdown("### Writer output")
    with st.expander("Complete writer output", expanded=False):
        if isinstance(writer_response, dict):
            st.text_area("Writer result", result_text, height=280)
        else:
            st.code(str(writer_response))

    with st.expander("Writer agent card"):
        _render_agent_card(writer_card)

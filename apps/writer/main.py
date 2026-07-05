import os
import re
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request

from apps.schema import AgentCard

app = FastAPI(title="Writer Agent")

WRITER_BASE_URL = os.getenv("WRITER_AGENT_URL", "http://localhost:8001")

writer_card = AgentCard(
    name="ReportWriter",
    version="1.0.0",
    description="Specialized transformation node for turning raw research into polished, structured output.",
    capabilities=["summarize", "format-report", "cite-sources", "adjust-tone"],
    endpoints={
        "task_delegation": f"{WRITER_BASE_URL}/a2a/task",
        "agent_card": f"{WRITER_BASE_URL}/.well-known/agent-card.json",
    },
    metadata={
        "transport": "http",
        "protocol": "a2a",
        "default_task": "format-report",
    },
)


def _to_dict(model: AgentCard) -> Dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()


def _rewrite_tone(text: str, tone: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if not cleaned:
        return "No content provided."
    tone_map = {
        "professional": "This report outlines the following points in a concise, professional manner:",
        "technical": "The data supports the following technical observations:",
        "executive": "The key takeaway is that:",
    }
    prefix = tone_map.get(tone.lower(), tone_map["professional"])
    return f"{prefix}\n- {cleaned}"


def process_task(task_name: str, payload: Any, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    metadata = metadata or {}
    if task_name not in writer_card.capabilities:
        return {"status": "error", "message": f"Capability '{task_name}' is not supported. Choose from: {', '.join(writer_card.capabilities)}"}

    text = str(payload or "")
    if task_name == "format-report":
        result = f"# REPORT\n\n## Summary\n{text}\n\n## Next Steps\n- Review the supporting evidence\n- Confirm the narrative"
    elif task_name == "summarize":
        result = f"Summary:\n- {text[:280]}"
    elif task_name == "cite-sources":
        result = f"{text}\n\n[Source: research payload]"
    elif task_name == "adjust-tone":
        result = _rewrite_tone(text, metadata.get("tone", "professional"))
    else:
        result = text

    return {"status": "success", "task_name": task_name, "result": result}


@app.get("/.well-known/agent-card.json")
async def get_agent_card():
    return _to_dict(writer_card)


@app.post("/a2a/task")
async def handle_task(request: Request):
    task_data = await request.json()
    task_name = task_data.get("task_name", "")
    payload = task_data.get("payload", "")
    metadata = task_data.get("metadata") or {}
    return process_task(task_name, payload, metadata)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8001")))
import os
import re
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request

load_dotenv()

try:
    import litellm
    from litellm import completion as litellm_completion
except ImportError:  # pragma: no cover - graceful fallback when LiteLLM is not installed
    litellm = None
    litellm_completion = None

from apps.schema import AgentCard

app = FastAPI(title="Writer Agent")

WRITER_BASE_URL = os.getenv("WRITER_AGENT_URL", "http://localhost:8001")
WRITER_LLM_MODEL = os.getenv("WRITER_LLM_MODEL", "gemini/gemini-2.0-flash")
WRITER_USE_LLM = os.getenv("WRITER_USE_LLM", "true").strip().lower() in {"1", "true", "yes", "on"}
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

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
        "model": WRITER_LLM_MODEL,
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


def _build_prompt(task_name: str, text: str, metadata: Dict[str, Any]) -> str:
    tone = str(metadata.get("tone", "professional")).strip().lower() or "professional"
    if task_name == "format-report":
        return (
            "You are a report-writing assistant. Convert the supplied research notes into a polished markdown report. "
            "Use clear sections: Summary, Key Findings, and Next Steps. Keep it concise and professional.\n\n"
            f"Research notes:\n{text}"
        )
    if task_name == "summarize":
        return (
            "You are a research summarizer. Return a short, readable summary using bullet points and a clear main takeaway. "
            "Do not invent facts.\n\n"
            f"Research notes:\n{text}"
        )
    if task_name == "cite-sources":
        return (
            "You are a source-citation assistant. Read the supplied research payload and rewrite it with inline source markers "
            "that are easy to follow in markdown format. If no explicit sources are provided, use a generic [Source: research payload] marker.\n\n"
            f"Research notes:\n{text}"
        )
    if task_name == "adjust-tone":
        return (
            f"Rewrite the text in a {tone} tone while preserving the underlying facts and structure.\n\n"
            f"Original text:\n{text}"
        )
    return text


def _extract_llm_text(response: Any) -> Optional[str]:
    if response is None:
        return None

    choices = getattr(response, "choices", None) or []
    if choices:
        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        if message:
            content = getattr(message, "content", None)
            if isinstance(content, str):
                return content.strip() or None
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text") or item.get("content") or ""
                        parts.append(str(text))
                combined = "\n".join(part for part in parts if part).strip()
                if combined:
                    return combined
        if isinstance(first_choice, dict):
            content = first_choice.get("message", {}).get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()

    text = getattr(response, "model_response", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    return None


def _call_llm(task_name: str, text: str, metadata: Dict[str, Any]) -> Optional[str]:
    if not WRITER_USE_LLM or not GEMINI_API_KEY or litellm_completion is None:
        return None

    prompt = _build_prompt(task_name, text, metadata)
    try:
        response = litellm_completion(
            model=WRITER_LLM_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a thoughtful writer for a multi-agent research assistant. Keep the final response concise, structured, and factual.",
                },
                {"role": "user", "content": prompt},
            ],
            api_key=GEMINI_API_KEY,
            temperature=0.2,
        )
    except Exception:
        return None

    return _extract_llm_text(response)


def _fallback_result(task_name: str, text: str, metadata: Dict[str, Any]) -> str:
    if task_name == "format-report":
        return f"# REPORT\n\n## Summary\n{text}\n\n## Next Steps\n- Review the supporting evidence\n- Confirm the narrative"
    if task_name == "summarize":
        return f"Summary:\n- {text[:280]}"
    if task_name == "cite-sources":
        return f"{text}\n\n[Source: research payload]"
    if task_name == "adjust-tone":
        return _rewrite_tone(text, metadata.get("tone", "professional"))
    return text


def process_task(task_name: str, payload: Any, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    metadata = metadata or {}
    if task_name not in writer_card.capabilities:
        return {"status": "error", "message": f"Capability '{task_name}' is not supported. Choose from: {', '.join(writer_card.capabilities)}"}

    text = str(payload or "").strip()
    if not text:
        return {"status": "success", "task_name": task_name, "result": "No content provided."}

    llm_result = _call_llm(task_name, text, metadata)
    result = llm_result or _fallback_result(task_name, text, metadata)
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
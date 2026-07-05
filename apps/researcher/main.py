import os
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Researcher Agent")

WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://localhost:8001")
RESEARCHER_AGENT_URL = os.getenv("RESEARCHER_AGENT_URL", "http://localhost:8002")


def perform_research(topic: str) -> str:
    searxng_url = os.getenv("SEARXNG_URL", "").strip() or os.getenv("SEARXNG_BASE_URL", "http://localhost:8888").strip()
    if searxng_url:
        try:
            response = httpx.get(
                f"{searxng_url.rstrip('/')}/search",
                params={"q": topic, "format": "json", "categories": "general"},
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()
            results = payload.get("results", [])
            if results:
                snippets = [
                    f"- {item.get('title', topic)}: {item.get('content', item.get('url', ''))}"
                    for item in results[:3]
                ]
                return f"Research for {topic}:\n" + "\n".join(snippets)
        except Exception:
            pass

    return (
        f"Research for {topic}:\n"
        "- Public web search unavailable in this environment; using a local placeholder response.\n"
        "- The workflow still demonstrates agent-to-agent delegation."
    )


async def read_writer_card() -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{WRITER_AGENT_URL.rstrip('/')}/.well-known/agent-card.json")
        response.raise_for_status()
        return response.json()


async def delegate_to_writer(raw_data: str, task_name: str, tone: str) -> Dict[str, Any]:
    card = await read_writer_card()
    capabilities: List[str] = card.get("capabilities", [])
    if task_name not in capabilities:
        raise HTTPException(status_code=400, detail=f"Task '{task_name}' is not supported by the discovered writer card")

    async with httpx.AsyncClient(timeout=10.0) as client:
        payload = {
            "task_name": task_name,
            "payload": raw_data,
            "metadata": {"tone": tone},
        }
        response = await client.post(f"{WRITER_AGENT_URL.rstrip('/')}/a2a/task", json=payload)
        response.raise_for_status()
        return response.json()


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "ok", "writer_url": WRITER_AGENT_URL, "researcher_url": RESEARCHER_AGENT_URL}


@app.get("/discover")
async def discover_writer() -> Dict[str, Any]:
    return await read_writer_card()


@app.get("/research/{topic}")
async def run_research_workflow(topic: str, task_name: str = "format-report", tone: str = "professional"):
    data = perform_research(topic)
    writer_card = await read_writer_card()
    writer_response = await delegate_to_writer(data, task_name, tone)
    return {
        "status": "workflow_complete",
        "topic": topic,
        "task_name": task_name,
        "writer_card": writer_card,
        "research_summary": data,
        "writer_response": writer_response,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8002")))
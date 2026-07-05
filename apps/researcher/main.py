import os
from typing import Any, Dict, List

import httpx
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Researcher Agent")

WRITER_AGENT_URL = os.getenv("WRITER_AGENT_URL", "http://localhost:8001")
RESEARCHER_AGENT_URL = os.getenv("RESEARCHER_AGENT_URL", "http://localhost:8002")


def _resolve_searxng_url() -> str:
    configured = os.getenv("SEARXNG_URL", "").strip() or os.getenv("SEARXNG_BASE_URL", "").strip()
    if configured:
        return configured

    if os.path.exists("/.dockerenv"):
        return "http://searxng:8080"

    return "http://localhost:8888"


def _build_fallback_research(topic: str, reason: str = "search backend unavailable") -> str:
    return (
        f"Research for {topic}:\n"
        f"- Topic: {topic}\n"
        "- Search status: local search is unavailable or returned no results.\n"
        f"- Reason: {reason}\n"
        "- Potential angle: summarize the main problem, compare the leading options, and list the next steps.\n"
        "- A2A handoff: the researcher will package these findings and delegate them to the writer agent."
    )


def _extract_search_results(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    results = payload.get("results") or payload.get("items") or []
    if not isinstance(results, list):
        return []

    normalized: List[Dict[str, str]] = []
    for item in results[:5]:
        if not isinstance(item, dict):
            continue
        title = item.get("title") or item.get("name") or "Search result"
        content = item.get("content") or item.get("snippet") or item.get("description") or item.get("url") or ""
        url = item.get("url") or item.get("link") or ""
        normalized.append({"title": str(title), "content": str(content), "url": str(url)})
    return normalized


def perform_research(topic: str) -> str:
    searxng_url = _resolve_searxng_url()
    if searxng_url:
        try:
            response = httpx.get(
                f"{searxng_url.rstrip('/')}/search",
                params={"q": topic, "format": "json", "categories": "general"},
                headers={
                    "X-Real-IP": "127.0.0.1",
                    "X-Forwarded-For": "127.0.0.1",
                },
                timeout=10.0,
            )
            response.raise_for_status()
            payload = response.json()
            results = _extract_search_results(payload)
            if results:
                snippets = [
                    f"- {item['title']}: {item['content'] or item['url']}"
                    for item in results[:3]
                ]
                return f"Research for {topic}:\n" + "\n".join(snippets)
            return _build_fallback_research(topic, "the search backend returned no usable results")
        except Exception as exc:
            return _build_fallback_research(topic, str(exc))

    return _build_fallback_research(topic)


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
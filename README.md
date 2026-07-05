# Research Assistant A2A SDK

This project demonstrates a simple Agent-to-Agent (A2A) workflow in which a Researcher agent discovers a Writer agent, validates its capabilities, and delegates a writing task.

## What is A2A?
Agent-to-Agent communication is the idea that one AI service can discover another AI service, understand what it can do, and send it a task.

In a real multi-agent system, this usually looks like:
1. An agent exposes an Agent Card describing its identity and capabilities.
2. Another agent reads that card.
3. The caller checks whether the requested capability exists.
4. The caller sends a task payload to the target agent.
5. The target agent processes the request and returns a result.

This repository implements that pattern in a lightweight, local-first way.

## What this project includes
- A Writer agent that exposes an Agent Card at /.well-known/agent-card.json
- A Researcher agent that reads the card and delegates work to the Writer
- A Streamlit demo UI for showing the full interaction end to end
- Docker Compose support for running everything together

## How we implemented it

### 1. Writer Agent
The Writer agent defines its identity in an Agent Card with:
- a name and version,
- a description,
- a list of capabilities such as summarize, format-report, cite-sources, and adjust-tone,
- endpoint information for discovery and task execution.

It exposes:
- GET /.well-known/agent-card.json for discovery
- POST /a2a/task for receiving delegated tasks

### 2. Researcher Agent
The Researcher agent:
- fetches the Writer agent card,
- checks whether the requested capability is supported,
- collects research content,
- sends the task to the Writer agent,
- returns the resulting output.

It also uses a free web search fallback via duckduckgo-search when a real search backend is not configured.

### 3. Streamlit Demo
The Streamlit app provides a simple UI where you can:
- enter a topic,
- choose a writer capability,
- run the full workflow,
- inspect the discovered Agent Card and the final result.

## Environment variables
Copy .env.example to .env and adjust as needed:

```bash
cp .env.example .env
```

Supported variables:
- WRITER_AGENT_URL: base URL of the writer service
- RESEARCHER_AGENT_URL: base URL of the researcher service
- PORT: port for the current service

## Run locally

```bash
python -m pip install -r requirements.txt
chmod +x start_agents.sh
./start_agents.sh
```

Then open:
- Writer card: http://localhost:8001/.well-known/agent-card.json
- Researcher health: http://localhost:8002/health
- Streamlit UI: http://localhost:8501

## Run with Docker Compose

```bash
docker compose up --build
```

## Example workflow

1. The Researcher calls /discover to fetch the Writer Agent Card.
2. It checks the requested capability against the card.
3. It posts the task to /a2a/task on the Writer service.
4. The Streamlit demo displays the discovered card and the final response.

## Why this matters
This example shows the basic building blocks of agent interoperability:
- discovery,
- capability negotiation,
- delegated execution,
- and a simple human-readable interface for observing the interaction.

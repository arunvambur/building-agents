# Agent Runtime – Running CLI and API

This document explains how to run the **plugin-based agent runtime** in two modes:

1. CLI mode (interactive terminal chat)
2. API mode (FastAPI service)

---

# Prerequisites

### 1. Python Version

Use Python **3.10+**

```bash
python --version
```

---

### 2. Install dependencies

If using editable install:

```bash
pip install -e .
```

Or install manually:

```bash
pip install langgraph langchain langchain-openai chromadb fastapi uvicorn python-dotenv pydantic
```

---

### 3. Environment variables

Create a `.env` file in project root:

```bash
OPENAI_API_KEY=your_key_here
```

---

# Running CLI Mode

CLI mode is useful for:

• local testing
• debugging agents
• experimenting with prompts
• validating tool execution

---

### Start CLI

```bash
python -m agent_runtime.app.cli
```

---

### Example session

```text
You: tell me about Cornwall
Assistant: Cornwall is a historic county...

You: find BnB in St Ives for 2 rooms
Assistant: Here are available BnBs...
```

---

### CLI execution flow

```text
User input
   ↓
Router plugin
   ↓
Selected agent plugin
   ↓
Tools executed (if needed)
   ↓
Response returned
```

---

# Running API Mode

API mode exposes the runtime as an HTTP service using FastAPI.

---

### Start API server

```bash
uvicorn agent_runtime.app.api:app --reload
```

---

### Default URL

```
http://127.0.0.1:8000
```

---

# API Endpoints

## Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

---

## Chat Endpoint

```http
POST /chat
```

### Request

```json
{
  "message": "Find a BnB in St Ives for 2 rooms"
}
```

### Response

```json
{
  "response": "Here are available BnBs in St Ives...",
  "agent_used": "accommodation_booking_agent"
}
```

---

## Debug Endpoint

Returns raw LangGraph state for troubleshooting.

```http
POST /debug
```

---

## Streaming Endpoint (optional)

```http
POST /chat/stream
```

Returns streamed response.

---

# Testing API using curl

```bash
curl -X POST http://127.0.0.1:8000/chat \
-H "Content-Type: application/json" \
-d '{"message":"weather in Cornwall"}'
```

---

# Project Structure Reminder

```text
src/agent_runtime/
    app/
        cli.py
        api.py
        bootstrap.py

    core/
        runtime.py
        registry.py

    agents/
        travel_agent/
        booking_agent/

    tools/
        travel_tools.py
        booking_tools.py
```

---

# Running in Development Mode

Auto reload when code changes:

```bash
uvicorn agent_runtime.app.api:app --reload
```

---

# Running with Docker (optional)

```bash
docker build -t agent-runtime .
docker run -p 8000:8000 agent-runtime
```

---

# Quick Start Summary

### CLI

```bash
python -m agent_runtime.app.cli
```

---

### API

```bash
uvicorn agent_runtime.app.api:app --reload
```

---

# Next recommended enhancements

• add conversation memory
• add authentication
• add tracing (LangSmith)
• add async tool execution
• deploy via Docker/Kubernetes
• multi-tenant routing support

---

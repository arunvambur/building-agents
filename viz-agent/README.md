# Viz Agent

A plugin-based multi-agent runtime built on LangGraph for data visualization and processing,
with a Next.js chat UI.

---

## Prerequisites

### Python 3.10+

```bash
python --version
```

### Node.js 18+

```bash
node --version
npm --version
```

### Environment variables

Create a `.env` file in the project root:

```bash
OPENAI_API_KEY=your_key_here
```

---

## Project Structure

```
viz-agent/
├── data/
│   └── hotel_db/
│       └── cornwall_hotels.db       SQLite hotel database
├── src/
│   ├── agents/
│   │   ├── data_agent/              Queries structured data via tools
│   │   ├── viz_agent/               Builds and renders visualizations
│   │   └── supervisor/              LangGraph supervisor — sequences agents
│   ├── app/
│   │   ├── api/                     FastAPI application
│   │   ├── cli/                     Interactive terminal chat
│   │   └── bootstrap.py             Wires runtime, registry, renderers
│   ├── core/
│   │   ├── dsl/                     VisualizationSpec schema + validator
│   │   ├── plugin/                  Interfaces, registry, runtime, guardrail
│   │   └── renderer/                Renderer base, registry, Excel, Tableau
│   ├── infra/                       LLM model, checkpointer
│   └── tools/                       QueryTools (SQLite), RenderingTools
├── chat/                            Next.js chat UI
└── tests/                           pytest test suite
```

---

## Install Python Dependencies

From the project root:

```bash
pip install -e .
```

---

## Running the Backend API

The FastAPI backend must be started from the `src/` directory so that absolute imports resolve correctly.

```bash
cd src
python -m uvicorn app.api.api:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

```
http://localhost:8000
```

Interactive API docs (Swagger UI):

```
http://localhost:8000/docs
```

---

## Running the CLI

For local testing and debugging without the UI:

```bash
cd src
python -m app.cli.cli
```

Example session:

```
Viz Agent ready. Type 'exit' to quit.
You: show me hotels in St Ives
Agent: The St Ives Bay Resort is available with 6 rooms...

You: generate an Excel chart of ratings by town
Agent: Your Excel report has been generated at /tmp/abc123.xlsx
```

---

## Running the Chat UI

In a separate terminal:

```bash
cd chat
npm install
npm run dev
```

The UI will be available at:

```
http://localhost:3000
```

The UI proxies all API calls to `http://localhost:8000`. To change the backend URL, edit `chat/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## API Endpoints

### Health Check

```http
GET /health
```

Response:

```json
{ "status": "ok" }
```

---

### Visualize

```http
POST /visualize
```

Request:

```json
{
  "message": "Show me a bar chart of hotel ratings by town",
  "session_id": "optional-session-id-for-conversation-continuity"
}
```

Response:

```json
{
  "response": "Your Excel report has been generated...",
  "session_id": "a1b2c3d4-..."
}
```

Pass the returned `session_id` in subsequent requests to maintain conversation history.

---

### Test with curl

```bash
curl -X POST http://localhost:8000/visualize \
  -H "Content-Type: application/json" \
  -d '{"message": "which hotels in Newquay have rooms available?"}'
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Quick Start (both services)

Open two terminals:

**Terminal 1 — Backend**

```bash
cd src
python -m uvicorn app.api.api:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 — Frontend**

```bash
cd chat
npm install
npm run dev
```

Then open `http://localhost:3000`.

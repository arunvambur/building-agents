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

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

**Using OpenAI (default):**
```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

**Using a local model via Ollama:**
```bash
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
```

Make sure Ollama is running and the model is pulled before starting:
```bash
ollama pull llama3.1:8b
ollama serve
```

> Note: Ollama models must support tool calling. Confirmed working: `llama3.1`, `qwen2.5`.
> `gemma3` does not support tool calling and will not work.

---

## Project Structure

```
viz-agent/
├── .env.example
├── data/
│   └── hotel_db/
│       └── cornwall_hotels.db           SQLite hotel database
├── src/
│   ├── agents/
│   │   ├── data_agent/                  Queries structured data via tools
│   │   ├── viz_agent/                   Builds and renders visualizations
│   │   └── supervisor/                  LangGraph supervisor — sequences agents
│   ├── app/
│   │   ├── api/                         FastAPI application + routes
│   │   ├── cli/                         Interactive terminal chat
│   │   └── bootstrap.py                 Wires runtime, registry, renderers
│   ├── core/
│   │   ├── dsl/                         VisualizationSpec schema + validator
│   │   ├── plugin/                      Interfaces, registry, runtime, guardrail
│   │   └── renderer/                    Image, Excel, PDF, PPT, Tableau renderers
│   ├── infra/                           LLM provider factory, checkpointer
│   └── tools/                           QueryTools (SQLite), RenderingTools
├── chat/                                Next.js chat UI
└── tests/                               pytest test suite
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

You: show me a bar chart of hotel ratings by town
Agent: data:image/png;base64,...
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

To change the backend URL, edit `chat/.env.local`:

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

Response (image):

```json
{
  "session_id": "a1b2c3d4-...",
  "type": "image",
  "content": "<base64 PNG string>"
}
```

Response (file):

```json
{
  "session_id": "a1b2c3d4-...",
  "type": "file",
  "content": "/download/<file_id>",
  "filename": "cornwall_hotels_a1b2c3d4.xlsx",
  "file_format": "excel"
}
```

Response (text):

```json
{
  "session_id": "a1b2c3d4-...",
  "type": "text",
  "content": "The St Ives Bay Resort has 6 rooms available..."
}
```

Pass the returned `session_id` in subsequent requests to maintain conversation history.

---

### Download File

```http
GET /download/{file_id}
```

Returns the generated file (Excel, PDF, or PPT) as a binary download.

---

### Test with curl

```bash
curl -X POST http://localhost:8000/visualize \
  -H "Content-Type: application/json" \
  -d '{"message": "which hotels in Newquay have rooms available?"}'
```

---

## Chart Types

### Supported Chart Types

| Chart Type | Trigger phrases | y2 field | Description |
|------------|----------------|----------|-------------|
| `bar` | "bar chart", "bar graph" | No | Vertical bars grouped by category |
| `horizontal_bar` | "horizontal bar", "sideways bar" | No | Horizontal bars — better for long labels |
| `stacked_bar` | "stacked bar" | Yes | Two measures stacked vertically per category |
| `grouped_bar` | "grouped bar", "side by side" | Yes | Two measures side-by-side per category |
| `line` | "line chart", "trend" | No | Connected data points over categories |
| `area` | "area chart", "filled line" | Yes | Line chart with filled area beneath |
| `scatter` | "scatter", "scatter plot" | No | Individual data points on x/y axes |
| `pie` | "pie chart" | No | Proportional slices — requires aggregation |
| `donut` | "donut chart", "doughnut" | No | Pie with hollow centre showing total |
| `histogram` | "histogram", "distribution", "frequency" | No | Frequency distribution with mean line |
| `heatmap` | "heatmap", "heat map", "matrix" | Yes — column dimension | 2D colour matrix; y2=column field, y=value |
| `bubble` | "bubble chart", "bubble" | Yes — size field | Scatter with bubble size encoding |
| `waterfall` | "waterfall", "waterfall chart" | No | Cumulative incremental values, green/red bars |
| `gauge` | "gauge", "kpi", "speedometer", "meter" | No | Semicircular KPI gauge; requires aggregation |

> `y2` field usage:
> - `stacked_bar`, `grouped_bar`, `area`: second measure to compare
> - `heatmap`: column dimension field (e.g. `price_single` as columns, `town` as rows)
> - `bubble`: size encoding field (e.g. `available_rooms`)

---

### Output Format Rules

| Output | Trigger phrases | Result |
|--------|----------------|--------|
| `image` | Default — any chart/graph request | Inline PNG displayed in chat |
| `excel` | "Excel", "spreadsheet", ".xlsx" | Downloadable `.xlsx` file |
| `pdf` | "PDF", "PDF report" | Downloadable `.pdf` file |
| `ppt` | "PowerPoint", "presentation", "slides" | Downloadable `.pptx` file |

---

### Renderer Support Matrix

| Chart Type | Image (PNG) | Excel (.xlsx) | PDF (.pdf) | PPT (.pptx) |
|------------|:-----------:|:-------------:|:----------:|:-----------:|
| bar | matplotlib | BarChart col | matplotlib | matplotlib |
| horizontal_bar | matplotlib | BarChart bar | matplotlib | matplotlib |
| stacked_bar | matplotlib | BarChart stacked | matplotlib | matplotlib |
| grouped_bar | matplotlib | BarChart clustered | matplotlib | matplotlib |
| line | matplotlib | LineChart | matplotlib | matplotlib |
| area | matplotlib | AreaChart | matplotlib | matplotlib |
| scatter | matplotlib | ScatterChart | matplotlib | matplotlib |
| pie | matplotlib | PieChart | matplotlib | matplotlib |
| donut | matplotlib | DoughnutChart | matplotlib | matplotlib |
| histogram | matplotlib | BarChart (binned) | matplotlib | matplotlib |
| heatmap | matplotlib | Data table only | matplotlib | matplotlib |
| bubble | matplotlib | BubbleChart | matplotlib | matplotlib |
| waterfall | matplotlib | BarChart stacked | matplotlib | matplotlib |
| gauge | matplotlib | Data table only | matplotlib | matplotlib |

> PDF and PPT renderers embed matplotlib-generated PNGs directly — all 14 chart types are
> fully supported across all output formats.
> Heatmap and Gauge have no native Excel chart equivalent; Excel output shows the data table only.

---


## Data Tools

The data agent has access to the following SQLite tools against `cornwall_hotels.db`:

| Tool | Description |
|------|-------------|
| `search_hotels` | Filter hotels by town and/or minimum rating |
| `get_room_offers` | Get pricing and availability for a specific hotel |
| `list_all_hotels_with_offers` | All hotels joined with room pricing — used for charts |
| `get_hotels_by_price` | Filter hotels by maximum single or double room price |

---

## Running Tests

```bash
python -m pytest tests/ -v
```

Current test coverage: **99 tests** across 10 test files.

| Test file | Coverage |
|-----------|---------|
| `test_dsl_validator.py` | DSL schema validation rules |
| `test_guardrail.py` | Keyword fast-pass + LLM fallback guardrail |
| `test_plugin_registry.py` | Agent/tool registration and binding |
| `test_renderer_registry.py` | Renderer lookup by format |
| `test_image_renderer.py` | All 10 high-value chart types as PNG |
| `test_excel_renderer.py` | All 10 high-value chart types as Excel |
| `test_pdf_renderer.py` | PDF rendering with charts and tables |
| `test_ppt_renderer.py` | PPT slide count, filters slide, chart types |
| `test_query_tools.py` | All 4 SQLite hotel DB tools |
| `test_medium_charts.py` | Heatmap, bubble, waterfall, gauge — image + Excel |

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

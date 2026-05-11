# Project Context
Plugin-based multi-agent runtime built on LangGraph for data visualization and processing.

# Tech Stack
- **Language**: Python 3.10+
- **Core Frameworks**: LangGraph, LangChain, FastAPI, Pydantic
- **Vector DB**: ChromaDB
- **Build System**: setuptools (`pyproject.toml`)

# Architecture & Design Patterns
- **Plugin System**: The core architecture relies on plugins defined in `src/core/plugin/interfaces.py`.
  - `AgentPlugin`: Must implement `build_graph(llm)`, `initialize()`, `shutdown()`.
  - `RouterPlugin`: Must implement `route(state) -> str`.
  - `ToolPlugin`: Must implement `get_tools()`, `initialize()`, `shutdown()`.
  - `GuardrailPlugin`: Must implement `validate(state)`.
- **State Management**: LangGraph state is passed as a dictionary containing a `messages` list (e.g., `{"messages": [HumanMessage(...)]}`).
- **API Layer**: FastAPI (`src/app/api`) exposes the runtime. Endpoints should be `async`.
- **CLI Layer**: Interactive terminal chat available via `src/app/cli`.

# Coding Conventions
- **Formatting**: Use Black with a line length of 100.
- **Typing**: Use standard Python type hints and Pydantic models for validation.
- **Imports**: Group imports logically. Use absolute imports starting from `app`, `core`, `agents`, etc., based on the `src` root.
- **Testing**: Write tests using `pytest`. Place them in the `tests/` directory.

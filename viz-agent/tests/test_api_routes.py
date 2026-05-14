"""
Tests for app/api/routes — /health, /visualize, /download endpoints.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage


@pytest.fixture(autouse=True)
def _isolate_file_store():
    """Clear the in-memory download store before and after every test."""
    from app.api.routes.download import _file_store
    _file_store.clear()
    yield
    _file_store.clear()


# ---------------------------------------------------------------------------
# Health route
# ---------------------------------------------------------------------------

def _make_health_app():
    from fastapi import FastAPI
    from app.api.routes.health import router
    app = FastAPI()
    app.include_router(router)
    return app


def test_health_ok_when_db_reachable(tmp_path):
    import sqlite3
    db = tmp_path / "test.db"
    sqlite3.connect(str(db)).close()

    with patch("app.api.routes.health._DB_PATH", str(db)):
        client = TestClient(_make_health_app())
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_unhealthy_when_db_missing():
    with patch("sqlite3.connect", side_effect=Exception("cannot open")):
        client = TestClient(_make_health_app())
        resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "unhealthy"


# ---------------------------------------------------------------------------
# Download route
# ---------------------------------------------------------------------------

def _make_download_app():
    from fastapi import FastAPI
    from app.api.routes.download import router
    app = FastAPI()
    app.include_router(router)
    return app


def test_download_unknown_id_returns_404():
    client = TestClient(_make_download_app())
    resp = client.get("/download/nonexistent-id")
    assert resp.status_code == 404


def test_download_registered_file_returns_200(tmp_path):
    from app.api.routes.download import register_file

    f = tmp_path / "report.xlsx"
    f.write_bytes(b"fake xlsx content")

    file_id = register_file(str(f), "report.xlsx")
    client = TestClient(_make_download_app())
    resp = client.get(f"/download/{file_id}")
    assert resp.status_code == 200
    assert resp.content == b"fake xlsx content"


def test_download_removed_file_returns_410():
    from app.api.routes.download import register_file

    file_id = register_file("/nonexistent/path/file.xlsx", "file.xlsx")
    client = TestClient(_make_download_app())
    resp = client.get(f"/download/{file_id}")
    assert resp.status_code == 410


# ---------------------------------------------------------------------------
# Visualize route
# ---------------------------------------------------------------------------

def _make_visualize_app(runtime):
    from fastapi import FastAPI
    from app.api.routes.download import router as dl_router
    from app.api.routes.visualize import register

    app = FastAPI()
    app.include_router(dl_router)
    app.include_router(register(runtime))
    return app


def _mock_runtime(content: str):
    runtime = MagicMock()
    runtime.ainvoke = AsyncMock(
        return_value={"messages": [AIMessage(content=content)]}
    )
    return runtime


def test_visualize_returns_image_response():
    b64 = "data:image/png;base64,iVBORw0KGgo="
    client = TestClient(_make_visualize_app(_mock_runtime(b64)))
    resp = client.post("/visualize", json={"message": "show a bar chart"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "image"
    assert body["content"] == "iVBORw0KGgo="
    assert body["session_id"]


def test_visualize_returns_text_response():
    client = TestClient(_make_visualize_app(_mock_runtime("I cannot help with that.")))
    resp = client.post("/visualize", json={"message": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "text"
    assert body["content"] == "I cannot help with that."


def test_visualize_returns_file_response_for_excel(tmp_path):
    xlsx = tmp_path / f"{uuid.uuid4()}.xlsx"
    xlsx.write_bytes(b"fake")

    client = TestClient(_make_visualize_app(_mock_runtime(f"file://{xlsx}")))
    resp = client.post("/visualize", json={"message": "generate excel"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "file"
    assert body["file_format"] == "excel"
    assert body["content"].startswith("/download/")
    assert body["filename"].endswith(".xlsx")


def test_visualize_preserves_session_id():
    client = TestClient(_make_visualize_app(_mock_runtime("ok")))
    resp = client.post("/visualize", json={"message": "hi", "session_id": "my-session-123"})
    assert resp.json()["session_id"] == "my-session-123"


def test_visualize_generates_session_id_when_absent():
    client = TestClient(_make_visualize_app(_mock_runtime("ok")))
    resp = client.post("/visualize", json={"message": "hi"})
    assert resp.json()["session_id"]


@pytest.mark.parametrize("ext,expected_format", [
    (".xlsx", "excel"),
    (".pdf",  "pdf"),
    (".pptx", "ppt"),
])
def test_visualize_file_format_detection(ext, expected_format, tmp_path):
    f = tmp_path / f"{uuid.uuid4()}{ext}"
    f.write_bytes(b"fake")

    client = TestClient(_make_visualize_app(_mock_runtime(f"file://{f}")))
    resp = client.post("/visualize", json={"message": "generate report"})
    assert resp.json()["file_format"] == expected_format

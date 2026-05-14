import os
import sqlite3

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()

_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "data", "hotel_db", "cornwall_hotels.db")
)


@router.get("/health")
async def health() -> JSONResponse:
    """
    Liveness + readiness check.
    Verifies the SQLite database is reachable before reporting healthy.
    """
    try:
        conn = sqlite3.connect(_DB_PATH, timeout=2)
        conn.execute("SELECT 1")
        conn.close()
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "detail": f"Database unreachable: {exc}"},
        )

    return JSONResponse(status_code=200, content={"status": "ok"})

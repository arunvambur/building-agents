import os
import uuid
from typing import Dict, Tuple

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# In-memory store: file_id → (absolute_path, filename)
# Files are written to the OS temp dir by the Excel renderer.
_file_store: Dict[str, Tuple[str, str]] = {}


def register_file(path: str, filename: str) -> str:
    """
    Register a file path in the store and return a unique download ID.
    Called by the rendering pipeline after a file is written to disk.
    """
    file_id = str(uuid.uuid4())
    _file_store[file_id] = (path, filename)
    return file_id


@router.get("/download/{file_id}")
async def download_file(file_id: str):
    entry = _file_store.get(file_id)
    if not entry:
        raise HTTPException(status_code=404, detail="File not found or has expired.")

    path, filename = entry
    if not os.path.exists(path):
        raise HTTPException(status_code=410, detail="File has been removed from the server.")

    return FileResponse(
        path=path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

import os
import uuid
from typing import Dict, Tuple

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()

# In-memory store: file_id → (absolute_path, filename)
_file_store: Dict[str, Tuple[str, str]] = {}

_MIME_TYPES = {
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pdf":  "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def register_file(path: str, filename: str) -> str:
    """Register a rendered file and return a unique download ID."""
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

    ext = os.path.splitext(filename)[-1].lower()
    media_type = _MIME_TYPES.get(ext, "application/octet-stream")

    return FileResponse(path=path, filename=filename, media_type=media_type)

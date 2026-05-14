import logging
import logging.config

from fastapi import FastAPI

from app.api.routes import download, health
from app.api.routes.visualize import register as register_visualize
from app.bootstrap import build_runtime

# Configure logging for the entire application.
# All agent/supervisor/runtime loggers inherit from the root.
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            "datefmt": "%H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "root": {
        "level": "DEBUG",
        "handlers": ["console"],
    },
    # Quieten noisy third-party loggers
    "loggers": {
        "httpx": {"level": "WARNING"},
        "httpcore": {"level": "WARNING"},
        "openai": {"level": "WARNING"},
        "langchain": {"level": "WARNING"},
        "langgraph": {"level": "WARNING"},
        "chromadb": {"level": "WARNING"},
        "uvicorn": {"level": "INFO"},
        "uvicorn.access": {"level": "INFO"},
        "matplotlib": {"level": "WARNING"},
    },
})

app = FastAPI(title="Viz Agent API", version="0.1.0")

runtime = build_runtime()

app.include_router(health.router)
app.include_router(download.router)
app.include_router(register_visualize(runtime))

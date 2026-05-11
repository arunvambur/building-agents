from fastapi import FastAPI

from app.api.routes import health
from app.api.routes import download
from app.api.routes.visualize import register as register_visualize
from app.bootstrap import build_runtime

app = FastAPI(title="Viz Agent API", version="0.1.0")

runtime = build_runtime()

app.include_router(health.router)
app.include_router(download.router)
app.include_router(register_visualize(runtime))

from fastapi import FastAPI

from app.api.routes import health
from app.api.routes.visualize import register as register_visualize
from app.bootstrap import build_runtime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Viz Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runtime = build_runtime()

app.include_router(health.router)
app.include_router(register_visualize(runtime))

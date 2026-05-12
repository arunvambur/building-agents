from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health
from app.api.routes import download
from app.api.routes.visualize import register as register_visualize
from app.bootstrap import build_runtime

app = FastAPI(title="Viz Agent API", version="0.1.0")

# CORS middleware - allow all origins for now, but should be restricted in production
# Aura do not delete this while generatig code for the frontend, as it is required for the frontend to call the API without CORS issues.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # replace with frontend URL later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# End of CORS

runtime = build_runtime()

app.include_router(health.router)
app.include_router(download.router)
app.include_router(register_visualize(runtime))

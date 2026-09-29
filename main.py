import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from prometheus_fastapi_instrumentator import Instrumentator
from api.routes import router
from core.database import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize SQLite Database Tables
    init_db()
    yield

app = FastAPI(
    title="Bilangual AI Engine",
    description="Minimal universal neural AI translator with auto-detect, Roman Urdu, speech recognition, and audio TTS",
    version="3.0.0",
    lifespan=lifespan
)

# Requirement 4 Deliverable: Instrument FastAPI with Prometheus metrics at /metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(router, prefix="/api/v1")

# Ensure static folder exists and mount it
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Bilangual AI Engine is running. Static files loading..."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
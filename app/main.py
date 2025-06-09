from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .routers import events, weather
from .config import settings

app = FastAPI(
    title="Weather Event Planner",
    description="A service for planning outdoor events with weather integration",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(weather.router, prefix="/weather", tags=["weather"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Weather Event Planner API",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    } 
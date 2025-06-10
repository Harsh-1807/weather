from fastapi import FastAPI, HTTPException, Request, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .routers import events, weather, auth, test_db
from .config import settings
from datetime import datetime
import asyncio
from .tasks.weather_notifications import start_notification_tasks
from .services.event_service import event_service
from .models import EventCreate, EventUpdate
from .models.user import UserDB
from .database import engine, get_db
from sqlalchemy.orm import Session
import logging

# Create database tables
UserDB.metadata.create_all(bind=engine)

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
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(weather.router, prefix="/weather", tags=["weather"])
app.include_router(test_db.router, prefix="/test", tags=["database-tests"])

# Templates
templates = Jinja2Templates(directory="app/templates")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Start background tasks on application startup"""
    asyncio.create_task(start_notification_tasks())

@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/events/")
async def create_event(
    title: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    email: str = Form(...),
    event_type: str = Form("outdoor_sports")  # Default to outdoor_sports
):
    """Create a new event with weather data"""
    try:
        # Parse date and time
        event_datetime = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        
        # Create event with default type if not specified
        if event_type not in ["outdoor_sports", "formal_events"]:
            event_type = "outdoor_sports"
            
        event = event_service.create_event(
            title=title,
            description=description,
            location=location,
            date=event_datetime,
            email=email,
            event_type=event_type
        )
        
        return {"message": "Event created successfully", "event": event}
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/events/")
async def get_events():
    return await event_service.get_events()

@app.get("/events/{event_id}")
async def get_event(event_id: str):
    event = await event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@app.put("/events/{event_id}")
async def update_event(event_id: str, event: EventUpdate):
    updated_event = await event_service.update_event(event_id, event)
    if not updated_event:
        raise HTTPException(status_code=404, detail="Event not found")
    return updated_event

@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    success = await event_service.delete_event(event_id)
    if not success:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted successfully"}

@app.get("/api/events/{event_id}/alternatives")
async def get_alternative_dates(event_id: str):
    """Get alternative dates with better weather conditions"""
    try:
        alternatives = await event_service.get_alternative_dates(event_id)
        if "error" in alternatives:
            raise HTTPException(status_code=404, detail=alternatives["error"])
        return alternatives
    except Exception as e:
        logger.error(f"Error getting alternative dates: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
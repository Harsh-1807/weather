from fastapi import APIRouter, HTTPException
from typing import List
from ..models import Event, EventCreate, EventUpdate, WeatherResponse, WeatherAlternatives
from ..services.event_service import event_service

router = APIRouter()

@router.post("/", response_model=Event)
async def create_event(event: EventCreate):
    try:
        return await event_service.create_event(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Event])
async def get_events():
    return event_service.get_all_events()

@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: str):
    event = event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.put("/{event_id}", response_model=Event)
async def update_event(event_id: str, event_update: EventUpdate):
    event = await event_service.update_event(event_id, event_update)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event

@router.post("/{event_id}/weather-check", response_model=WeatherResponse)
async def check_event_weather(event_id: str):
    event = event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    if not event.weather_data:
        raise HTTPException(status_code=400, detail="No weather data available for this event")
    
    return WeatherResponse(
        location=event.location,
        date=event.date,
        weather_data=event.weather_data,
        score=event.weather_score,
        condition=event.weather_condition
    )

@router.get("/{event_id}/alternatives", response_model=WeatherAlternatives)
async def get_alternative_dates(event_id: str):
    event = event_service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    alternatives = await event_service.get_alternative_dates(event_id)
    if not alternatives:
        raise HTTPException(status_code=400, detail="Could not find alternative dates")
    
    return WeatherAlternatives(
        event_id=event_id,
        original_date=event.date,
        alternatives=alternatives
    ) 
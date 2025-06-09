from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..models import Event, EventCreate, EventUpdate, WeatherResponse, WeatherAlternatives
from ..services.event_service import event_service

router = APIRouter()

@router.post("/", response_model=Event)
async def create_event(event: EventCreate):
    """Create a new event"""
    try:
        return await event_service.create_event(event)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Event])
async def get_events():
    """Get all events"""
    try:
        return await event_service.get_events()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{event_id}", response_model=Event)
async def get_event(event_id: str):
    """Get event by ID"""
    try:
        event = await event_service.get_event(event_id)
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        return event
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{event_id}", response_model=Event)
async def update_event(event_id: str, event: EventUpdate):
    """Update an event"""
    try:
        existing_event = await event_service.get_event(event_id)
        if not existing_event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        # Update only provided fields
        update_data = event.dict(exclude_unset=True)
        updated_event = existing_event.copy(update=update_data)
        updated_event.id = event_id
        
        result = await event_service.update_event(updated_event)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to update event")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{event_id}")
async def delete_event(event_id: str):
    """Delete an event"""
    try:
        success = await event_service.delete_event(event_id)
        if not success:
            raise HTTPException(status_code=404, detail="Event not found")
        return {"message": "Event deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{event_id}/weather-check", response_model=WeatherResponse)
async def check_event_weather(event_id: str):
    event = await event_service.get_event(event_id)
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
    """Get alternative dates for an event"""
    try:
        alternatives = await event_service.get_alternative_dates(event_id)
        if not alternatives:
            raise HTTPException(status_code=404, detail="Event not found or no alternatives available")
        return alternatives
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 
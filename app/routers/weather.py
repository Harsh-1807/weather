from fastapi import APIRouter, HTTPException
from datetime import datetime
from ..models import WeatherResponse, WeatherData, WeatherCondition
from ..services.weather_service import weather_service

router = APIRouter()

@router.get("/{location}/{date}", response_model=WeatherResponse)
async def get_weather(location: str, date: datetime):
    weather_data = await weather_service.get_weather(location, date)
    if not weather_data:
        raise HTTPException(
            status_code=404,
            detail=f"Weather data not found for {location} on {date}"
        )
    
    # Calculate a generic score for the weather
    score = weather_service.calculate_weather_score(weather_data, "other")
    condition = weather_service.get_weather_condition(score)
    
    return WeatherResponse(
        location=location,
        date=date,
        weather_data=weather_data,
        score=score,
        condition=condition
    ) 
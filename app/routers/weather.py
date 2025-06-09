from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import List
from ..models import WeatherResponse, WeatherData, WeatherCondition
from ..services.weather_service import weather_service, WeatherServiceError

router = APIRouter()

@router.get("/{location}/{date}", response_model=WeatherResponse)
async def get_weather(location: str, date: datetime, event_type: str = "other"):
    try:
        weather_data = await weather_service.get_weather(location, date)
        if not weather_data:
            raise HTTPException(
                status_code=404,
                detail=f"Weather data not found for {location} on {date}"
            )
        
        # Calculate score using the provided event type
        score = weather_service.calculate_weather_score(weather_data, event_type)
        condition = weather_service.get_weather_condition(score)
        
        return WeatherResponse(
            location=location,
            date=date,
            weather_data=weather_data,
            score=score,
            condition=condition
        )
    except WeatherServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{location}/forecast", response_model=List[WeatherResponse])
async def get_forecast(location: str, days: int = 5, event_type: str = "other"):
    try:
        forecast_data = await weather_service.get_forecast(location, days)
        if not forecast_data:
            raise HTTPException(
                status_code=404,
                detail=f"Forecast not found for {location}"
            )
        
        responses = []
        for weather_data in forecast_data:
            score = weather_service.calculate_weather_score(weather_data, event_type)
            condition = weather_service.get_weather_condition(score)
            
            responses.append(WeatherResponse(
                location=location,
                date=weather_data.timestamp,
                weather_data=weather_data,
                score=score,
                condition=condition
            ))
        
        return responses
    except WeatherServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{location}/historical/{date}", response_model=WeatherResponse)
async def get_historical_weather(location: str, date: datetime):
    try:
        weather_data = await weather_service.get_historical_weather(location, date)
        if not weather_data:
            raise HTTPException(
                status_code=404,
                detail=f"Historical weather data not found for {location} on {date}"
            )
        
        score = weather_service.calculate_weather_score(weather_data, "other")
        condition = weather_service.get_weather_condition(score)
        
        return WeatherResponse(
            location=location,
            date=date,
            weather_data=weather_data,
            score=score,
            condition=condition
        )
    except WeatherServiceError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") 
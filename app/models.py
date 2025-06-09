from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    OUTDOOR_SPORTS = "outdoor_sports"
    FORMAL_EVENTS = "formal_events"

class WeatherCondition(str, Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNKNOWN = "unknown"

class WeatherData(BaseModel):
    temperature: Optional[float] = None
    precipitation: Optional[float] = None
    wind_speed: Optional[float] = None
    cloud_cover: Optional[float] = None
    description: Optional[str] = None
    timestamp: Optional[datetime] = None

class AirQualityData(BaseModel):
    aqi: Optional[int] = None
    co: Optional[float] = None
    no: Optional[float] = None
    no2: Optional[float] = None
    o3: Optional[float] = None
    so2: Optional[float] = None
    pm2_5: Optional[float] = None
    pm10: Optional[float] = None
    nh3: Optional[float] = None
    timestamp: Optional[datetime] = None

class HistoricalWeatherData(BaseModel):
    """Historical weather data model"""
    date: datetime
    weather_data: WeatherData
    location: str
    timestamp: int
    daily_high: Optional[float] = None
    daily_low: Optional[float] = None
    humidity: Optional[float] = None
    wind_deg: Optional[float] = None
    feels_like: Optional[float] = None

    class Config:
        arbitrary_types_allowed = True

class EventBase(BaseModel):
    name: str
    location: str
    date: datetime
    event_type: EventType
    description: Optional[str] = None
    email: Optional[EmailStr] = None

class EventCreate(BaseModel):
    name: str
    date: datetime
    location: str
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    event_type: EventType

class EventUpdate(BaseModel):
    name: Optional[str] = None
    date: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    event_type: Optional[EventType] = None

class Event(BaseModel):
    id: str
    name: str
    date: datetime
    location: str
    description: Optional[str] = None
    email: Optional[EmailStr] = None
    event_type: EventType
    weather_data: Optional[Dict[str, Any]] = None
    air_quality: Optional[AirQualityData] = None
    historical_weather: Optional[HistoricalWeatherData] = None
    weather_score: Optional[float] = None
    weather_condition: Optional[WeatherCondition] = None
    weather_analysis: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WeatherResponse(BaseModel):
    location: str
    date: datetime
    weather_data: WeatherData
    air_quality: Optional[AirQualityData] = None
    score: float
    condition: WeatherCondition

class AlternativeDate(BaseModel):
    date: datetime
    score: float
    condition: WeatherCondition
    weather_data: Dict[str, Any]
    weather_analysis: Dict[str, Any]

class WeatherAlternatives(BaseModel):
    event_id: str
    original_date: datetime
    original_score: float
    alternatives: List[AlternativeDate] 
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    CRICKET = "cricket"
    WEDDING = "wedding"
    HIKING = "hiking"
    CORPORATE = "corporate"
    OTHER = "other"

class WeatherCondition(str, Enum):
    GOOD = "good"
    OKAY = "okay"
    POOR = "poor"

class WeatherData(BaseModel):
    temperature: float
    precipitation: float
    wind_speed: float
    cloud_cover: float
    description: str
    timestamp: datetime

class EventBase(BaseModel):
    name: str
    location: str
    date: datetime
    event_type: EventType
    description: Optional[str] = None

class EventCreate(EventBase):
    pass

class EventUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    date: Optional[datetime] = None
    event_type: Optional[EventType] = None
    description: Optional[str] = None

class Event(EventBase):
    id: str
    weather_data: Optional[WeatherData] = None
    weather_score: Optional[float] = None
    weather_condition: Optional[WeatherCondition] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class WeatherResponse(BaseModel):
    location: str
    date: datetime
    weather_data: WeatherData
    score: float
    condition: WeatherCondition

class AlternativeDate(BaseModel):
    date: datetime
    weather_data: WeatherData
    score: float
    condition: WeatherCondition

class WeatherAlternatives(BaseModel):
    event_id: str
    original_date: datetime
    alternatives: List[AlternativeDate] 
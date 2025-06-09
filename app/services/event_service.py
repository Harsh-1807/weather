from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
import json
from pathlib import Path
from ..models import Event, EventCreate, EventUpdate, WeatherData, WeatherCondition, AirQualityData, HistoricalWeatherData, EventType, AlternativeDate, WeatherAlternatives
from .weather_service import weather_service
from .notification_service import notification_service
from .weather_analysis import weather_analysis
from ..config import settings
import os
import uuid

# Constants
EVENTS_FILE = Path("events.json")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

class EventService:
    EVENTS_FILE = "events.json"

    def __init__(self):
        """Initialize the event service"""
        self.logger = logging.getLogger(__name__)
        self.events: List[Event] = []
        self.weather_service = weather_service
        self._load_events()

    def _load_events(self) -> None:
        """Load events from the JSON file"""
        try:
            with open(self.EVENTS_FILE, 'r') as f:
                data = json.load(f)
                self.events = []
                for event_data in data:
                    # Convert date string back to datetime
                    if isinstance(event_data.get('date'), str):
                        event_data['date'] = datetime.fromisoformat(event_data['date'])
                    self.events.append(Event(**event_data))
        except FileNotFoundError:
            self.logger.info("No events file found, starting with empty list")
            self.events = []
        except Exception as e:
            self.logger.error(f"Error loading events: {e}")
            self.events = []

    def _save_events(self) -> None:
        """Save events to the JSON file"""
        try:
            # Convert events to list of dictionaries
            events_data = []
            for event in self.events:
                event_dict = event.dict()
                # Convert datetime objects to ISO format strings
                if isinstance(event_dict.get('date'), datetime):
                    event_dict['date'] = event_dict['date'].isoformat()
                if isinstance(event_dict.get('created_at'), datetime):
                    event_dict['created_at'] = event_dict['created_at'].isoformat()
                if isinstance(event_dict.get('updated_at'), datetime):
                    event_dict['updated_at'] = event_dict['updated_at'].isoformat()
                events_data.append(event_dict)
            
            # Save using custom encoder
            with open(self.EVENTS_FILE, 'w') as f:
                json.dump(events_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving events: {e}")
            raise

    def _get_event(self, event_id: str) -> Optional[Event]:
        """Get an event by ID"""
        try:
            return next((event for event in self.events if event.id == event_id), None)
        except Exception as e:
            self.logger.error(f"Error getting event {event_id}: {e}")
            return None

    async def get_events(self) -> List[Event]:
        """Get all events"""
        return self.events

    async def get_event(self, event_id: str) -> Optional[Event]:
        """Get an event by ID with weather data"""
        try:
            event = self._get_event(event_id)
            if event:
                # Get weather data for the event date
                weather_data = await weather_service.get_weather_for_date(event.location, event.date)
                if weather_data:
                    event.weather_data = weather_data
            return event
        except Exception as e:
            self.logger.error(f"Error getting event {event_id}: {e}")
            return None

    async def create_event(self, event: EventCreate) -> Event:
        """Create a new event with weather data."""
        try:
            # Convert date string to datetime if needed
            if isinstance(event.date, str):
                event_date = datetime.fromisoformat(event.date)
            else:
                event_date = event.date

            # Get weather data for the event date
            weather_data = await self.weather_service.get_weather_for_date(
                event.location,
                event_date
            )
            
            logger.info(f"Raw weather data received: {json.dumps(weather_data, indent=2)}")
            
            # Calculate weather score
            weather_analysis_result = weather_analysis.calculate_weather_score(
                weather_data,
                event.event_type
            )
            
            logger.info(f"Weather analysis result: {json.dumps(weather_analysis_result, indent=2)}")
            
            # Create new event with weather data and analysis
            new_event = Event(
                id=str(uuid.uuid4()),
                name=event.name,
                date=event_date,
                location=event.location,
                description=event.description,
                email=event.email,
                event_type=event.event_type,
                weather_data=weather_data,
                weather_score=weather_analysis_result['score'],
                weather_condition=weather_analysis_result['condition'],
                weather_analysis=weather_analysis_result['details']
            )
            
            # Add to events list and save
            self.events.append(new_event)
            self._save_events()
            
            return new_event
            
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            raise

    async def update_event(self, event_id: str, event_update: EventUpdate) -> Optional[Event]:
        """Update an existing event"""
        try:
            event = self._get_event(event_id)
            if not event:
                return None

            # Update event fields
            update_data = event_update.dict(exclude_unset=True)
            for key, value in update_data.items():
                setattr(event, key, value)

            # Update weather data if location or date changed
            if 'location' in update_data or 'date' in update_data:
                weather_data = await weather_service.get_weather_for_date(event.location, event.date)
                if weather_data:
                    event.weather_data = weather_data

            self._save_events()
            return event
        except Exception as e:
            self.logger.error(f"Error updating event {event_id}: {e}")
            return None

    async def delete_event(self, event_id: str) -> bool:
        """Delete an event"""
        try:
            event = self._get_event(event_id)
            if event:
                self.events.remove(event)
                self._save_events()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deleting event {event_id}: {e}")
            return False

    async def get_alternative_dates(self, event_id: str) -> Dict[str, Any]:
        """Get alternative dates with better weather within next 5 days"""
        try:
            event = self._get_event(event_id)
            if not event:
                return {"error": "Event not found"}

            # Get current event's weather score
            current_score = event.weather_score or 0

            # Get best alternative dates from weather service
            alternatives = await weather_service.get_best_alternative_dates(
                event.location,
                event.date,
                event.event_type,
                current_score
            )

            return {
                "event_id": event_id,
                "original_date": event.date.isoformat(),
                "original_score": current_score,
                "original_condition": event.weather_condition,
                "alternatives": alternatives
            }

        except Exception as e:
            self.logger.error(f"Error getting alternative dates: {e}")
            return {"error": str(e)}

    def _calculate_weather_score(self, weather: WeatherData, event_type: str) -> float:
        """Calculate weather score based on event type"""
        try:
            score = 100.0

            # Temperature penalties
            if event_type == "outdoor_sports":
                if weather.temperature > 30:  # Too hot
                    score -= 20
                elif weather.temperature < 15:  # Too cold
                    score -= 20
            else:  # formal_events
                if weather.temperature > 25:  # Too hot
                    score -= 20
                elif weather.temperature < 18:  # Too cold
                    score -= 20

            # Precipitation penalties
            if weather.precipitation > 0:
                score -= 30

            # Wind speed penalties
            if weather.wind_speed > 20:  # Strong wind
                score -= 20
            elif weather.wind_speed > 10:  # Moderate wind
                score -= 10

            # Cloud cover penalties
            if weather.cloud_cover > 80:  # Heavy clouds
                score -= 15
            elif weather.cloud_cover > 50:  # Moderate clouds
                score -= 5

            return max(0, min(100, score))  # Ensure score is between 0 and 100

        except Exception as e:
            logging.error(f"Error calculating weather score: {e}")
            return 0.0

    def _get_weather_condition(self, score: float) -> WeatherCondition:
        """Get weather condition based on score"""
        if score >= 70:
            return WeatherCondition.GOOD
        elif score >= 49:  # 70 * 0.7
            return WeatherCondition.OKAY
        else:
            return WeatherCondition.POOR

    async def get_upcoming_events(self) -> List[Event]:
        """Get all upcoming events"""
        try:
            current_time = datetime.utcnow()
            return [event for event in self.events if event.date > current_time]
        except Exception as e:
            logging.error(f"Error getting upcoming events: {e}")
            return []

    async def get_events_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Event]:
        """Get events within a date range"""
        try:
            return [
                event for event in self.events 
                if start_date <= event.date <= end_date
            ]
        except Exception as e:
            logging.error(f"Error getting events by date range: {e}")
            return []

    async def get_weather_for_event(self, event: Event) -> Optional[WeatherData]:
        """Get weather data for a specific event"""
        try:
            return await weather_service.get_weather_for_date(event.location, event.date)
        except Exception as e:
            logging.error(f"Error getting weather for event: {e}")
            return None

event_service = EventService() 
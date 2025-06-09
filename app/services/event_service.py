from datetime import datetime, timedelta
from typing import List, Optional, Dict
import json
import os
from ..models import Event, EventCreate, EventUpdate, WeatherData, WeatherCondition
from .weather_service import weather_service

class EventService:
    def __init__(self):
        self.events_file = "events.json"
        self.events: Dict[str, Event] = {}
        self._load_events()

    def _load_events(self):
        if os.path.exists(self.events_file):
            try:
                with open(self.events_file, "r") as f:
                    data = json.load(f)
                    for event_id, event_data in data.items():
                        # Convert string dates back to datetime objects
                        for date_field in ["date", "created_at", "updated_at"]:
                            if date_field in event_data:
                                event_data[date_field] = datetime.fromisoformat(event_data[date_field])
                        if event_data.get("weather_data"):
                            event_data["weather_data"]["timestamp"] = datetime.fromisoformat(
                                event_data["weather_data"]["timestamp"]
                            )
                        self.events[event_id] = Event(**event_data)
            except Exception as e:
                print(f"Error loading events: {e}")
                self.events = {}

    def _save_events(self):
        try:
            with open(self.events_file, "w") as f:
                # Convert datetime objects to ISO format strings
                events_data = {}
                for event_id, event in self.events.items():
                    event_dict = event.dict()
                    for date_field in ["date", "created_at", "updated_at"]:
                        if date_field in event_dict:
                            event_dict[date_field] = event_dict[date_field].isoformat()
                    if event_dict.get("weather_data"):
                        event_dict["weather_data"]["timestamp"] = event_dict["weather_data"]["timestamp"].isoformat()
                    events_data[event_id] = event_dict
                json.dump(events_data, f, indent=2)
        except Exception as e:
            print(f"Error saving events: {e}")

    async def create_event(self, event: EventCreate) -> Event:
        event_id = str(len(self.events) + 1)
        new_event = Event(
            id=event_id,
            **event.dict(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Get weather data for the event
        weather_data = await weather_service.get_weather(event.location, event.date)
        if weather_data:
            new_event.weather_data = weather_data
            new_event.weather_score = weather_service.calculate_weather_score(
                weather_data, event.event_type
            )
            new_event.weather_condition = weather_service.get_weather_condition(
                new_event.weather_score
            )

        self.events[event_id] = new_event
        self._save_events()
        return new_event

    def get_event(self, event_id: str) -> Optional[Event]:
        return self.events.get(event_id)

    def get_all_events(self) -> List[Event]:
        return list(self.events.values())

    async def update_event(self, event_id: str, event_update: EventUpdate) -> Optional[Event]:
        if event_id not in self.events:
            return None

        event = self.events[event_id]
        update_data = event_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(event, field, value)
        
        event.updated_at = datetime.utcnow()

        # Update weather data if location or date changed
        if "location" in update_data or "date" in update_data:
            weather_data = await weather_service.get_weather(event.location, event.date)
            if weather_data:
                event.weather_data = weather_data
                event.weather_score = weather_service.calculate_weather_score(
                    weather_data, event.event_type
                )
                event.weather_condition = weather_service.get_weather_condition(
                    event.weather_score
                )

        self._save_events()
        return event

    async def get_alternative_dates(
        self, event_id: str, days_range: int = 7
    ) -> Optional[List[Dict]]:
        event = self.get_event(event_id)
        if not event:
            return None

        alternatives = []
        base_date = event.date
        location = event.location

        for day_offset in range(-days_range, days_range + 1):
            if day_offset == 0:
                continue

            check_date = base_date + timedelta(days=day_offset)
            weather_data = await weather_service.get_weather(location, check_date)
            
            if weather_data:
                score = weather_service.calculate_weather_score(
                    weather_data, event.event_type
                )
                condition = weather_service.get_weather_condition(score)
                
                alternatives.append({
                    "date": check_date,
                    "weather_data": weather_data,
                    "score": score,
                    "condition": condition
                })

        # Sort alternatives by score in descending order
        alternatives.sort(key=lambda x: x["score"], reverse=True)
        return alternatives[:5]  # Return top 5 alternatives

event_service = EventService() 
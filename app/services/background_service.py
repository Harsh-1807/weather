from datetime import datetime, timedelta
import asyncio
import logging
from typing import List, Dict
from ..models import Event, WeatherAnalysis
from .event_service import event_service
from .weather_service import weather_service
from .notification_service import notification_service

logger = logging.getLogger(__name__)

class BackgroundService:
    def __init__(self):
        self.running = False
        self.check_interval = 3600  # Check every hour

    async def start(self):
        """Start the background service"""
        self.running = True
        logger.info("Background service started")
        
        while self.running:
            try:
                await self._check_events()
            except Exception as e:
                logger.error(f"Error in background service: {e}")
            
            await asyncio.sleep(self.check_interval)

    async def stop(self):
        """Stop the background service"""
        self.running = False
        logger.info("Background service stopped")

    async def _check_events(self):
        """Check all events for notifications"""
        try:
            events = await event_service.get_events()
            now = datetime.now()

            for event in events:
                # Skip events without email
                if not event.email:
                    continue

                # Check for weather changes
                if event.weather_data and event.weather_analysis:
                    try:
                        new_weather_data, new_analysis = await event_service.weather_service.get_weather(
                            location=event.location,
                            date=event.date
                        )

                        if new_analysis.overall_score < event.weather_analysis.overall_score - event.weather_change_threshold:
                            await notification_service.send_weather_alert(
                                event=event,
                                old_weather=event.weather_data,
                                new_weather=new_weather_data
                            )
                    except Exception as e:
                        logger.error(f"Error checking weather for event {event.id}: {e}")

                # Check for upcoming event reminders
                days_until_event = (event.date - now).days
                if 0 <= days_until_event <= event.reminder_days_before:
                    await notification_service.send_event_reminder(event)

        except Exception as e:
            logger.error(f"Error checking events: {e}")

background_service = BackgroundService() 
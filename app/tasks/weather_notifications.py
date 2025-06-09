import asyncio
from datetime import datetime, timedelta
import logging
from typing import List
from ..models import Event
from ..services.event_service import event_service
from ..services.notification_service import notification_service
from ..config import settings

logger = logging.getLogger(__name__)

async def check_weather_changes():
    """Background task to check for weather changes and send notifications"""
    while True:
        try:
            # Get all upcoming events
            events = await event_service.get_upcoming_events()
            
            for event in events:
                try:
                    # Check if weather has changed significantly
                    if await notification_service.check_weather_changes(event):
                        # Get current weather
                        current_weather = await event_service.get_weather_for_event(event)
                        if not current_weather:
                            continue

                        # Calculate changes
                        changes = {
                            "temperature_diff": round(
                                current_weather.temperature - event.weather_data.temperature, 1
                            ),
                            "precipitation_diff": round(
                                current_weather.precipitation - event.weather_data.precipitation, 1
                            ),
                            "wind_diff": round(
                                current_weather.wind_speed - event.weather_data.wind_speed, 1
                            )
                        }

                        # Send weather alert
                        await notification_service.send_weather_alert(event, changes)

                        # Update event weather data
                        event.weather_data = current_weather
                        await event_service.update_event(event)

                except Exception as e:
                    logger.error(f"Error processing event {event.id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in weather change check task: {e}")

        # Wait for next check
        await asyncio.sleep(settings.NOTIFICATIONS["check_interval"])

async def send_event_reminders():
    """Background task to send event reminders"""
    while True:
        try:
            # Get events happening in the next 24 hours
            reminder_time = datetime.now() + timedelta(hours=settings.NOTIFICATIONS["reminder_hours_before"])
            events = await event_service.get_events_by_date_range(
                start_date=reminder_time - timedelta(minutes=5),
                end_date=reminder_time + timedelta(minutes=5)
            )

            for event in events:
                try:
                    # Send reminder
                    await notification_service.send_event_reminder(event)
                except Exception as e:
                    logger.error(f"Error sending reminder for event {event.id}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in event reminder task: {e}")

        # Wait for next check
        await asyncio.sleep(300)  # Check every 5 minutes

async def check_weather_thresholds():
    """Check weather conditions for all upcoming events"""
    try:
        # Get all upcoming events
        events = await event_service.get_upcoming_events()
        
        for event in events:
            try:
                # Check for weather changes
                changes = await notification_service.check_weather_changes(event)
                
                if changes:
                    # Send notification if changes are significant
                    await notification_service.send_notification(event, changes)
                    
                    # Update event's weather data
                    current_weather = await event_service.get_weather_for_event(event)
                    if current_weather:
                        event.weather_data = current_weather
                        await event_service.update_event(event.id, event)
                        
            except Exception as e:
                logger.error(f"Error checking thresholds for event {event.id}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Error in weather notification task: {e}")

async def start_notification_tasks():
    """Start all notification background tasks"""
    tasks = [
        asyncio.create_task(check_weather_changes()),
        asyncio.create_task(send_event_reminders()),
        asyncio.create_task(check_weather_thresholds())
    ]
    await asyncio.gather(*tasks) 
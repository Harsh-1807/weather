from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ..models import Event, WeatherData
from .weather_service import weather_service
from .weather_analysis import weather_analysis
from ..config import settings
import aiosmtplib

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.notifications_enabled = bool(settings.SMTP_USERNAME and settings.SMTP_PASSWORD)

    async def check_weather_changes(self, event: Event) -> None:
        """Check for significant weather changes and send notifications"""
        try:
            if not event.email:
                return

            # Get current weather data
            weather_data = await weather_service.get_weather_for_date(event.location, event.date)
            if not weather_data:
                return

            # Calculate new weather score
            weather_analysis_result = weather_analysis.calculate_weather_score(weather_data, event.event_type)
            new_score = weather_analysis_result['score']
            new_condition = weather_analysis_result['condition']

            # Check if there's a significant change
            if event.weather_score is not None:
                score_diff = abs(new_score - event.weather_score)
                if score_diff >= 20 or new_condition != event.weather_condition:
                    # Send notification
                    await self.send_notification(
                        event.email,
                        f"Weather Update for {event.name}",
                        f"Significant weather change detected for your event:\n"
                        f"Previous Score: {event.weather_score}/100 ({event.weather_condition})\n"
                        f"New Score: {new_score}/100 ({new_condition})\n\n"
                        f"Event Details:\n"
                        f"Date: {event.date}\n"
                        f"Location: {event.location}"
                    )

        except Exception as e:
            logger.error(f"Error checking weather changes: {e}")

    async def send_notification(self, email: str, subject: str, message: str) -> bool:
        """Send a notification email"""
        try:
            if not self.notifications_enabled:
                logger.warning("Email notifications are not configured")
                return False

            # Create message
            msg = MIMEMultipart()
            msg['From'] = settings.SMTP_USERNAME
            msg['To'] = email
            msg['Subject'] = subject

            # Add message body
            msg.attach(MIMEText(message, 'plain'))

            # Send email
            async with aiosmtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as smtp:
                await smtp.starttls()
                await smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                await smtp.send_message(msg)

            logger.info(f"Notification sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False
    
    async def send_weather_alert(self, event: Event, changes: Dict) -> bool:
        """Send weather change alert email"""
        if not self.notifications_enabled:
            self.logger.info("Email notifications are disabled - SMTP settings not configured")
            return False
            
        try:
            if not event.email:
                return False

            subject = f"Weather Alert for {event.title}"
            body = self._generate_alert_email(event, changes)

            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USERNAME
            msg["To"] = event.email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

            return True
        except Exception as e:
            self.logger.error(f"Error sending weather alert: {e}")
            return False
    
    async def send_event_reminder(self, event: Event) -> None:
        """Send event reminder with weather information"""
        if not event.email:
            return

        try:
            # Get weather data
            weather = await weather_service.get_weather_for_date(event.location, event.date)
            if not weather:
                return

            # Get hourly breakdown
            hourly_data = await weather_analysis.get_hourly_breakdown(event.location, event)
            
            # Format hourly data
            hourly_text = ""
            if hourly_data:
                hourly_text = "\nHourly Forecast:\n"
                for hour in hourly_data:
                    hourly_text += f"{hour['time']}: {hour['temperature']}°C - {hour['description']} (Score: {hour['score']}/100)\n"

            # Create email content
            subject = f"Weather Update for {event.name}"
            body = f"""
            Event: {event.name}
            Date: {event.date.strftime('%Y-%m-%d %H:%M')}
            Location: {event.location}
            
            Current Weather Forecast:
            Temperature: {weather.temperature}°C
            Description: {weather.description}
            Weather Score: {event.weather_score}/100
            Condition: {event.weather_condition}
            
            {hourly_text}
            
            Stay tuned for any weather changes!
            """

            # Send email
            await self._send_email(event.email, subject, body)

        except Exception as e:
            self.logger.error(f"Error sending event reminder: {e}")

    async def _send_email(self, to_email: str, subject: str, body: str) -> None:
        """Send email using configured SMTP settings"""
        try:
            if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
                self.logger.warning("SMTP settings not configured")
                return

            message = MIMEMultipart()
            message['From'] = settings.SMTP_USERNAME
            message['To'] = to_email
            message['Subject'] = subject

            message.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)

            self.logger.info(f"Email sent to {to_email}")
            
        except Exception as e:
            self.logger.error(f"Error sending email: {e}")
            raise

    async def send_threshold_alert(self, event: Event, threshold_type: str, current_value: float) -> bool:
        """Send custom threshold alert"""
        if not self.notifications_enabled:
            self.logger.info("Email notifications are disabled - SMTP settings not configured")
            return False

        try:
            if not event.email:
                return False

            subject = f"Weather Threshold Alert for {event.title}"
            body = self._generate_threshold_email(event, threshold_type, current_value)

            msg = MIMEMultipart()
            msg["From"] = settings.SMTP_USERNAME
            msg["To"] = event.email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

            return True
        except Exception as e:
            self.logger.error(f"Error sending threshold alert: {e}")
            return False

    def _generate_alert_email(self, event: Event, changes: Dict) -> str:
        """Generate HTML email for weather alert"""
        return f"""
        <html>
            <body>
                <h2>Weather Alert for {event.title}</h2>
                <p>Significant weather changes detected for your event:</p>
                <ul>
                    <li>Temperature change: {changes.get('temperature', {}).get('change', 0)}°C</li>
                    <li>Precipitation change: {changes.get('rain', {}).get('change', 0)}%</li>
                    <li>Wind speed change: {changes.get('wind', {}).get('change', 0)} km/h</li>
                </ul>
                <p>Event Details:</p>
                <ul>
                    <li>Date: {event.date.strftime('%Y-%m-%d %H:%M')}</li>
                    <li>Location: {event.location}</li>
                </ul>
            </body>
        </html>
        """

    def _generate_reminder_email(self, event: Event, weather: WeatherData, 
                               hourly_data: List[Dict], trends: Dict) -> str:
        """Generate HTML email for event reminder"""
        hourly_html = ""
        for hour in hourly_data:
            hourly_html += f"""
            <tr>
                <td>{hour['time']}</td>
                <td>{hour['weather']['temperature']}°C</td>
                <td>{hour['weather']['precipitation']}%</td>
                <td>{hour['weather']['wind_speed']} km/h</td>
                <td>{hour['score']}/100</td>
            </tr>
            """

        return f"""
        <html>
            <body>
                <h2>Weather Summary for {event.title}</h2>
                <p>Event Details:</p>
                <ul>
                    <li>Date: {event.date.strftime('%Y-%m-%d %H:%M')}</li>
                    <li>Location: {event.location}</li>
                </ul>
                
                <h3>Overall Weather</h3>
                <ul>
                    <li>Temperature: {weather.temperature}°C</li>
                    <li>Precipitation: {weather.precipitation}%</li>
                    <li>Wind Speed: {weather.wind_speed} km/h</li>
                    <li>Cloud Cover: {weather.cloud_cover}%</li>
                </ul>

                <h3>Weather Trends</h3>
                <ul>
                    <li>Temperature: {trends['temperature']['trend']}</li>
                    <li>Precipitation: {trends['precipitation']['trend']}</li>
                    <li>Wind: {trends['wind']['trend']}</li>
                </ul>

                <h3>Hourly Breakdown</h3>
                <table border="1">
                    <tr>
                        <th>Time</th>
                        <th>Temperature</th>
                        <th>Precipitation</th>
                        <th>Wind</th>
                        <th>Score</th>
                    </tr>
                    {hourly_html}
                </table>
            </body>
        </html>
        """

    def _generate_threshold_email(self, event: Event, threshold_type: str, 
                                current_value: float) -> str:
        """Generate HTML email for threshold alert"""
        return f"""
        <html>
            <body>
                <h2>Weather Threshold Alert for {event.title}</h2>
                <p>The {threshold_type} has exceeded the threshold:</p>
                <ul>
                    <li>Current value: {current_value}</li>
                </ul>
                <p>Event Details:</p>
                <ul>
                    <li>Date: {event.date.strftime('%Y-%m-%d %H:%M')}</li>
                    <li>Location: {event.location}</li>
                </ul>
            </body>
        </html>
        """

notification_service = NotificationService()
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, List
import logging
from app.config import settings

logger = logging.getLogger(__name__)

class SMTPService:
    def __init__(self):
        self.server = None
        self.is_connected = False
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to SMTP server."""
        try:
            if not settings.EMAIL_ENABLED:
                logger.info("Email notifications are disabled")
                return
                
            if not all([settings.SMTP_SERVER, settings.SMTP_PORT, 
                       settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
                logger.warning("SMTP settings are incomplete")
                return
            
            self.server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            self.server.starttls()
            self.server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            self.is_connected = True
            logger.info("Successfully connected to SMTP server")
        except Exception as e:
            logger.error(f"Failed to connect to SMTP server: {str(e)}")
            self.is_connected = False
    
    def _disconnect(self) -> None:
        """Close SMTP connection."""
        if self.server and self.is_connected:
            try:
                self.server.quit()
                self.is_connected = False
                logger.info("Disconnected from SMTP server")
            except Exception as e:
                logger.error(f"Error disconnecting from SMTP server: {str(e)}")
    
    def send_email(self, 
                  to_email: str, 
                  subject: str, 
                  html_content: str,
                  cc: Optional[List[str]] = None) -> bool:
        """
        Send an email with HTML content.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content of the email
            cc: Optional list of CC recipients
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not settings.EMAIL_ENABLED:
            logger.info("Email notifications are disabled")
            return False
            
        if not self.is_connected:
            logger.warning("Not connected to SMTP server")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.FROM_EMAIL
            msg['To'] = to_email
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            
            self.server.sendmail(settings.FROM_EMAIL, recipients, msg.as_string())
            logger.info(f"Successfully sent email to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_weather_alert(self, 
                          to_email: str,
                          event_name: str,
                          event_date: str,
                          location: str,
                          current_weather: dict,
                          forecast_weather: dict) -> bool:
        """
        Send a weather alert email.
        
        Args:
            to_email: Recipient email address
            event_name: Name of the event
            event_date: Date of the event
            location: Location of the event
            current_weather: Current weather data
            forecast_weather: Forecast weather data
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        subject = f"Weather Alert: {event_name} on {event_date}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2c3e50;">Weather Alert for {event_name}</h2>
                <p><strong>Event Details:</strong></p>
                <ul>
                    <li>Date: {event_date}</li>
                    <li>Location: {location}</li>
                </ul>
                
                <h3 style="color: #2c3e50;">Current Weather</h3>
                <ul>
                    <li>Temperature: {current_weather.get('temperature', 'N/A')}°C</li>
                    <li>Conditions: {current_weather.get('description', 'N/A')}</li>
                    <li>Precipitation: {current_weather.get('precipitation', 'N/A')}%</li>
                    <li>Wind Speed: {current_weather.get('wind_speed', 'N/A')} m/s</li>
                </ul>
                
                <h3 style="color: #2c3e50;">Forecast for Event Day</h3>
                <ul>
                    <li>Temperature: {forecast_weather.get('temperature', 'N/A')}°C</li>
                    <li>Conditions: {forecast_weather.get('description', 'N/A')}</li>
                    <li>Precipitation: {forecast_weather.get('precipitation', 'N/A')}%</li>
                    <li>Wind Speed: {forecast_weather.get('wind_speed', 'N/A')} m/s</li>
                </ul>
                
                <p style="color: #e74c3c; font-weight: bold;">
                    Please check the weather forecast regularly as conditions may change.
                </p>
                
                <p>Best regards,<br>Weather Event Planner</p>
            </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_event_reminder(self,
                          to_email: str,
                          event_name: str,
                          event_date: str,
                          location: str,
                          weather_data: dict) -> bool:
        """
        Send an event reminder email with weather information.
        
        Args:
            to_email: Recipient email address
            event_name: Name of the event
            event_date: Date of the event
            location: Location of the event
            weather_data: Weather data for the event
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        subject = f"Reminder: {event_name} Tomorrow"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2c3e50;">Event Reminder: {event_name}</h2>
                <p>Your event is tomorrow! Here are the details:</p>
                
                <h3 style="color: #2c3e50;">Event Details</h3>
                <ul>
                    <li>Date: {event_date}</li>
                    <li>Location: {location}</li>
                </ul>
                
                <h3 style="color: #2c3e50;">Weather Forecast</h3>
                <ul>
                    <li>Temperature: {weather_data.get('temperature', 'N/A')}°C</li>
                    <li>Conditions: {weather_data.get('description', 'N/A')}</li>
                    <li>Precipitation: {weather_data.get('precipitation', 'N/A')}%</li>
                    <li>Wind Speed: {weather_data.get('wind_speed', 'N/A')} m/s</li>
                </ul>
                
                <p style="color: #27ae60; font-weight: bold;">
                    Don't forget to check the weather forecast before heading out!
                </p>
                
                <p>Best regards,<br>Weather Event Planner</p>
            </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def send_alternative_suggestion(self,
                                  to_email: str,
                                  event_name: str,
                                  original_date: str,
                                  alternative_date: str,
                                  location: str,
                                  weather_data: dict,
                                  score_improvement: float) -> bool:
        """
        Send an alternative date suggestion email.
        
        Args:
            to_email: Recipient email address
            event_name: Name of the event
            original_date: Original event date
            alternative_date: Suggested alternative date
            location: Location of the event
            weather_data: Weather data for the alternative date
            score_improvement: Weather score improvement percentage
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        subject = f"Better Weather Found for {event_name}"
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #2c3e50;">Better Weather Found!</h2>
                <p>We found a better date for your event with improved weather conditions.</p>
                
                <h3 style="color: #2c3e50;">Event Details</h3>
                <ul>
                    <li>Event: {event_name}</li>
                    <li>Original Date: {original_date}</li>
                    <li>Suggested Date: {alternative_date}</li>
                    <li>Location: {location}</li>
                </ul>
                
                <h3 style="color: #2c3e50;">Weather Forecast for Alternative Date</h3>
                <ul>
                    <li>Temperature: {weather_data.get('temperature', 'N/A')}°C</li>
                    <li>Conditions: {weather_data.get('description', 'N/A')}</li>
                    <li>Precipitation: {weather_data.get('precipitation', 'N/A')}%</li>
                    <li>Wind Speed: {weather_data.get('wind_speed', 'N/A')} m/s</li>
                </ul>
                
                <p style="color: #27ae60; font-weight: bold;">
                    Weather Score Improvement: {score_improvement}%
                </p>
                
                <p>Best regards,<br>Weather Event Planner</p>
            </body>
        </html>
        """
        
        return self.send_email(to_email, subject, html_content)
    
    def __del__(self):
        """Cleanup when the service is destroyed."""
        self._disconnect()
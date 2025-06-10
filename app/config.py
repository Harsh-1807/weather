from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional

load_dotenv()

class Settings(BaseSettings):
    # API Keys
    OPENWEATHER_API_KEY: str = "d46c861c593afe826fe8141072c309eb"  # Default API key
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"  # Base URL for OpenWeather API
    SMTP_USERNAME: Optional[str] = "nkharshbachhav@gmail.com"
    SMTP_PASSWORD: Optional[str] = "gkpz rfne hrep uzat"
    FROM_EMAIL: Optional[str] = "nkharshbachhav@gmail.com"
    SMTP_SERVER: Optional[str] = "smtp.gmail.com"
    SMTP_PORT: Optional[int] = 587
    SMTP_USE_TLS: Optional[bool] = True
    SMTP_USE_SSL: Optional[bool] = False
    SMTP_HOST: Optional[str] = "smtp.gmail.com"

    # Cache settings
    CACHE_EXPIRY: int = 3600  # 1 hour in seconds
    CACHE_PREFIX: str = "weather_"

    # Weather score thresholds
    WEATHER_SCORE_THRESHOLD: float = 70.0
    WEATHER_CHANGE_THRESHOLD: float = 20.0

    # Event type requirements
    EVENT_TYPE_REQUIREMENTS: Dict = {
        "outdoor_sports": {
            "temperature": {
                "weight": 0.3,
                "ideal_range": [15, 25],
                "description": "Comfortable temperature for physical activity"
            },
            "precipitation": {
                "weight": 0.3,
                "max": 20,
                "description": "Low chance of rain"
            },
            "wind": {
                "weight": 0.2,
                "max": 20,
                "description": "Moderate wind conditions"
            },
            "cloud_cover": {
                "weight": 0.2,
                "max": 50,
                "description": "Partly cloudy conditions"
            }
        },
        "formal_events": {
            "temperature": {
                "weight": 0.25,
                "ideal_range": [18, 28],
                "description": "Comfortable temperature for formal attire"
            },
            "precipitation": {
                "weight": 0.35,
                "max": 10,
                "description": "Very low chance of rain"
            },
            "wind": {
                "weight": 0.2,
                "max": 15,
                "description": "Light wind conditions"
            },
            "cloud_cover": {
                "weight": 0.2,
                "max": 30,
                "description": "Mostly clear conditions"
            }
        }
    }

    # Notification settings
    NOTIFICATIONS: Dict = {
        "weather_change_threshold": 20.0,  # Percentage change to trigger alert
        "reminder_hours_before": 24,  # Hours before event to send reminder
        "check_interval": 300,  # Check every 5 minutes
        "threshold_alerts": {
            "temperature": {
                "min": 10,
                "max": 35
            },
            "precipitation": {
                "max": 50
            },
            "wind": {
                "max": 30
            }
        }
    }

    # Database URLs
    POSTGRES_URL: str = "postgresql://project_vk7r_user:a7sQJEldVn0SHLy17qIMJyngZgbeLHZe@dpg-d143l0ggjchc73fo9tn0-a.singapore-postgres.render.com/project_vk7r"
    MONGO_URI: str = "mongodb+srv://nkharshbachhav:6vXGGAWOSLpGkXPJ@resume.ooqny.mongodb.net/resume_database?retryWrites=true&w=majority"
    
    # JWT Settings
    SECRET_KEY: str = "your-secret-key-here"  # Change this in production
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Google OAuth Settings
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    
    # Weather API Settings
    WEATHER_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings() 
from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    OPENWEATHER_API_KEY: str = os.getenv("OPENWEATHER_API_KEY", "d46c861c593afe826fe8141072c309eb")
    CACHE_DURATION: int = 21600  # 6 hours in seconds
    WEATHER_SCORE_THRESHOLDS: dict = {
        "good": 80,
        "okay": 60,
        "poor": 40
    }
    EVENT_TYPE_REQUIREMENTS: dict = {
        "cricket": {
            "temperature": {"min": 15, "max": 30},
            "precipitation": {"max": 20},
            "wind": {"max": 20},
            "cloud_cover": {"max": 50}
        },
        "wedding": {
            "temperature": {"min": 18, "max": 28},
            "precipitation": {"max": 10},
            "wind": {"max": 15},
            "cloud_cover": {"max": 30}
        },
        "hiking": {
            "temperature": {"min": 10, "max": 25},
            "precipitation": {"max": 30},
            "wind": {"max": 25},
            "cloud_cover": {"max": 70}
        },
        "other": {
            "temperature": {"min": 15, "max": 30},
            "precipitation": {"max": 30},
            "wind": {"max": 25},
            "cloud_cover": {"max": 70}
        }
    }

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings() 
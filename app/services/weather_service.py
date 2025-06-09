import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from cachetools import TTLCache
from ..config import settings
from ..models import WeatherData, WeatherCondition

class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.cache = TTLCache(maxsize=100, ttl=settings.CACHE_DURATION)

    async def get_weather(self, location: str, date: datetime) -> Optional[WeatherData]:
        cache_key = f"{location}_{date.date()}"
        
        # Check cache first
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Get coordinates for location
        coords = await self._get_coordinates(location)
        if not coords:
            return None

        # Get weather data
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/forecast"
            params = {
                "lat": coords["lat"],
                "lon": coords["lon"],
                "appid": self.api_key,
                "units": "metric"
            }
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    weather_data = self._process_weather_data(data, date)
                    
                    if weather_data:
                        self.cache[cache_key] = weather_data
                    
                    return weather_data
            except Exception as e:
                print(f"Error fetching weather data: {e}")
                return None

    async def _get_coordinates(self, location: str) -> Optional[Dict[str, float]]:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key
            }
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        return None
                    
                    data = await response.json()
                    return {
                        "lat": data["coord"]["lat"],
                        "lon": data["coord"]["lon"]
                    }
            except Exception as e:
                print(f"Error getting coordinates: {e}")
                return None

    def _process_weather_data(self, data: Dict, target_date: datetime) -> Optional[WeatherData]:
        try:
            # Find the forecast closest to the target date
            target_date = target_date.replace(hour=12)  # Use noon for daily forecast
            closest_forecast = min(
                data["list"],
                key=lambda x: abs(datetime.fromtimestamp(x["dt"]) - target_date)
            )

            return WeatherData(
                temperature=closest_forecast["main"]["temp"],
                precipitation=closest_forecast.get("pop", 0) * 100,  # Convert to percentage
                wind_speed=closest_forecast["wind"]["speed"],
                cloud_cover=closest_forecast["clouds"]["all"],
                description=closest_forecast["weather"][0]["description"],
                timestamp=datetime.fromtimestamp(closest_forecast["dt"])
            )
        except Exception as e:
            print(f"Error processing weather data: {e}")
            return None

    def calculate_weather_score(self, weather_data: WeatherData, event_type: str) -> float:
        requirements = settings.EVENT_TYPE_REQUIREMENTS.get(event_type, {})
        score = 0
        max_score = 100

        # Temperature score
        temp_req = requirements.get("temperature", {})
        if temp_req.get("min") <= weather_data.temperature <= temp_req.get("max"):
            score += 30
        else:
            temp_diff = min(
                abs(weather_data.temperature - temp_req.get("min", 0)),
                abs(weather_data.temperature - temp_req.get("max", 0))
            )
            score += max(0, 30 - (temp_diff * 2))

        # Precipitation score
        precip_req = requirements.get("precipitation", {})
        if weather_data.precipitation <= precip_req.get("max", 100):
            score += 25
        else:
            precip_diff = weather_data.precipitation - precip_req.get("max", 100)
            score += max(0, 25 - (precip_diff * 0.5))

        # Wind score
        wind_req = requirements.get("wind", {})
        if weather_data.wind_speed <= wind_req.get("max", 100):
            score += 20
        else:
            wind_diff = weather_data.wind_speed - wind_req.get("max", 100)
            score += max(0, 20 - (wind_diff * 0.4))

        # Cloud cover score
        cloud_req = requirements.get("cloud_cover", {})
        if weather_data.cloud_cover <= cloud_req.get("max", 100):
            score += 25
        else:
            cloud_diff = weather_data.cloud_cover - cloud_req.get("max", 100)
            score += max(0, 25 - (cloud_diff * 0.5))

        return min(score, max_score)

    def get_weather_condition(self, score: float) -> WeatherCondition:
        if score >= settings.WEATHER_SCORE_THRESHOLDS["good"]:
            return WeatherCondition.GOOD
        elif score >= settings.WEATHER_SCORE_THRESHOLDS["okay"]:
            return WeatherCondition.OKAY
        else:
            return WeatherCondition.POOR

weather_service = WeatherService() 
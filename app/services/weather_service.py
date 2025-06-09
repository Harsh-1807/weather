import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple
from cachetools import TTLCache
from ..config import settings
from ..models import WeatherData, WeatherCondition
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WeatherServiceError(Exception):
    """Base exception for weather service errors"""
    pass

class WeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "http://api.openweathermap.org/data/2.5"
        self.cache = TTLCache(maxsize=100, ttl=settings.CACHE_DURATION)
        self.rate_limit = 1000  # Free tier limit
        self.requests_count = 0
        self.last_reset = datetime.utcnow()

    async def get_weather(self, location: str, date: datetime) -> Optional[WeatherData]:
        """Get weather data for a specific location and date"""
        cache_key = f"{location}_{date.date()}"
        
        # Check cache first
        if cache_key in self.cache:
            logger.info(f"Cache hit for {location} on {date.date()}")
            return self.cache[cache_key]

        # Check rate limit
        if not self._check_rate_limit():
            raise WeatherServiceError("API rate limit exceeded. Please try again later.")

        try:
            # Get coordinates for location
            coords = await self._get_coordinates(location)
            if not coords:
                raise WeatherServiceError(f"Location not found: {location}")

            # Get weather data
            weather_data = await self._fetch_weather_data(coords, date)
            if not weather_data:
                raise WeatherServiceError(f"No weather data available for {location} on {date}")

            # Validate weather data
            if not self._validate_weather_data(weather_data):
                raise WeatherServiceError("Invalid weather data received from API")

            self.cache[cache_key] = weather_data
            return weather_data
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error while fetching weather data: {e}")
            raise WeatherServiceError("Failed to fetch weather data. Please try again later.")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise WeatherServiceError("An unexpected error occurred.")

    def _validate_weather_data(self, weather_data: WeatherData) -> bool:
        """Validate weather data has all required fields and reasonable values"""
        try:
            # Check if all required fields are present and have reasonable values
            if weather_data.temperature is None or not -50 <= weather_data.temperature <= 50:
                return False
            if weather_data.precipitation is None or not 0 <= weather_data.precipitation <= 100:
                return False
            if weather_data.wind_speed is None or not 0 <= weather_data.wind_speed <= 200:
                return False
            if weather_data.cloud_cover is None or not 0 <= weather_data.cloud_cover <= 100:
                return False
            if not weather_data.description:
                return False
            return True
        except Exception as e:
            logger.error(f"Error validating weather data: {e}")
            return False

    async def get_forecast(self, location: str, days: int = 5) -> List[WeatherData]:
        """Get weather forecast for the next N days"""
        try:
            coords = await self._get_coordinates(location)
            if not coords:
                raise WeatherServiceError(f"Location not found: {location}")

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/forecast"
                params = {
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "appid": self.api_key,
                    "units": "metric"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise WeatherServiceError(f"Failed to fetch forecast: {response.status}")
                    
                    data = await response.json()
                    forecast_data = self._process_forecast_data(data, days)
                    
                    # Validate forecast data
                    valid_forecasts = [f for f in forecast_data if self._validate_weather_data(f)]
                    if not valid_forecasts:
                        raise WeatherServiceError("No valid forecast data available")
                    
                    return valid_forecasts
        except Exception as e:
            logger.error(f"Error fetching forecast: {e}")
            raise WeatherServiceError("Failed to fetch weather forecast")

    async def get_historical_weather(self, location: str, date: datetime) -> Optional[WeatherData]:
        """Get historical weather data for a specific date"""
        # Note: This is a placeholder. OpenWeatherMap's historical data requires a paid subscription
        # You would need to implement this with a different weather API that provides historical data
        logger.warning("Historical weather data requires a paid subscription")
        return None

    def _check_rate_limit(self) -> bool:
        """Check if we're within the API rate limit"""
        now = datetime.utcnow()
        if (now - self.last_reset).days >= 1:
            self.requests_count = 0
            self.last_reset = now
        
        if self.requests_count >= self.rate_limit:
            return False
        
        self.requests_count += 1
        return True

    async def _get_coordinates(self, location: str) -> Optional[Dict[str, float]]:
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/weather"
            params = {
                "q": location,
                "appid": self.api_key
            }
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 404:
                        logger.warning(f"Location not found: {location}")
                        return None
                    if response.status != 200:
                        logger.error(f"Error getting coordinates: {response.status}")
                        return None
                    
                    data = await response.json()
                    return {
                        "lat": data["coord"]["lat"],
                        "lon": data["coord"]["lon"]
                    }
            except Exception as e:
                logger.error(f"Error getting coordinates: {e}")
                return None

    async def _fetch_weather_data(self, coords: Dict[str, float], date: datetime) -> Optional[WeatherData]:
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
                        logger.error(f"Error fetching weather data: {response.status}")
                        return None
                    
                    data = await response.json()
                    return self._process_weather_data(data, date)
            except Exception as e:
                logger.error(f"Error fetching weather data: {e}")
                return None

    def _process_weather_data(self, data: Dict, target_date: datetime) -> Optional[WeatherData]:
        try:
            # Find the forecast closest to the target date
            target_date = target_date.replace(hour=12)  # Use noon for daily forecast
            closest_forecast = min(
                data["list"],
                key=lambda x: abs(datetime.fromtimestamp(x["dt"]) - target_date)
            )

            # Extract weather data with safe defaults
            main_data = closest_forecast.get("main", {})
            wind_data = closest_forecast.get("wind", {})
            clouds_data = closest_forecast.get("clouds", {})
            weather_desc = closest_forecast.get("weather", [{}])[0]

            return WeatherData(
                temperature=main_data.get("temp"),
                precipitation=closest_forecast.get("pop", 0) * 100,  # Convert to percentage
                wind_speed=wind_data.get("speed"),
                cloud_cover=clouds_data.get("all"),
                description=weather_desc.get("description", "Unknown"),
                timestamp=datetime.fromtimestamp(closest_forecast["dt"])
            )
        except Exception as e:
            logger.error(f"Error processing weather data: {e}")
            return None

    def _process_forecast_data(self, data: Dict, days: int) -> List[WeatherData]:
        """Process forecast data for multiple days"""
        forecast_data = []
        try:
            # Group forecasts by day
            daily_forecasts = {}
            for forecast in data["list"]:
                date = datetime.fromtimestamp(forecast["dt"]).date()
                if date not in daily_forecasts:
                    daily_forecasts[date] = []
                daily_forecasts[date].append(forecast)

            # Process each day's forecast
            for date, forecasts in sorted(daily_forecasts.items())[:days]:
                # Use the forecast closest to noon
                noon_forecast = min(
                    forecasts,
                    key=lambda x: abs(datetime.fromtimestamp(x["dt"]).hour - 12)
                )

                # Extract weather data with safe defaults
                main_data = noon_forecast.get("main", {})
                wind_data = noon_forecast.get("wind", {})
                clouds_data = noon_forecast.get("clouds", {})
                weather_desc = noon_forecast.get("weather", [{}])[0]

                weather_data = WeatherData(
                    temperature=main_data.get("temp"),
                    precipitation=noon_forecast.get("pop", 0) * 100,
                    wind_speed=wind_data.get("speed"),
                    cloud_cover=clouds_data.get("all"),
                    description=weather_desc.get("description", "Unknown"),
                    timestamp=datetime.fromtimestamp(noon_forecast["dt"])
                )
                forecast_data.append(weather_data)

            return forecast_data
        except Exception as e:
            logger.error(f"Error processing forecast data: {e}")
            return []

    def calculate_weather_score(self, weather_data: WeatherData, event_type: str) -> float:
        """Calculate weather suitability score for an event type"""
        if not weather_data or not self._validate_weather_data(weather_data):
            return 0.0

        requirements = settings.EVENT_TYPE_REQUIREMENTS.get(event_type, {})
        if not requirements:
            logger.warning(f"No requirements found for event type: {event_type}")
            return 0.0

        score = 0
        max_score = 100

        # Temperature score (30 points)
        temp_req = requirements.get("temperature", {})
        if weather_data.temperature is not None:
            if temp_req.get("min") is not None and temp_req.get("max") is not None:
                if temp_req["min"] <= weather_data.temperature <= temp_req["max"]:
                    score += 30  # Perfect temperature
                else:
                    # Calculate score based on how far from ideal range
                    temp_diff = min(
                        abs(weather_data.temperature - temp_req.get("min", 0)),
                        abs(weather_data.temperature - temp_req.get("max", 0))
                    )
                    score += max(0, 30 - (temp_diff * 2))

        # Precipitation score (25 points)
        precip_req = requirements.get("precipitation", {})
        if weather_data.precipitation is not None:
            if precip_req.get("max") is not None:
                if weather_data.precipitation <= precip_req["max"]:
                    score += 25  # Acceptable precipitation
                else:
                    # Reduce score based on excess precipitation
                    precip_diff = weather_data.precipitation - precip_req["max"]
                    score += max(0, 25 - (precip_diff * 0.5))

        # Wind score (20 points)
        wind_req = requirements.get("wind", {})
        if weather_data.wind_speed is not None:
            if wind_req.get("max") is not None:
                if weather_data.wind_speed <= wind_req["max"]:
                    score += 20  # Acceptable wind
                else:
                    # Reduce score based on excess wind
                    wind_diff = weather_data.wind_speed - wind_req["max"]
                    score += max(0, 20 - (wind_diff * 0.4))

        # Cloud cover score (25 points)
        cloud_req = requirements.get("cloud_cover", {})
        if weather_data.cloud_cover is not None:
            if cloud_req.get("max") is not None:
                if weather_data.cloud_cover <= cloud_req["max"]:
                    score += 25  # Acceptable cloud cover
                else:
                    # Reduce score based on excess cloud cover
                    cloud_diff = weather_data.cloud_cover - cloud_req["max"]
                    score += max(0, 25 - (cloud_diff * 0.5))

        return min(score, max_score)

    def get_weather_condition(self, score: float) -> WeatherCondition:
        """Determine weather condition based on score"""
        if score >= settings.WEATHER_SCORE_THRESHOLDS["good"]:
            return WeatherCondition.GOOD
        elif score >= settings.WEATHER_SCORE_THRESHOLDS["okay"]:
            return WeatherCondition.OKAY
        else:
            return WeatherCondition.POOR

weather_service = WeatherService() 
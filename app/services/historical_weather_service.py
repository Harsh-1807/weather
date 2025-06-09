from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import aiohttp
import logging
from cachetools import TTLCache
import asyncio
from ..config import settings
from ..models import WeatherData, WeatherTrend

logger = logging.getLogger(__name__)

class HistoricalWeatherService:
    def __init__(self):
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = settings.HISTORICAL_WEATHER["api_url"]
        # Initialize TTL cache with 1 hour expiration
        self.cache = TTLCache(
            maxsize=1000,
            ttl=3600  # 1 hour in seconds
        )
        self.rate_limit = {
            "requests": 0,
            "last_reset": datetime.now(),
            "requests_per_minute": settings.API_RATE_LIMIT["requests_per_minute"],
            "requests_per_day": settings.API_RATE_LIMIT["requests_per_day"]
        }
        self._rate_limit_lock = asyncio.Lock()

    async def get_historical_weather(
        self, 
        location: str, 
        date: datetime,
        days_to_compare: int = None,
        include_hourly: bool = True
    ) -> Tuple[List[WeatherData], WeatherTrend]:
        """Get historical weather data and analyze trends"""
        if days_to_compare is None:
            days_to_compare = settings.HISTORICAL_WEATHER["days_to_compare"]

        try:
            # Get coordinates for location
            coords = await self._get_coordinates(location)
            if not coords:
                raise ValueError(f"Location not found: {location}")

            # Get historical data for the past week
            historical_data = []
            for i in range(days_to_compare):
                check_date = date - timedelta(days=i+1)
                if include_hourly:
                    # Get hourly data for each day
                    hourly_data = await self._fetch_hourly_historical_weather(coords, check_date)
                    if hourly_data:
                        historical_data.extend(hourly_data)
                else:
                    # Get daily average
                    daily_data = await self._fetch_historical_weather(coords, check_date)
                    if daily_data:
                        historical_data.append(daily_data)

            # Analyze trends with enhanced metrics
            trend = self._analyze_trends(historical_data, date)

            return historical_data, trend

        except Exception as e:
            logger.error(f"Error getting historical weather: {e}")
            raise

    async def _check_rate_limit(self) -> bool:
        """Check and update rate limit status"""
        async with self._rate_limit_lock:
            now = datetime.now()
            
            # Reset daily counter if it's a new day
            if (now - self.rate_limit["last_reset"]).days >= 1:
                self.rate_limit["requests"] = 0
                self.rate_limit["last_reset"] = now
            
            # Check daily limit
            if self.rate_limit["requests"] >= self.rate_limit["requests_per_day"]:
                logger.warning("Daily API rate limit exceeded")
                return False
            
            # Check minute limit
            if (now - self.rate_limit["last_reset"]).seconds < 60:
                if self.rate_limit["requests"] >= self.rate_limit["requests_per_minute"]:
                    logger.warning("Minute API rate limit exceeded")
                    return False
            
            self.rate_limit["requests"] += 1
            return True

    async def _get_coordinates(self, location: str) -> Optional[Dict[str, float]]:
        """Get coordinates for a location"""
        cache_key = f"coords_{location}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        async with aiohttp.ClientSession() as session:
            url = f"http://api.openweathermap.org/geo/1.0/direct"
            params = {
                "q": location,
                "limit": 1,
                "appid": self.api_key
            }
            
            try:
                if not await self._check_rate_limit():
                    raise Exception("Rate limit exceeded")

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data:
                            coords = {
                                "lat": data[0]["lat"],
                                "lon": data[0]["lon"],
                                "name": data[0]["name"],
                                "country": data[0]["country"],
                                "id": data[0]["id"]
                            }
                            self.cache[cache_key] = coords
                            return coords
                    return None
            except Exception as e:
                logger.error(f"Error getting coordinates: {e}")
                return None

    async def _fetch_hourly_historical_weather(
        self, 
        coords: Dict[str, float], 
        date: datetime
    ) -> List[WeatherData]:
        """Fetch hourly historical weather data"""
        hourly_data = []
        for hour in range(0, 24, 3):  # Get data every 3 hours
            check_time = date.replace(hour=hour)
            weather_data = await self._fetch_historical_weather(coords, check_time)
            if weather_data:
                hourly_data.append(weather_data)
        return hourly_data

    async def _fetch_historical_weather(
        self, 
        coords: Dict[str, float], 
        date: datetime
    ) -> Optional[WeatherData]:
        """Fetch historical weather data from OpenWeatherMap API"""
        cache_key = f"{coords['id']}_{date.strftime('%Y-%m-%d_%H')}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        if not await self._check_rate_limit():
            raise Exception("Rate limit exceeded")

        async with aiohttp.ClientSession() as session:
            url = self.base_url
            params = {
                "id": coords["id"],
                "type": "hour",
                "appid": self.api_key,
                "start": int(date.timestamp()),
                "end": int((date + timedelta(hours=1)).timestamp())
            }
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "list" in data and data["list"]:
                            weather_data = self._process_historical_data(data["list"][0], coords)
                            self.cache[cache_key] = weather_data
                            return weather_data
                    elif response.status == 429:  # Too Many Requests
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limit hit, waiting {retry_after} seconds")
                        await asyncio.sleep(retry_after)
                        return await self._fetch_historical_weather(coords, date)
                    return None
            except Exception as e:
                logger.error(f"Error fetching historical weather: {e}")
                return None

    def _process_historical_data(self, data: Dict, coords: Dict[str, float]) -> WeatherData:
        """Process historical weather data from API response"""
        main_data = data.get("main", {})
        wind_data = data.get("wind", {})
        weather_desc = data.get("weather", [{}])[0]
        rain_data = data.get("rain", {})
        clouds_data = data.get("clouds", {})
        
        return WeatherData(
            temperature=main_data.get("temp"),
            humidity=main_data.get("humidity"),
            wind_speed=wind_data.get("speed"),
            precipitation=rain_data.get("1h", 0),
            precipitation_probability=data.get("pop", 0),
            wind_direction=self._get_wind_direction(wind_data.get("deg", 0)),
            description=weather_desc.get("description", "Unknown"),
            timestamp=datetime.fromtimestamp(data["dt"]),
            uv_index=data.get("uvi", 0),
            air_quality=data.get("aqi", 1),
            location_name=coords["name"],
            country=coords["country"],
            cloud_cover=clouds_data.get("all", 0),
            pressure=main_data.get("pressure", 0),
            visibility=data.get("visibility", 0)
        )

    def _get_wind_direction(self, degrees: float) -> str:
        """Convert wind degrees to cardinal direction"""
        directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
                     "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        index = round(degrees / 22.5) % 16
        return directions[index]

    def _analyze_trends(
        self, 
        historical_data: List[WeatherData],
        target_date: datetime
    ) -> WeatherTrend:
        """Analyze weather trends with enhanced metrics"""
        if not historical_data:
            return WeatherTrend(
                temperature_trend="stable",
                precipitation_trend="stable",
                wind_trend="stable",
                confidence="low"
            )

        # Calculate trends for each metric
        temp_trend = self._calculate_trend(
            [d.temperature for d in historical_data if d.temperature is not None]
        )
        precip_trend = self._calculate_trend(
            [d.precipitation for d in historical_data if d.precipitation is not None]
        )
        wind_trend = self._calculate_trend(
            [d.wind_speed for d in historical_data if d.wind_speed is not None]
        )

        # Calculate additional metrics
        humidity_trend = self._calculate_trend(
            [d.humidity for d in historical_data if d.humidity is not None]
        )
        pressure_trend = self._calculate_trend(
            [d.pressure for d in historical_data if d.pressure is not None]
        )
        visibility_trend = self._calculate_trend(
            [d.visibility for d in historical_data if d.visibility is not None]
        )

        # Calculate confidence based on data points and consistency
        confidence = self._calculate_confidence(historical_data)

        return WeatherTrend(
            temperature_trend=temp_trend,
            precipitation_trend=precip_trend,
            wind_trend=wind_trend,
            confidence=confidence
        )

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a list of values"""
        if not values or len(values) < 2:
            return "stable"

        # Calculate average change
        changes = [values[i] - values[i-1] for i in range(1, len(values))]
        avg_change = sum(changes) / len(changes)

        # Calculate standard deviation of changes
        std_dev = (sum((x - avg_change) ** 2 for x in changes) / len(changes)) ** 0.5

        # Determine trend based on average change and consistency
        threshold = settings.HISTORICAL_WEATHER["trend_threshold"]
        if std_dev > threshold * 2:  # High variability
            return "variable"
        elif avg_change > threshold:
            return "increasing"
        elif avg_change < -threshold:
            return "decreasing"
        else:
            return "stable"

    def _calculate_confidence(self, data: List[WeatherData]) -> str:
        """Calculate confidence level based on data quality and quantity"""
        if not data:
            return "low"

        # Check data quantity
        if len(data) >= 24:  # Full day of hourly data
            quantity_score = 1.0
        elif len(data) >= 8:  # 8 data points
            quantity_score = 0.8
        elif len(data) >= 4:  # 4 data points
            quantity_score = 0.6
        else:
            quantity_score = 0.4

        # Check data completeness
        complete_fields = 0
        total_fields = 0
        for record in data:
            for field in record.__dict__:
                if getattr(record, field) is not None:
                    complete_fields += 1
                total_fields += 1

        completeness_score = complete_fields / total_fields if total_fields > 0 else 0

        # Calculate final confidence
        final_score = (quantity_score + completeness_score) / 2
        if final_score >= 0.8:
            return "high"
        elif final_score >= 0.6:
            return "medium"
        else:
            return "low"

historical_weather_service = HistoricalWeatherService() 
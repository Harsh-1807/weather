import aiohttp
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from cachetools import TTLCache
from ..config import settings
from ..models import WeatherData, WeatherCondition, AirQualityData, HistoricalWeatherData
from .weather_analysis import WeatherAnalysis
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create weather analysis instance
weather_analysis = WeatherAnalysis()

class WeatherServiceError(Exception):
    """Base exception for weather service errors"""
    pass

class WeatherService:
    def __init__(self):
        """Initialize the weather service with API key and cache"""
        self.api_key = settings.OPENWEATHER_API_KEY
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.geo_url = "http://api.openweathermap.org/geo/1.0"
        self.air_pollution_url = "http://api.openweathermap.org/data/2.5/air_pollution"
        self.history_url = "http://api.openweathermap.org/data/3.0/onecall/timemachine"
        self.cache = {}
        self.rate_limit = 50000  # Student API limit
        self.requests_count = 0
        self.last_reset = datetime.utcnow()
        self.logger = logging.getLogger(__name__)
        
    async def get_current_weather(self, location: str) -> Optional[WeatherData]:
        """Get current weather data for a location"""
        cache_key = f"current_{location}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        try:
            coords = await self._get_coordinates(location)
            if not coords:
                raise WeatherServiceError(f"Location not found: {location}")

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/weather"
                params = {
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "appid": self.api_key,
                    "units": "metric"
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise WeatherServiceError(f"Failed to fetch current weather: {response.status}")
                    
                    data = await response.json()
                    weather_data = self._process_current_weather(data)
            self.cache[cache_key] = weather_data
            return weather_data
        except Exception as e:
            logger.error(f"Error fetching current weather: {e}")
            raise WeatherServiceError("Failed to fetch current weather")

    async def get_hourly_forecast(self, location: str, date: datetime) -> List[Dict]:
        """Get hourly forecast data for a specific date and surrounding dates"""
        try:
            # Get coordinates
            coords = await self._get_coordinates(location)
            if not coords:
                logger.error(f"Could not get coordinates for {location}")
                return []

            # Get forecast data
            params = {
                'lat': coords['lat'],
                'lon': coords['lon'],
                'appid': settings.OPENWEATHER_API_KEY,
                'units': 'metric'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{settings.OPENWEATHER_BASE_URL}/forecast", params=params) as response:
                    if response.status != 200:
                        logger.error(f"Error getting forecast: {response.status}")
                        return []

                    data = await response.json()
                    if not data or 'list' not in data:
                        logger.error("Invalid forecast data received")
                        return []

                    # Get all forecast entries (5 days of 3-hour data)
                    forecast_list = []
                    for item in data['list']:
                        try:
                            forecast_date = datetime.fromtimestamp(item['dt']).date()
                            # Include data for 3 days before and after the event date
                            if abs((forecast_date - date.date()).days) <= 3:
                                forecast_list.append(item)
                        except Exception as e:
                            logger.error(f"Error processing forecast item: {e}")
                            continue

                    logger.info(f"Found {len(forecast_list)} forecast entries around {date.date()}")
                    return forecast_list

        except Exception as e:
            logger.error(f"Error getting hourly forecast: {e}")
            return []

    async def get_daily_forecast(self, location: str, days: int = 16) -> List[WeatherData]:
        """Get daily forecast for the next 16 days"""
        try:
            coords = await self._get_coordinates(location)
            if not coords:
                raise WeatherServiceError(f"Location not found: {location}")

            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/forecast/daily"
                params = {
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "appid": self.api_key,
                    "units": "metric",
                    "cnt": days
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise WeatherServiceError(f"Failed to fetch daily forecast: {response.status}")
                    
                    data = await response.json()
                    return self._process_daily_forecast(data)
        except Exception as e:
            logger.error(f"Error fetching daily forecast: {e}")
            raise WeatherServiceError("Failed to fetch daily forecast")

    async def get_air_quality(self, location: str) -> Optional[AirQualityData]:
        """Get current air quality data"""
        try:
            coords = await self._get_coordinates(location)
            if not coords:
                raise WeatherServiceError(f"Location not found: {location}")

            async with aiohttp.ClientSession() as session:
                url = self.air_pollution_url
                params = {
                    "lat": coords["lat"],
                    "lon": coords["lon"],
                    "appid": self.api_key
                }
                
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        raise WeatherServiceError(f"Failed to fetch air quality: {response.status}")
                    
                    data = await response.json()
                    return self._process_air_quality(data)
        except Exception as e:
            logger.error(f"Error fetching air quality: {e}")
            raise WeatherServiceError("Failed to fetch air quality")

    async def get_historical_weather(self, location: str, date: datetime) -> Optional[HistoricalWeatherData]:
        """Get historical weather data for a specific date"""
        try:
            # Get coordinates for the location
            coords = await self._get_coordinates(location)
            if not coords:
                return None

            # Calculate timestamp for the date
            timestamp = int(date.timestamp())

            # Check cache first
            cache_key = f"historical_{coords['lat']}_{coords['lon']}_{timestamp}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # Make API request
            params = {
                "lat": coords["lat"],
                "lon": coords["lon"],
                "dt": timestamp,
                "appid": self.api_key,
                "units": "metric"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.history_url}", params=params) as response:
                    if response.status == 401:
                        self.logger.warning("Historical weather data not available (401 Unauthorized). Using current weather as fallback.")
                        current_weather = await self.get_current_weather(location)
                        if current_weather:
                            return HistoricalWeatherData(
                                date=date,
                                weather_data=current_weather,
                                location=location,
                                timestamp=timestamp
                            )
                        return None

                    if response.status != 200:
                        self.logger.error(f"Error fetching historical weather: {response.status}")
                        return None

                    data = await response.json()
                    current = data["current"]
                    
                    # Extract weather data
                    weather_data = WeatherData(
                        temperature=current["temp"],
                        precipitation=current.get("rain", {}).get("1h", 0),
                        wind_speed=current["wind_speed"],
                        cloud_cover=current["clouds"],
                        description=current["weather"][0]["description"],
                        icon=current["weather"][0]["icon"]
                    )

                    historical_data = HistoricalWeatherData(
                        date=date,
                        weather_data=weather_data,
                        location=location,
                        timestamp=timestamp,
                        daily_high=current.get("temp_max"),
                        daily_low=current.get("temp_min"),
                        humidity=current.get("humidity"),
                        wind_deg=current.get("wind_deg"),
                        feels_like=current.get("feels_like")
                    )

                    # Cache the result
                    self.cache[cache_key] = historical_data
                    return historical_data

        except Exception as e:
            self.logger.error(f"Error getting historical weather: {e}")
        return None

    def _process_current_weather(self, data: Dict) -> WeatherData:
        """Process current weather data"""
        main_data = data.get("main", {})
        wind_data = data.get("wind", {})
        clouds_data = data.get("clouds", {})
        weather_desc = data.get("weather", [{}])[0]

        return WeatherData(
            temperature=main_data.get("temp"),
            precipitation=data.get("rain", {}).get("1h", 0),
            wind_speed=wind_data.get("speed"),
            cloud_cover=clouds_data.get("all"),
            description=weather_desc.get("description", "Unknown"),
            timestamp=datetime.fromtimestamp(data["dt"])
        )

    def _process_hourly_forecast(self, data: Dict, hours: int) -> List[WeatherData]:
        """Process hourly forecast data"""
        forecast_data = []
        for forecast in data["list"][:hours//3]:  # API returns 3-hour intervals
            main_data = forecast.get("main", {})
            wind_data = forecast.get("wind", {})
            clouds_data = forecast.get("clouds", {})
            weather_desc = forecast.get("weather", [{}])[0]

            weather_data = WeatherData(
                temperature=main_data.get("temp"),
                precipitation=forecast.get("pop", 0) * 100,
                wind_speed=wind_data.get("speed"),
                cloud_cover=clouds_data.get("all"),
                description=weather_desc.get("description", "Unknown"),
                timestamp=datetime.fromtimestamp(forecast["dt"])
            )
            forecast_data.append(weather_data)

        return forecast_data

    def _process_daily_forecast(self, data: Dict) -> List[WeatherData]:
        """Process daily forecast data"""
        forecast_data = []
        for forecast in data["list"]:
            temp_data = forecast.get("temp", {})
            weather_desc = forecast.get("weather", [{}])[0]

            weather_data = WeatherData(
                temperature=temp_data.get("day"),
                precipitation=forecast.get("pop", 0) * 100,
                wind_speed=forecast.get("speed"),
                cloud_cover=forecast.get("clouds"),
                description=weather_desc.get("description", "Unknown"),
                timestamp=datetime.fromtimestamp(forecast["dt"])
            )
            forecast_data.append(weather_data)

        return forecast_data

    def _process_air_quality(self, data: Dict) -> AirQualityData:
        """Process air quality data"""
        components = data["list"][0]["components"]
        aqi = data["list"][0]["main"]["aqi"]

        return AirQualityData(
            aqi=aqi,
            co=components.get("co"),
            no=components.get("no"),
            no2=components.get("no2"),
            o3=components.get("o3"),
            so2=components.get("so2"),
            pm2_5=components.get("pm2_5"),
            pm10=components.get("pm10"),
            nh3=components.get("nh3"),
            timestamp=datetime.fromtimestamp(data["list"][0]["dt"])
        )

    def _process_historical_weather(self, data: Dict) -> HistoricalWeatherData:
        """Process historical weather data"""
        current = data.get("current", {})
        daily = data.get("daily", [{}])[0]

        return HistoricalWeatherData(
            temperature=current.get("temp"),
            feels_like=current.get("feels_like"),
            humidity=current.get("humidity"),
            wind_speed=current.get("wind_speed"),
            wind_deg=current.get("wind_deg"),
            clouds=current.get("clouds"),
            precipitation=current.get("rain", {}).get("1h", 0),
            description=current.get("weather", [{}])[0].get("description"),
            daily_high=daily.get("temp", {}).get("max"),
            daily_low=daily.get("temp", {}).get("min"),
            timestamp=datetime.fromtimestamp(current["dt"])
        )

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
        """Get coordinates for a location"""
        try:
            # Add country code for better accuracy
            search_query = f"{location}, India"
            params = {
                'q': search_query,
                'limit': 1,
                'appid': settings.OPENWEATHER_API_KEY
            }

            logger.info(f"Geocoding location: {search_query}")
            
            async with aiohttp.ClientSession() as session:
                async with session.get("http://api.openweathermap.org/geo/1.0/direct", params=params) as response:
                    if response.status != 200:
                        logger.error(f"Error getting coordinates: {response.status}")
                        return None
                    
                    data = await response.json()
                    logger.info(f"Geocoding response: {json.dumps(data, indent=2)}")
                    
                    if not data:
                        logger.error(f"No coordinates found for {location}")
                        return None

                    # Get the first result
                    result = data[0]
                    coords = {
                        'lat': result['lat'],
                        'lon': result['lon']
                    }
                    logger.info(f"Found coordinates for {location}: {coords}")
                    return coords

        except Exception as e:
            logger.error(f"Error getting coordinates for {location}: {e}")
            return None

    async def get_best_alternative_dates(self, location: str, event_date: datetime, event_type: str, current_score: float) -> List[Dict]:
        """Find the best 5 alternative dates within the next 5 days based on weather conditions"""
        try:
            # Get coordinates for the location
            coords = await self._get_coordinates(location)
            if not coords:
                logger.error(f"Could not get coordinates for location: {location}")
                return []

            logger.info(f"Getting forecast for {location} at coordinates: {coords}")
            logger.info(f"Current event score: {current_score}")

            # Get forecast data
            params = {
                "lat": coords["lat"],
                "lon": coords["lon"],
                "appid": self.api_key,
                "units": "metric"
            }
            
            url = f"{self.base_url}/forecast"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Error getting forecast: {response.status}")
                        return []
                    
                    data = await response.json()
                    if not data or 'list' not in data:
                        logger.error(f"Invalid forecast data received for {location}")
                        return []

                    # Process each forecast entry
                    alternatives = []
                    seen_dates = set()  # Track unique dates

                    for entry in data['list']:
                        try:
                            forecast_date = datetime.fromtimestamp(entry['dt'])
                            forecast_date_str = forecast_date.strftime('%Y-%m-%d')
                            
                            # Skip if date is more than 5 days away
                            if (forecast_date - event_date).days > 5:
                                continue
                                
                            # Skip if date is before current date
                            if forecast_date < event_date:
                                continue

                            # Skip the original event date
                            if forecast_date.date() == event_date.date():
                                continue

                            # Skip if we've already seen this date
                            if forecast_date_str in seen_dates:
                                continue

                            # Calculate weather score for this forecast
                            score_result = weather_analysis.calculate_weather_score(entry, event_type)
                            logger.info(f"Date: {forecast_date}, Score: {score_result['score']}, Current: {current_score}")
                            
                            # Add to alternatives and mark date as seen
                            alternatives.append({
                                'date': forecast_date.isoformat(),
                                'score': score_result['score'],
                                'condition': score_result['condition'],
                                'weather_data': entry,
                                'weather_analysis': score_result['details']
                            })
                            seen_dates.add(forecast_date_str)

                        except Exception as e:
                            logger.error(f"Error processing forecast entry for {location}: {e}")
                            continue

                    # Sort alternatives by score and take top 5
                    alternatives.sort(key=lambda x: x['score'], reverse=True)
                    logger.info(f"Found {len(alternatives)} unique date alternatives for {location}")
                    
                    return alternatives[:5]

        except Exception as e:
            logger.error(f"Error finding alternative dates for {location}: {e}")
            return []

    async def get_weather_for_date(self, location: str, date: datetime) -> Optional[Dict]:
        """Get weather data for a specific date and location"""
        try:
            # Get coordinates for the location
            coords = await self._get_coordinates(location)
            if not coords:
                logger.error(f"Could not get coordinates for location: {location}")
                return None

            lat, lon = coords["lat"], coords["lon"]
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }

            # If date is in the future, use forecast API
            if date > datetime.now():
                url = f"{self.base_url}/forecast"
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            logger.info("OpenWeatherMap API Response:")
                            logger.info(json.dumps(data, indent=2))
                            
                            # Find the closest forecast to the target date
                            closest_forecast = min(
                                data["list"],
                                key=lambda x: abs(
                                    datetime.fromtimestamp(x["dt"]) - date
                                )
                            )
                            logger.info("Selected closest forecast:")
                            logger.info(json.dumps(closest_forecast, indent=2))
                            
                            return closest_forecast  # Return the raw forecast data
                        else:
                            logger.error(f"Error getting forecast: {response.status}")
                            return None
            else:
                # For past dates, use historical data
                historical = await self.get_historical_weather(location, date)
                return historical.weather_data if historical else None

        except Exception as e:
            logger.error(f"Error getting weather for date: {e}")
            return None

weather_service = WeatherService() 
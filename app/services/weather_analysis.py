from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import logging
from ..models import WeatherData, Event, WeatherCondition
import json

logger = logging.getLogger(__name__)

class WeatherAnalysis:
    # Weather condition thresholds
    TEMP_THRESHOLDS = {
        'outdoor_sports': {
            'optimal': (18, 25),  # (min, max) in Celsius
            'acceptable': (15, 30),
            'weight': 0.25
        },
        'formal_events': {
            'optimal': (20, 24),
            'acceptable': (18, 26),
            'weight': 0.25
        }
    }

    WIND_THRESHOLDS = {
        'outdoor_sports': {
            'optimal': (0, 15),  # (min, max) in m/s
            'acceptable': (0, 20),
            'weight': 0.15
        },
        'formal_events': {
            'optimal': (0, 10),
            'acceptable': (0, 15),
            'weight': 0.15
        }
    }

    RAIN_THRESHOLDS = {
        'outdoor_sports': {
            'optimal': 0,  # mm in 3h
            'acceptable': 0.5,
            'weight': 0.25
        },
        'formal_events': {
            'optimal': 0,
            'acceptable': 1.0,
            'weight': 0.25
        }
    }

    CLOUD_THRESHOLDS = {
        'outdoor_sports': {
            'optimal': (0, 30),  # (min, max) in percentage
            'acceptable': (0, 50),
            'weight': 0.1
        },
        'formal_events': {
            'optimal': (0, 40),
            'acceptable': (0, 60),
            'weight': 0.1
        }
    }

    VISIBILITY_THRESHOLDS = {
        'outdoor_sports': {
            'optimal': 8000,  # meters
            'acceptable': 5000,
            'weight': 0.15
        },
        'formal_events': {
            'optimal': 8000,
            'acceptable': 5000,
            'weight': 0.15
        }
    }

    def calculate_weather_score(self, weather_data: Dict[str, Any], event_type: str) -> Dict[str, Any]:
        """Calculate weather score based on event type and weather conditions"""
        try:
            if not weather_data:
                return {
                    'score': 0,
                    'condition': 'unknown',
                    'details': 'No weather data available'
                }

            # Extract weather parameters
            main = weather_data.get('main', {})
            wind = weather_data.get('wind', {})
            rain = weather_data.get('rain', {})
            clouds = weather_data.get('clouds', {})
            
            # Calculate individual scores
            temp_score = self._calculate_temperature_score(
                main.get('temp'),
                event_type
            )
            
            wind_score = self._calculate_wind_score(
                wind.get('speed'),
                event_type
            )
            
            rain_score = self._calculate_rain_score(
                rain.get('3h', 0),
                event_type
            )
            
            cloud_score = self._calculate_cloud_score(
                clouds.get('all'),
                event_type
            )
            
            visibility_score = self._calculate_visibility_score(
                weather_data.get('visibility'),
                event_type
            )

            # Calculate weighted total score
            total_score = (
                temp_score * self.TEMP_THRESHOLDS[event_type]['weight'] +
                wind_score * self.WIND_THRESHOLDS[event_type]['weight'] +
                rain_score * self.RAIN_THRESHOLDS[event_type]['weight'] +
                cloud_score * self.CLOUD_THRESHOLDS[event_type]['weight'] +
                visibility_score * self.VISIBILITY_THRESHOLDS[event_type]['weight']
            )

            # Determine weather condition
            condition = self._get_weather_condition(total_score)

            return {
                'score': round(total_score, 1),
                'condition': condition,
                'details': {
                    'temperature': {
                        'score': round(temp_score, 1),
                        'value': main.get('temp'),
                        'weight': self.TEMP_THRESHOLDS[event_type]['weight']
                    },
                    'wind': {
                        'score': round(wind_score, 1),
                        'value': wind.get('speed'),
                        'weight': self.WIND_THRESHOLDS[event_type]['weight']
                    },
                    'rain': {
                        'score': round(rain_score, 1),
                        'value': rain.get('3h', 0),
                        'weight': self.RAIN_THRESHOLDS[event_type]['weight']
                    },
                    'clouds': {
                        'score': round(cloud_score, 1),
                        'value': clouds.get('all'),
                        'weight': self.CLOUD_THRESHOLDS[event_type]['weight']
                    },
                    'visibility': {
                        'score': round(visibility_score, 1),
                        'value': weather_data.get('visibility'),
                        'weight': self.VISIBILITY_THRESHOLDS[event_type]['weight']
                    }
                }
            }

        except Exception as e:
            logger.error(f"Error calculating weather score: {e}")
            return {
                'score': 0,
                'condition': 'error',
                'details': str(e)
            }

    def _calculate_temperature_score(self, temp: float, event_type: str) -> float:
        """Calculate temperature score based on event type"""
        if temp is None:
            return 0

        thresholds = self.TEMP_THRESHOLDS[event_type]
        optimal_min, optimal_max = thresholds['optimal']
        acceptable_min, acceptable_max = thresholds['acceptable']

        if optimal_min <= temp <= optimal_max:
            return 100
        elif acceptable_min <= temp <= acceptable_max:
            return 70
        else:
            return 30

    def _calculate_wind_score(self, wind_speed: float, event_type: str) -> float:
        """Calculate wind score based on event type"""
        if wind_speed is None:
            return 0

        thresholds = self.WIND_THRESHOLDS[event_type]
        optimal_min, optimal_max = thresholds['optimal']
        acceptable_min, acceptable_max = thresholds['acceptable']

        if optimal_min <= wind_speed <= optimal_max:
            return 100
        elif acceptable_min <= wind_speed <= acceptable_max:
            return 70
        else:
            return 30

    def _calculate_rain_score(self, rain_amount: float, event_type: str) -> float:
        """Calculate rain score based on event type"""
        thresholds = self.RAIN_THRESHOLDS[event_type]
        optimal = thresholds['optimal']
        acceptable = thresholds['acceptable']

        if rain_amount <= optimal:
            return 100
        elif rain_amount <= acceptable:
            return 70
        else:
            return 30

    def _calculate_cloud_score(self, cloud_cover: float, event_type: str) -> float:
        """Calculate cloud cover score based on event type"""
        if cloud_cover is None:
            return 0

        thresholds = self.CLOUD_THRESHOLDS[event_type]
        optimal_min, optimal_max = thresholds['optimal']
        acceptable_min, acceptable_max = thresholds['acceptable']

        if optimal_min <= cloud_cover <= optimal_max:
            return 100
        elif acceptable_min <= cloud_cover <= acceptable_max:
            return 70
        else:
            return 30

    def _calculate_visibility_score(self, visibility: float, event_type: str) -> float:
        """Calculate visibility score based on event type"""
        if visibility is None:
            return 0

        thresholds = self.VISIBILITY_THRESHOLDS[event_type]
        optimal = thresholds['optimal']
        acceptable = thresholds['acceptable']

        if visibility >= optimal:
            return 100
        elif visibility >= acceptable:
            return 70
        else:
            return 30

    def _get_weather_condition(self, score: float) -> str:
        """Get weather condition based on score"""
        if score >= 80:
            return 'excellent'
        elif score >= 60:
            return 'good'
        elif score >= 40:
            return 'fair'
        else:
            return 'poor'

class WeatherAnalysisService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    async def get_historical_comparison(self, location: str, date: datetime) -> Dict:
        """Compare with past week's weather for the same day"""
        try:
            # Get weather for the target date
            target_weather = await weather_service.get_weather_for_date(location, date)
            if not target_weather:
                return {}

            # Get weather for the same day in previous week
            last_week_date = date - timedelta(days=7)
            last_week_weather = await weather_service.get_weather_for_date(location, last_week_date)

            comparison = {
                "target_date": {
                    "date": date.isoformat(),
                    "weather": target_weather.dict() if target_weather else None
                },
                "last_week": {
                    "date": last_week_date.isoformat(),
                    "weather": last_week_weather.dict() if last_week_weather else None
                }
            }

            if target_weather and last_week_weather:
                comparison["temperature_diff"] = target_weather.temperature - last_week_weather.temperature
                comparison["precipitation_diff"] = target_weather.precipitation - last_week_weather.precipitation
                comparison["wind_diff"] = target_weather.wind_speed - last_week_weather.wind_speed

            return comparison
        except Exception as e:
            self.logger.error(f"Error getting historical comparison: {e}")
            return {}

    async def get_hourly_breakdown(self, location: str, event: Event) -> List[Dict[str, Any]]:
        """Get detailed hourly weather breakdown for an event"""
        try:
            # Get hourly forecast
            hourly_data = await weather_service.get_hourly_forecast(location, event.date)
            if not hourly_data:
                return []

            # Convert event date to datetime if it's a string
            event_date = event.date if isinstance(event.date, datetime) else datetime.fromisoformat(event.date)

            # Filter and process hourly data
            breakdown = []
            for hour_data in hourly_data:
                hour_time = datetime.fromtimestamp(hour_data['dt'])
                if hour_time.date() == event_date.date():
                    score = weather_service._calculate_weather_score(hour_data, event.event_type)
                    breakdown.append({
                        'time': hour_time.strftime('%H:%M'),
                        'temperature': hour_data['main']['temp'],
                        'description': hour_data['weather'][0]['description'],
                        'score': score
                    })

            return breakdown

        except Exception as e:
            self.logger.error(f"Error getting hourly breakdown: {e}")
            return []

    async def get_alternative_dates(self, location: str, event: Event) -> List[Dict[str, Any]]:
        """Get alternative dates with weather scores"""
        try:
            # Get forecast data
            forecast = await weather_service.get_hourly_forecast(location, event.date)
            if not forecast:
                return []

            # Log the first forecast entry to see the structure
            if forecast:
                self.logger.info(f"Processing {len(forecast)} forecast entries")
                self.logger.info("Sample forecast entry structure:")
                self.logger.info(json.dumps(forecast[0], indent=2))

            # Group forecasts by date to reduce API calls
            date_forecasts = {}
            for entry in forecast:
                try:
                    date = datetime.fromtimestamp(entry['dt']).date()
                    if date == event.date.date():
                        continue  # Skip the original event date
                    
                    if date not in date_forecasts:
                        date_forecasts[date] = []
                    date_forecasts[date].append(entry)
                except Exception as e:
                    self.logger.error(f"Error processing forecast date: {e}")
                    continue

            # Analyze weather for each unique date
            alternatives = []
            for date, forecasts in date_forecasts.items():
                try:
                    # Calculate averages for the day
                    temps = []
                    feels_like = []
                    humidity = []
                    wind_speeds = []
                    cloud_cover = []
                    rain_amounts = []
                    weather_conditions = []
                    
                    for forecast in forecasts:
                        # Temperature data
                        main = forecast.get('main', {})
                        if 'temp' in main:
                            temps.append(float(main['temp']))
                        if 'feels_like' in main:
                            feels_like.append(float(main['feels_like']))
                        if 'humidity' in main:
                            humidity.append(float(main['humidity']))
                        
                        # Wind data
                        wind = forecast.get('wind', {})
                        if 'speed' in wind:
                            wind_speeds.append(float(wind['speed']))
                        
                        # Cloud data
                        clouds = forecast.get('clouds', {})
                        if 'all' in clouds:
                            cloud_cover.append(float(clouds['all']))
                        
                        # Rain data
                        rain = forecast.get('rain', {})
                        if '3h' in rain:
                            rain_amounts.append(float(rain['3h']))
                        
                        # Weather conditions
                        weather_list = forecast.get('weather', [])
                        if weather_list:
                            weather = weather_list[0]
                            weather_conditions.append({
                                'id': weather.get('id'),
                                'main': weather.get('main'),
                                'description': weather.get('description'),
                                'icon': weather.get('icon')
                            })

                    if not temps or not weather_conditions:
                        continue

                    # Calculate averages
                    avg_temp = sum(temps) / len(temps)
                    avg_feels_like = sum(feels_like) / len(feels_like) if feels_like else avg_temp
                    avg_humidity = sum(humidity) / len(humidity) if humidity else 0
                    avg_wind = sum(wind_speeds) / len(wind_speeds) if wind_speeds else 0
                    avg_clouds = sum(cloud_cover) / len(cloud_cover) if cloud_cover else 0
                    total_rain = sum(rain_amounts) if rain_amounts else 0
                    
                    # Get most common weather condition
                    main_weather = max(set(w['main'] for w in weather_conditions), key=lambda x: sum(1 for w in weather_conditions if w['main'] == x))
                    main_description = max(set(w['description'] for w in weather_conditions), key=lambda x: sum(1 for w in weather_conditions if w['description'] == x))
                    
                    # Create weather data object
                    weather_data = {
                        'dt': int(datetime.combine(date, datetime.min.time()).timestamp()),
                        'main': {
                            'temp': round(avg_temp, 1),
                            'feels_like': round(avg_feels_like, 1),
                            'temp_min': min(temps),
                            'temp_max': max(temps),
                            'pressure': 1013,  # Default pressure
                            'humidity': round(avg_humidity),
                            'temp_kf': 0
                        },
                        'weather': [{
                            'id': weather_conditions[0]['id'],
                            'main': main_weather,
                            'description': main_description,
                            'icon': weather_conditions[0]['icon']
                        }],
                        'clouds': {
                            'all': round(avg_clouds)
                        },
                        'wind': {
                            'speed': round(avg_wind, 1),
                            'deg': 0,  # Default direction
                            'gust': round(avg_wind * 1.5, 1)  # Estimate gust
                        },
                        'visibility': 10000,
                        'pop': round(total_rain / 3, 2) if total_rain > 0 else 0,
                        'rain': {'3h': round(total_rain, 2)} if total_rain > 0 else {},
                        'sys': {
                            'pod': 'd' if 6 <= datetime.now().hour <= 18 else 'n'
                        },
                        'dt_txt': datetime.combine(date, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    
                    # Calculate score
                    score = self._calculate_simple_score(WeatherData(
                        temperature=avg_temp,
                        precipitation=total_rain,
                        wind_speed=avg_wind,
                        cloud_cover=avg_clouds,
                        description=main_description,
                        timestamp=datetime.combine(date, datetime.min.time())
                    ))
                    
                    condition = self._get_weather_condition(score)

                    # Add to alternatives
                    alternatives.append({
                        'date': datetime.combine(date, datetime.min.time()).isoformat(),
                        'score': round(score, 1),
                        'condition': condition,
                        'temperature': round(avg_temp, 1),
                        'description': main_description,
                        'weather_data': weather_data
                    })

                except Exception as e:
                    self.logger.error(f"Error processing date forecasts: {e}")
                    continue

            # Sort alternatives by score and return top 5
            alternatives.sort(key=lambda x: x['score'], reverse=True)
            return alternatives[:5]  # Return top 5 alternatives

        except Exception as e:
            self.logger.error(f"Error getting alternative dates: {e}")
            return []

    def _get_weather_condition(self, score: float) -> str:
        """Get weather condition based on score"""
        if score >= 70:
            return "good"
        elif score >= 49:  # 70 * 0.7
            return "okay"
        else:
            return "poor"

    async def analyze_weather_trends(self, location: str, date: datetime) -> Dict:
        """Analyze improving/worsening weather trends"""
        try:
            # Get 3-hour forecast data
            hourly_data = await weather_service.get_hourly_forecast(location, date)
            if not hourly_data:
                return {}

            trends = {
                "temperature": self._analyze_trend([w.temperature for w in hourly_data]),
                "precipitation": self._analyze_trend([w.precipitation for w in hourly_data]),
                "wind": self._analyze_trend([w.wind_speed for w in hourly_data]),
                "cloud_cover": self._analyze_trend([w.cloud_cover for w in hourly_data])
            }

            return trends
        except Exception as e:
            self.logger.error(f"Error analyzing weather trends: {e}")
            return {}

    async def compare_nearby_locations(self, location: str, date: datetime) -> List[Dict]:
        """Compare weather across nearby cities"""
        try:
            # Get coordinates for the main location
            coords = await weather_service.get_coordinates(location)
            if not coords:
                return []

            # Define nearby cities (example coordinates)
            nearby_cities = [
                {"name": "City 1", "lat": coords["lat"] + 0.1, "lon": coords["lon"] + 0.1},
                {"name": "City 2", "lat": coords["lat"] - 0.1, "lon": coords["lon"] - 0.1},
                {"name": "City 3", "lat": coords["lat"] + 0.1, "lon": coords["lon"] - 0.1}
            ]

            comparisons = []
            for city in nearby_cities:
                weather = await weather_service.get_weather_for_date(
                    f"{city['lat']},{city['lon']}", date
                )
                if weather:
                    comparisons.append({
                        "city": city["name"],
                        "weather": weather.dict()
                    })

            return comparisons
        except Exception as e:
            self.logger.error(f"Error comparing nearby locations: {e}")
            return []

    def _calculate_hour_score(self, weather: WeatherData, event_type: str) -> float:
        """Calculate weather score for a specific hour"""
        # Reuse the scoring logic from event service
        from .event_service import event_service
        return event_service._calculate_weather_score(weather, event_type)

    def _analyze_trend(self, values: List[float]) -> Dict:
        """Analyze trend in a series of values"""
        if not values:
            return {"trend": "unknown", "change": 0}

        # Calculate simple linear regression
        n = len(values)
        if n < 2:
            return {"trend": "stable", "change": 0}

        x = list(range(n))
        y = values

        # Calculate slope
        slope = (n * sum(i * j for i, j in zip(x, y)) - sum(x) * sum(y)) / (n * sum(i * i for i in x) - sum(x) ** 2)

        # Determine trend
        if abs(slope) < 0.1:
            trend = "stable"
        else:
            trend = "improving" if slope < 0 else "worsening"

        # Calculate total change
        change = values[-1] - values[0]

        return {
            "trend": trend,
            "change": change,
            "slope": slope
        }

    async def get_better_weather_alternatives(
        self,
        location: str,
        event_date: datetime,
        date_range: int = 7,  # Look for alternatives within 7 days
        nearby_locations: List[str] = None
    ) -> Dict[str, Any]:
        """Get alternative dates and locations with better weather"""
        try:
            # Get forecast for the date range
            forecast = await weather_service.get_forecast(location, date_range)
            self.logger.info(f"Raw forecast data: {forecast}")
            
            if not forecast:
                return {
                    "success": False,
                    "message": "Could not fetch weather forecast",
                    "alternatives": []
                }

            # Get current event's weather
            current_weather = await weather_service.get_weather_for_date(location, event_date)
            if not current_weather:
                return {
                    "success": False,
                    "message": "Could not fetch current event weather",
                    "alternatives": []
                }

            # Calculate current event's score
            current_score = self._calculate_simple_score(current_weather)
            
            # Analyze weather for each day in the forecast
            alternatives = []
            for entry in forecast:
                try:
                    self.logger.info(f"Processing forecast entry: {entry}")
                    
                    # Extract timestamp and create date
                    dt = entry.get('dt')
                    if not dt:
                        self.logger.warning("No timestamp in forecast entry")
                        continue
                        
                    date = datetime.fromtimestamp(dt)
                    if date.date() == event_date.date():
                        continue  # Skip the original event date

                    # Extract main weather data
                    main = entry.get('main', {})
                    if not main:
                        self.logger.warning(f"No main weather data for date {date}")
                        continue

                    temp = main.get('temp')
                    if temp is None:
                        self.logger.warning(f"No temperature data for date {date}")
                        continue

                    # Extract weather description
                    weather_list = entry.get('weather', [])
                    if not weather_list:
                        self.logger.warning(f"No weather data for date {date}")
                        continue

                    weather = weather_list[0]
                    desc = weather.get('description')
                    if not desc:
                        self.logger.warning(f"No weather description for date {date}")
                        continue

                    # Extract other weather data
                    precip = entry.get('rain', {}).get('3h', 0)
                    wind = entry.get('wind', {}).get('speed', 0)
                    clouds = entry.get('clouds', {}).get('all', 0)

                    # Create weather data object
                    weather_data = WeatherData(
                        temperature=float(temp),
                        precipitation=float(precip),
                        wind_speed=float(wind),
                        cloud_cover=float(clouds),
                        description=str(desc),
                        timestamp=date
                    )
                    
                    # Calculate score and condition
                    score = self._calculate_simple_score(weather_data)
                    condition = self._get_weather_condition(score)

                    # Only include if weather is better
                    if score > current_score:
                        alternative = {
                            'date': date.isoformat(),
                            'location': location,
                            'score': score,
                            'temperature': round(float(temp), 1),
                            'precipitation': round(float(precip), 1),
                            'wind_speed': round(float(wind), 1),
                            'description': str(desc),
                            'condition': condition
                        }
                        self.logger.info(f"Adding alternative: {alternative}")
                        alternatives.append(alternative)

                except Exception as e:
                    self.logger.error(f"Error processing forecast entry: {e}")
                    continue

            # Check nearby locations if provided
            if nearby_locations:
                for alt_location in nearby_locations:
                    try:
                        location_weather = await weather_service.get_weather_for_date(alt_location, event_date)
                        if location_weather and location_weather.temperature is not None:
                            location_score = self._calculate_simple_score(location_weather)
                            condition = self._get_weather_condition(location_score)
                            
                            if location_score > current_score:
                                alternatives.append({
                                    'date': event_date.isoformat(),
                                    'location': alt_location,
                                    'score': location_score,
                                    'temperature': round(float(location_weather.temperature), 1),
                                    'precipitation': round(float(location_weather.precipitation), 1),
                                    'wind_speed': round(float(location_weather.wind_speed), 1),
                                    'description': str(location_weather.description),
                                    'condition': condition
                                })
                    except Exception as e:
                        self.logger.warning(f"Error checking location {alt_location}: {e}")
                        continue

            # Sort alternatives by score
            alternatives.sort(key=lambda x: x['score'], reverse=True)

            # Prepare response
            response = {
                "success": True,
                "current_weather": {
                    "date": event_date.isoformat(),
                    "location": location,
                    "score": current_score,
                    "temperature": round(float(current_weather.temperature), 1),
                    "precipitation": round(float(current_weather.precipitation), 1),
                    "wind_speed": round(float(current_weather.wind_speed), 1),
                    "description": str(current_weather.description),
                    "condition": self._get_weather_condition(current_score)
                },
                "alternatives": alternatives[:5]  # Return top 5 alternatives
            }
            
            self.logger.info(f"Final response: {response}")
            return response

        except Exception as e:
            self.logger.error(f"Error getting better weather alternatives: {e}")
            return {
                "success": False,
                "message": str(e),
                "alternatives": []
            }

    def _calculate_simple_score(self, weather_data: WeatherData) -> float:
        """Calculate a simple weather score based on temperature and conditions"""
        try:
            # Base score starts at 100
            score = 100.0
            
            # Temperature scoring (ideal range: 18-25°C)
            temp = weather_data.temperature
            if temp > 30:  # Too hot
                score -= (temp - 30) * 2
            elif temp < 10:  # Too cold
                score -= (10 - temp) * 2
            elif temp > 25:  # Warm
                score -= (temp - 25)
            elif temp < 18:  # Cool
                score -= (18 - temp)
            
            # Weather condition scoring
            desc = weather_data.description.lower()
            if 'thunderstorm' in desc:
                score -= 40
            elif 'rain' in desc or 'drizzle' in desc:
                score -= 30
            elif 'snow' in desc:
                score -= 35
            elif 'mist' in desc or 'fog' in desc:
                score -= 15
            elif 'cloud' in desc:
                score -= 10
            elif 'clear' in desc or 'sunny' in desc:
                score += 5
            
            # Wind speed impact
            if weather_data.wind_speed > 20:  # Strong wind
                score -= 20
            elif weather_data.wind_speed > 10:  # Moderate wind
                score -= 10
            
            # Precipitation impact
            if weather_data.precipitation > 0:
                score -= weather_data.precipitation * 10
            
            # Ensure score stays within reasonable bounds
            return max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating weather score: {e}")
            return 50.0  # Return middle score on error

weather_analysis = WeatherAnalysis() 
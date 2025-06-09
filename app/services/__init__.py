from .weather_service import WeatherService
from .weather_analysis import WeatherAnalysis
from .weather_instances import weather_service, weather_analysis

# Create the instances
weather_service = WeatherService()
weather_analysis = WeatherAnalysis()

# Export the instances
__all__ = ['weather_service', 'weather_analysis'] 
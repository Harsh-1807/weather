# This file will be imported after both WeatherService and WeatherAnalysis are defined
# The actual instances will be created in __init__.py

# These are just type hints for IDE support
from .weather_service import WeatherService
from .weather_analysis import WeatherAnalysis

# The actual instances will be created in __init__.py
weather_service = None
weather_analysis = None 
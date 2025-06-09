# Weather Event Planner

A backend service that helps users plan outdoor events by integrating weather forecasts and providing intelligent recommendations.

## Features

- Weather API integration with OpenWeatherMap
- Event management system
- Weather analysis and scoring
- Alternative date recommendations
- Caching system for weather data

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your OpenWeatherMap API key:
   ```
   OPENWEATHER_API_KEY=your_api_key_here
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Event Management
- POST /events - Create event
- GET /events - List all events
- PUT /events/{id} - Update event

### Weather Integration
- GET /weather/{location}/{date} - Get weather for location and date
- POST /events/{id}/weather-check - Analyze weather for event
- GET /events/{id}/alternatives - Get better weather dates

### Analytics
- GET /events/{id}/suitability - Get weather suitability score

## Testing

The application includes a Postman collection for testing all endpoints. Import the `Weather_Event_Planner.postman_collection.json` file into Postman to get started.

## Environment Variables

- `OPENWEATHER_API_KEY`: Your OpenWeatherMap API key
- `PORT`: Port number for the application (default: 8000) 
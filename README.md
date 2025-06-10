#DEPLOYED ON : https://skylight-ur48.onrender.com


#POSTMAN LINK : https://harsh-3069181.postman.co/workspace/Harsh's-Workspace~d07d0c61-a134-4213-8b69-cab1f45918ee/collection/45737676-e91fbee6-a2af-424d-abe8-7d37025fb4e1?action=share&creator=45737676&active-environment=45737676-ee947ec6-c60c-4d67-8971-8119a33b8763
<p align="center">
  <img src="https://github.com/user-attachments/assets/249a9917-5fb7-417d-9354-5c150968a8c5" width="400" height="250" />
  <img src="https://github.com/user-attachments/assets/8eccc2ff-61c1-48b1-8128-2090ac0ca9a3" width="400" height="250" />
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/617f8c17-4daf-49bd-85b2-675c3a3a3d11" width="400" height="250" />
  <img src="https://github.com/user-attachments/assets/d7d3d043-cd3f-4af9-9054-456c798bd8b9" width="400" height="250" />
</p>




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

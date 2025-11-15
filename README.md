# Where It Went

A real-time interactive map application that visualizes federal spending data geographically. Track government spending by location and explore spending patterns across different places in the United States.

## Features

- 🗺️ **Interactive Map**: Real-time visualization of federal spending data on an interactive Mapbox map
- 📍 **Location Search**: Search for places using Google Places API with autocomplete suggestions
- 🎯 **Two Modes**:
  - **Live Tracking Mode**: Automatically tracks your current location and displays nearby spending
  - **Explore Mode**: Manually explore different locations on the map
- 📊 **Spending Reports**: View detailed spending reports for specific locations with charts and data tables
- 🔍 **Smart Search**: Fly to any place in explore mode or view the spending reports directly
- 📱 **Responsive Design**: Works seamlessly on desktop and mobile devices

## Tech Stack

### Backend
- **Python 3.13+** with Flask
- **Flask-SocketIO** for real-time communication
- **DynamoDB** for data storage (local development with DynamoDB Local)
- **Redis** for caching and session management
- **Google Places API** for location search and autocomplete
- **USA Spending API** for federal spending data
- **OpenAI API** for AI-powered report generation

### Frontend
- **React 19** with TypeScript
- **Vite** for fast development and building
- **Mapbox GL JS** for interactive maps
- **Socket.IO Client** for real-time updates
- **Chart.js** for data visualization

### Development Tools
- **Docker Compose** for containerized development
- **uv** for Python package management
- **Ruff** for linting and formatting
- **Basedpyright** for type checking

## Prerequisites

- **Python 3.13+**
- **Node.js 18+** and npm
- **Docker** and Docker Compose (for containerized development)
- **uv** package manager ([installation instructions](#installation))
- **API Keys**:
  - Google Places API key
  - Mapbox access token (for frontend)
  - OpenAI API key (optional, for AI report generation)

## Installation

### 1. Install uv

**On macOS and Linux:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**On Windows:**
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone the repository

```bash
git clone <repository-url>
cd where-it-went
```

### 3. Install Python dependencies

```bash
uv sync
```

### 4. Install Frontend dependencies

```bash
cd frontend
npm install
cd ..
```

## Environment Variables

Create a `.env` file in the root directory based on `env.example`:

```bash
# Port configuration
PORT=5000
APP_PORT=5000
REDIS_PORT=6379

# Google Places API Key (required)
PLACES_API_KEY=your_places_api_key_here

# OpenAI API Key (optional, for AI report generation)
OPENAI_API_KEY=your_openai_api_key_here

# DynamoDB configuration (for local development)
DYNAMODB_ENDPOINT=http://dynamodb-local:8000

# Flask configuration
FLASK_ENV=development
FLASK_APP=where_it_went.app:app
```

For the frontend, create a `.env` file in the `frontend` directory:

```bash
VITE_MAPBOX_ACCESS_TOKEN=your_mapbox_access_token_here
```

## Running the Project

### Option 1: Docker Compose (Recommended)

Run the entire stack with Docker Compose:

```bash
docker compose -f compose.dev.yml up
```

This will start:
- Flask backend on `http://localhost:5000`
- React frontend on `http://localhost:3000`
- Redis on port `6379`
- DynamoDB Local on port `8000`

### Option 2: Local Development

**Backend:**
```bash
uv run where-it-went
```

**Frontend (in a separate terminal):**
```bash
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:3000` and will proxy API requests to the backend.

## Development

### Running Tests

```bash
uv run pytest
```

### Linting and Formatting

```bash
# Lint
uv run ruff check --fix

# Format
uv run ruff format
```

### Type Checking

```bash
uv run basedpyright
```

### Frontend Development

```bash
cd frontend
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
```

## Project Structure

```
where-it-went/
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── components/    # React components
│   │   ├── services/      # API services
│   │   └── types/         # TypeScript type definitions
│   └── package.json
├── src/
│   └── where_it_went/     # Python backend application
│       ├── service/       # Business logic services
│       ├── routes.py      # API routes
│       └── app.py         # Flask application setup
├── test/                  # Test files
├── docker/                # Docker configuration
├── compose.dev.yml        # Docker Compose for development
├── pyproject.toml         # Python project configuration
└── README.md
```

## VS Code Setup

### Recommended Extensions

1. **Basedpyright**: https://marketplace.visualstudio.com/items?itemName=detachhead.basedpyright
2. **Ruff**: https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff

### VS Code Settings

Add this to your VS Code settings (`.vscode/settings.json` or User Settings):

```json
{
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports.ruff": "explicit"
    }
  }
}
```

## API Endpoints

- `GET /health` - Health check endpoint
- `POST /api/autocomplete` - Location autocomplete search
- `POST /api/text-search` - Text-based location search
- `POST /api/generate-summary` - Generate AI summary of spending data
- `POST /api/process-chart-data` - Process spending data for charts
- `POST /api/process-table-data` - Process spending data for tables
- `GET /search-spending-by-award` - Search federal spending by award

## Features in Detail

### Live Tracking Mode
- Automatically tracks your GPS location
- Updates spending data as you move
- Fetches nearby places within a configurable radius

### Explore Mode
- Manually navigate the map
- Search for specific locations
- View spending data for any location on the map


### Search Features
- Intelligent autocomplete
- Real-time suggestion updates
- "Fly To" feature to quickly navigate to searched locations in explore mode



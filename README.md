# Smart Traffic System

<p align="center">
  <b>AI Traffic Prediction & A*-OSM Smart Routing Engine</b><br/>
  Production-ready FastAPI Backend with Strict Validation Mode
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.14-blue"/>
  <img src="https://img.shields.io/badge/fastapi-high--performance-green"/>
  <img src="https://img.shields.io/badge/ml-xgboost%20%7C%20lightgbm-orange"/>
  <img src="https://img.shields.io/badge/routing-A*--OSM-red"/>
  <img src="https://img.shields.io/badge/status-production--ready-success"/>
</p>

## Overview

Smart Traffic System is an advanced backend platform that combines:

- Machine Learning for traffic prediction
- A*-based routing on OpenStreetMap (OSM) graphs
- High-performance FastAPI service architecture
- Strict production validation mode

This project is designed for real-world smart city workloads, not demo-only use cases.

## Key Highlights

- A* routing engine with OSM graph processing
- ML prediction service (XGBoost, LightGBM, Prophet)
- STRICT_REAL_MODE for production safety guarantees
- Structured logging with request tracing
- Health monitoring with full system diagnostics
- Modular and scalable architecture

## Core Features

### A*-OSM Routing Engine

- Builds graph from `.osm` map files
- Uses A* for shortest-path search
- Supports graph caching and spatial indexing
- In strict mode, fails fast when required map data is missing

### Machine Learning Prediction Layer

Supported models:

- XGBoost
- LightGBM
- Scikit-learn
- Prophet (time-series)

Capabilities:

- Runtime model readiness validation
- Health-check integrated model status reporting

### FastAPI Backend

- Async-ready, high-throughput API
- Automatic API documentation:
  - `/api/docs` (Swagger)
  - `/api/redoc`
- Versioned routing namespace:
  - `/api/v1/*`

### STRICT_REAL_MODE (Production Safety)

When `STRICT_REAL_MODE=true`, the application exits immediately if critical components are not ready.

App will stop on:

- Database unavailable
- ML models not loaded
- OSM graph missing or invalid

This guarantees:

- No fake/demo fallback data in production
- No silent partial startup
- Strong operational integrity

### Logging and Observability

- Structured logging using `structlog`
- Request tracing via `RequestIdMiddleware`
- Global exception capture and diagnostics

### Health Monitoring API

Endpoint: `GET /health`

Includes:

- ML model readiness
- Routing engine status
- Graph statistics (nodes, edges)
- Strict mode validation state
- System timestamp

## Architecture

```text
Client / Dashboard
        |
        v
 FastAPI Backend (main.py)
        |
        v
 +-------------------------+
 | Request Middleware      |
 | - Request ID            |
 | - Timing                |
 +-----------+-------------+
             |
             v
      API Router (/api/v1)
             |
             v
 +-------------------------+
 | Business Services       |
 | - Traffic Prediction    |
 | - Routing Engine        |
 +-----------+-------------+
             |
             v
 +-------------------------+
 | ML Models Layer         |
 | XGB / LGBM / Prophet    |
 +-----------+-------------+
             |
             v
 +-------------------------+
 | OSM Graph (A* Engine)   |
 +-------------------------+
```

## Startup Flow

1. Initialize logging
2. Load settings and configuration
3. Run strict mode validations
4. Initialize routing engine
   - Load `.osm` file
   - Build graph
   - Cache graph
5. Load ML prediction services
6. Start FastAPI application

## API Endpoints

### Root

`GET /`

Example response:

```json
{
  "message": "Welcome to Smart Traffic System API",
  "version": "1.0.0",
  "status": "operational"
}
```

### Health Check

`GET /health`

Returns system-level diagnostics, including ML and routing readiness.

### API v1

`/api/v1/*`

Business endpoints are grouped under versioned routing.

## Tech Stack

### Machine Learning

- scikit-learn
- xgboost
- lightgbm
- prophet

### Backend

- fastapi
- uvicorn
- pydantic v2
- structlog

### Routing

- A* algorithm
- OpenStreetMap (`.osm`)

### Data Layer

- SQLAlchemy
- pyodbc

## Getting Started

### 1. Clone repository

```bash
git clone https://github.com/duongloc216/Smart-Transport.git
cd Smart-Transport
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements-ml-demo.txt
```

### 4. Prepare OSM file

Make sure the map file exists:

```text
hcmc_10streets.osm
```

### 5. Run server

```bash
uvicorn main:app --reload
```

## Important Configuration

### Strict Mode

```env
STRICT_REAL_MODE=true
```

| Mode | Behavior |
|---|---|
| `true` | App exits if critical dependencies fail |
| `false` | Allows fallback behavior |

### Routing Engine

```env
ROUTING_ENGINE=A_STAR_OSM
```

## Why This Project Stands Out

- Not a CRUD-only backend
- Real ML + real routing pipeline
- Production-safe startup validation
- Clear architecture and scalability
- Built-in observability and diagnostics

Suitable for backend, AI, and internship portfolios.

## Future Improvements

- Real-time traffic streaming
- Frontend dashboard
- Cloud deployment
- Advanced route optimization

## Author

Duong Loc  
GitHub: https://github.com/duongloc216

## Support

If this project helps you:

- Star it
- Fork it
- Build on it

## Final Thought

"A smart city does not just collect data. It understands and acts on it."
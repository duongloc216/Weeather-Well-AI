# WeatherWell AI

Backend + workers + RAG pipeline for weather-aware health advisory in Vietnam.

The system combines:

- FastAPI API for auth, profile setup, visualization, and async chatbot requests
- Redis queues for background processing
- SQL Server for persistent weather, climate, UV, user, and suggestion data
- Local LLM + local embedding model for chatbot and passive health suggestions
- ChromaDB for disease-specific knowledge retrieval (RAG)
- React + Vite frontend (`vite-project/`)

## Main Architecture

```text
Frontend (React/Vite)
    |
    v
FastAPI (backend/app.py + backend/router.py)
    |
    +--> Redis queue_data ---------------------> worker/worker.py
    |                                             |- call weather/climate/uv APIs
    |                                             |- insert weather/climate/uv to SQL Server
    |
    +--> Redis queue_chatbot ------------------> chatbot/ai_agent.py
    |                                             |- read DB + user context
    |                                             |- local LLM generate response
    |                                             |- cache result to Redis DB1
    |
    +--> Redis queue_passive_suggestion -------> passive_suggestion/suggest_worker.py
                                                  |- Chroma retrieval by disease collection
                                                  |- local LLM generate suggestion
                                                  |- upsert suggestion table

Scheduler (scheduler/scheduler.py)
    |- 00:01 push weather collection jobs
    |- 00:30 push passive suggestion jobs
```

## Core Modules

- `backend/`
  - `app.py`: FastAPI app + CORS + router wiring
  - `router.py`: API endpoints for register/login, city setup, visualization, passive suggestion, chatbot submit/result
  - `jwt_utils.py`: JWT create/verify and auth dependency
- `worker/`
  - `worker.py`: Redis consumer for weather/climate/UV ingestion
  - `weather.py`, `climate.py`, `uv.py`, `period.py`: aggregate 3-hour API data into day periods
- `chatbot/`
  - `ai_agent.py`: async chatbot worker using local model
  - `tool_agent.py`: helper data access functions for agent tools
  - `chat_summary.py`: summarize recent chat history
- `passive_suggestion/`
  - `suggest_worker.py`: queue consumer for proactive suggestions
  - `langchain_suggestion.py`: RAG pipeline + suggestion upsert
  - `create_query_question.py`: query text construction
- `scheduler/`
  - `scheduler.py`: APScheduler cron entrypoint
  - `scheduler_push_job_collect_data.py`: push weather collection jobs
  - `scheduler_suggestion.py`: push suggestion jobs
  - `queries.py`: SQL query templates for scheduler/suggestion flow
- `core/`
  - `sqlserver_client.py`: async-compatible SQL Server access wrapper via `pyodbc`
  - `redis_client.py`: Redis DB0 queue, DB1 cache, DB2 chat history
  - `local_llm_client.py`: local GGUF LLM + embedding wrappers
  - `langchain_local_adapter.py`: LangChain-compatible adapters
- `rag/`
  - `rule_based.py`, `ml_based.py`: health interpretation utilities

## Data and Models

- `init_database.sql`: full SQL Server schema + seed disease/city data
- `chroma_data/`: persistent ChromaDB collections
- `models/qwen2.5-3b-instruct-q4_k_m.gguf`: local LLM file
- `models/embedding_model/`: local embedding model
- `data/weather_complete_2024.csv`, `data/weather_balanced_2022_2024.csv`: historical/training data

## Environment Setup

Create `.env` from `.env.example` and fill required values:

- SQL Server connection fields (`SQL_SERVER_*`)
- Redis host/port
- `OPEN_WEATHER_API`
- `JWT_SECRET_KEY`
- Queue names if customized

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Frontend:

```powershell
cd vite-project
npm install
cd ..
```

## Run Services (local)

Open multiple terminals from project root.

1. Redis server (if using bundled Windows Redis)

```powershell
cd redis
.\redis-server.exe
```

2. FastAPI backend

```powershell
python -m uvicorn backend.app:app --reload
```

3. Chatbot worker

```powershell
python -m chatbot.ai_agent
```

4. Data collection worker

```powershell
python -m worker.worker
```

5. Passive suggestion worker

```powershell
python -m passive_suggestion.suggest_worker
```

6. Scheduler (optional if running cron flow)

```powershell
python -m scheduler.scheduler
```

7. Frontend

```powershell
cd vite-project
npm run dev
```

## Useful Manual Scripts

- `python manual_crawl_all_cities.py`: push weather jobs for all tracked cities
- `python push_suggestion_job.py`: push passive suggestion jobs manually
- `python clear_suggestions.py`: clear suggestion data

## API Quick Reference

Base app: `backend/app.py`

- `POST /register`
- `POST /login`
- `POST /update_city_info_for_user`
- `PUT /update_disease`
- `GET /get_data_to_visualize/{city_id}`
- `GET /get_passive_suggestion/{city_id}`
- `POST /submit_chatbot_query`
- `GET /get_chatbot_result/{request_id}`

Default docs URL (when backend runs on 8000):

- Swagger: `http://localhost:8000/docs`

## Notes

- Chatbot and suggestion workers depend on both SQL Server and Redis connectivity.
- RAG suggestion generation requires valid Chroma collections in `chroma_data/`.
- Model files are loaded locally; ensure the paths in `models/` are present.

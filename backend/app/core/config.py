import os
from typing import List
from pydantic import BaseModel, Field


class Settings(BaseModel):
    PROJECT_NAME: str = "UrbanFlow AI Backend"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS Origins (allow local dev servers for Member 5)
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
    ]
    
    DEFAULT_CITY_NAME: str = "Metropolis SmartGrid"
    DEMO_OPERATOR_ID: str = os.getenv("DEMO_OPERATOR_ID", "DISPATCHER_LEAD_01")
    
    # Detour penalty in seconds for baseline navigation encountering a blocked road (e.g., 5 minutes = 300s)
    BLOCKED_ROAD_DETOUR_PENALTY_SECONDS: float = 300.0


settings = Settings()

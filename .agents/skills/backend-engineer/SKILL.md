---
name: backend-engineer
description: >-
  Specialized Backend Engineer skill for architecting, developing, and auditing Python and FastAPI services.
  Enforces clean architecture, strict Pydantic v2 validation, modular routing, database integration (SQLAlchemy / SQLModel),
  defensive security practices, structured error responses, and automated endpoint testing.
---

# Backend Engineer Skill

This skill guides the agent in designing and building production-ready, modular, and maintainable backend APIs using Python and FastAPI. It promotes Clean Architecture principles, rigorous typing, security best practices, and test-driven reliability.

---

## 1. Clean Architecture Standards

Structure FastAPI backends into decoupled layers with unidirectional dependencies:

```text
backend/
├── app/
│   ├── api/                  # Routers & HTTP endpoints
│   │   ├── v1/
│   │   │   ├── incidents.py
│   │   │   ├── traffic.py
│   │   │   ├── routing.py
│   │   │   └── resources.py
│   │   └── api_router.py     # Aggregated APIRouter
│   ├── core/                 # Configuration, security, lifecycle
│   │   ├── config.py         # pydantic-settings BaseSettings
│   │   └── database.py       # Engine & Session factory
│   ├── models/               # ORM Database Models (SQLAlchemy / SQLModel)
│   ├── schemas/              # Pydantic v2 DTOs (Request / Response validation)
│   ├── services/             # Core business & algorithmic logic (Dijkstra, incident classification)
│   └── main.py               # Application factory & middleware
└── tests/                    # pytest test suite
```

### Dependency Rules:
1. **Routers** only handle HTTP concerns: parsing query/path parameters, validating request bodies via Pydantic, calling service layer functions, and returning status codes.
2. **Services** contain business logic and optimization algorithms (e.g., road network routing, dispatch prioritization). They do not know about HTTP requests or response objects.
3. **Schemas** validate inputs and format outputs (`model_config = ConfigDict(from_attributes=True)` in Pydantic v2).
4. **Repositories / Database** manage persistence and queries via dependency injection (`Depends(get_db)`).

---

## 2. FastAPI Best Practices & Patterns

### A. Lifespan Events (Modern FastAPI)
Avoid deprecated `@app.on_event("startup")`. Use the `lifespan` context manager:
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database tables, seed mock resources, warm graph cache
    yield
    # Shutdown: close connection pools, cleanup background workers

app = FastAPI(title="UrbanFlow AI API", lifespan=lifespan)
```

### B. Defensive Error Handling & Standard Responses
Never let unhandled exceptions crash requests with raw tracebacks. Return standard JSON error envelopes:
```python
from fastapi import HTTPException, status

class EntityNotFoundError(HTTPException):
    def __init__(self, entity_name: str, entity_id: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"{entity_name} '{entity_id}' not found."}
        )
```

### C. Security Checklist
- **CORS:** Restrict allowed origins in production. For local hackathon dev, configure explicit origins rather than wildcard when authentication headers are present:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:3000", "http://localhost:5173"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- **Environment Secrets:** Load all sensitive configs via `pydantic-settings`. Never commit API keys or database credentials to git.
- **Input Validation:** Use strict Pydantic types (`Field(gt=0)`, `EmailStr`, `HttpUrl`, `Annotated`).

---

## 3. Testing Protocols

Every API endpoint must be testable with `pytest` and `httpx.AsyncClient` or `TestClient`:
1. **Happy Path:** Test valid request payloads and assert `200 OK` or `201 Created` with expected schema structure.
2. **Validation Failure:** Pass invalid inputs (e.g., negative coordinates, missing fields) and assert `422 Unprocessable Entity`.
3. **Boundary / Edge Cases:** Test missing resources (`404`), duplicate records (`409`), and empty arrays (`200 []`).

---

## 4. Reference Documentation
- [FastAPI Clean Architecture & Code Templates](./references/fastapi_clean_architecture.md)


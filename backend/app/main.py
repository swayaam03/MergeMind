from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import github, pull_requests

app = FastAPI(
    title="MergeMind API",
    description="Backend API for MergeMind — AI-powered semantic Git merge conflict resolver",
    version="0.1.0",
)

# CORS configuration
origins = [
    settings.FRONTEND_URL,
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(github.router, prefix="/api")
app.include_router(pull_requests.router, prefix="/api")


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "healthy", "app": "MergeMind"}

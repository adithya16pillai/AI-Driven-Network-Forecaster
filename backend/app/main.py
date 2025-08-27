from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import logging
from .database import engine, get_db
from .models import Base
from .config import settings

# Create tables
Base.metadata.create_all(bind=engine)

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Network Forecaster API",
    description="API for network traffic prediction and monitoring",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "AI Network Forecaster API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Include API routes
from .api.routes import router
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
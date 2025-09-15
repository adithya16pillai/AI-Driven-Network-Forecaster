from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
import logging
import json
import asyncio
from typing import List

from .database import engine, get_db, SessionLocal
from .models import Base, NetworkMetric
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

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:  # Create a copy to iterate
            try:
                await connection.send_text(message)
            except:
                # Remove broken connections
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/")
async def root():
    return {"message": "AI Network Forecaster API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send real-time updates every 30 seconds
            await asyncio.sleep(30)
            
            # Get latest data
            db = SessionLocal()
            try:
                latest_metrics = db.query(NetworkMetric).order_by(
                    desc(NetworkMetric.timestamp)
                ).limit(10).all()
                
                data = [{
                    'type': 'metric_update',
                    'device_id': m.device_id,
                    'metric_name': m.metric_name,
                    'value': float(m.value),
                    'timestamp': m.timestamp.isoformat()
                } for m in latest_metrics]
                
                await manager.send_personal_message(json.dumps(data), websocket)
            except Exception as e:
                logger.error(f"Error fetching metrics: {e}")
            finally:
                db.close()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Include API routes
from .api.routes import router
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
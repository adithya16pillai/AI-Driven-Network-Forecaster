from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, desc
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List, Optional
from ..app.database import get_db
from ..app.models import NetworkMetric, Prediction
from .schemas import NetworkMetric as NetworkMetricSchema, DeviceStatus

router = APIRouter()

@router.get("/metrics", response_model=List[NetworkMetricSchema])
async def get_metrics(
    device_id: Optional[str] = None,
    metric_name: Optional[str] = None,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """Get network metrics"""
    query = db.query(NetworkMetric)
    
    if device_id:
        query = query.filter(NetworkMetric.device_id == device_id)
    if metric_name:
        query = query.filter(NetworkMetric.metric_name == metric_name)
        
    return query.order_by(desc(NetworkMetric.timestamp)).limit(limit).all()

@router.get("/devices", response_model=List[DeviceStatus])
async def get_devices(db: Session = Depends(get_db)):
    """Get status of all monitored devices"""
    result = db.query(
        NetworkMetric.device_id,
        func.max(NetworkMetric.timestamp).label('last_seen'),
        func.count(NetworkMetric.id).label('metrics_count')
    ).group_by(NetworkMetric.device_id).all()
    
    devices = []
    for row in result:
        status = "online" if (datetime.utcnow() - row.last_seen).seconds < 300 else "offline"
        devices.append(DeviceStatus(
            device_id=row.device_id,
            last_seen=row.last_seen,
            metrics_count=row.metrics_count,
            status=status
        ))
    
    return devices

@router.get("/metrics/{device_id}/latest")
async def get_latest_metrics(device_id: str, db: Session = Depends(get_db)):
    """Get latest metrics for a device"""
    metrics = db.query(NetworkMetric).filter(
        NetworkMetric.device_id == device_id
    ).order_by(desc(NetworkMetric.timestamp)).limit(10).all()
    
    if not metrics:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return metrics

@router.post("/models/train")
async def train_models(
    device_id: Optional[str] = None,
    metric_name: Optional[str] = None
):
    """Train ML models"""
    trainer = ModelTrainer()
    
    try:
        if device_id and metric_name:
            # Train specific model
            result = trainer.train_single_model(device_id, metric_name)
            return {"results": [result]}
        else:
            # Train all models
            results = trainer.train_all_models()
            return {"results": results}
    finally:
        trainer.close()

@router.get("/predictions/{device_id}/{metric_name}", response_model=List[PredictionResponse])
async def get_predictions(
    device_id: str,
    metric_name: str,
    hours_ahead: int = Query(4, le=24)
):
    """Get predictions for a device and metric"""
    predictor = PredictionService()
    
    try:
        # Try to get stored predictions first
        predictions = predictor.get_stored_predictions(device_id, metric_name)
        
        # If no stored predictions or they're old, generate new ones
        if not predictions:
            predictions = predictor.generate_and_store_predictions(
                device_id, metric_name, hours_ahead
            )
        
        return predictions
    finally:
        predictor.close()

@router.post("/predictions/{device_id}/{metric_name}/generate")
async def generate_predictions(
    device_id: str,
    metric_name: str,
    hours_ahead: int = Query(4, le=24)
):
    """Generate new predictions for a device and metric"""
    predictor = PredictionService()
    
    try:
        predictions = predictor.generate_and_store_predictions(
            device_id, metric_name, hours_ahead
        )
        return {"predictions": predictions, "count": len(predictions)}
    finally:
        predictor.close()
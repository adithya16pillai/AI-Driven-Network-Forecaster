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
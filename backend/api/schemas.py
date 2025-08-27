from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from decimal import Decimal

class NetworkMetricBase(BaseModel):
    device_id: str
    metric_name: str
    value: Decimal
    unit: Optional[str] = None

class NetworkMetricCreate(NetworkMetricBase):
    pass

class NetworkMetric(NetworkMetricBase):
    id: int
    timestamp: datetime
    
    class Config:
        from_attributes = True

class PredictionResponse(BaseModel):
    device_id: str
    metric_name: str
    predicted_timestamp: datetime
    predicted_value: Decimal
    confidence_interval_lower: Optional[Decimal]
    confidence_interval_upper: Optional[Decimal]

class DeviceStatus(BaseModel):
    device_id: str
    last_seen: datetime
    metrics_count: int
    status: str
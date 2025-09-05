import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_
from ..app.database import SessionLocal
from ..app.models import NetworkMetric
import logging

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        self.db = SessionLocal()
        
    def fetch_time_series(
        self, 
        device_id: str, 
        metric_name: str, 
        days_back: int = 30
    ) -> pd.DataFrame:
        """Fetch time series data for a device and metric"""
        start_date = datetime.utcnow() - timedelta(days=days_back)
        
        metrics = self.db.query(NetworkMetric).filter(
            and_(
                NetworkMetric.device_id == device_id,
                NetworkMetric.metric_name == metric_name,
                NetworkMetric.timestamp >= start_date
            )
        ).order_by(NetworkMetric.timestamp).all()
        
        if not metrics:
            return pd.DataFrame()
        
        data = [{
            'ds': metric.timestamp,
            'y': float(metric.value),
            'device_id': metric.device_id,
            'metric_name': metric.metric_name
        } for metric in metrics]
        
        df = pd.DataFrame(data)
        df['ds'] = pd.to_datetime(df['ds'])
        return df
    
    def preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and preprocess the data"""
        if df.empty:
            return df
        
        # Remove duplicates
        df = df.drop_duplicates(subset=['ds'])
        
        # Sort by timestamp
        df = df.sort_values('ds')
        
        # Fill missing values
        df['y'] = df['y'].fillna(df['y'].median())
        
        # Remove outliers (values beyond 3 standard deviations)
        std_dev = df['y'].std()
        mean_val = df['y'].mean()
        df = df[abs(df['y'] - mean_val) <= (3 * std_dev)]
        
        # Resample to regular intervals (5-minute intervals)
        df.set_index('ds', inplace=True)
        df = df.resample('5T').mean().interpolate()
        df.reset_index(inplace=True)
        
        return df
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create additional features for the model"""
        if df.empty:
            return df
        
        df = df.copy()
        
        # Time-based features
        df['hour'] = df['ds'].dt.hour
        df['day_of_week'] = df['ds'].dt.dayofweek
        df['day_of_month'] = df['ds'].dt.day
        df['month'] = df['ds'].dt.month
        
        # Rolling statistics
        df['y_rolling_mean_1h'] = df['y'].rolling(window=12).mean()  # 12 * 5min = 1h
        df['y_rolling_std_1h'] = df['y'].rolling(window=12).std()
        df['y_rolling_mean_24h'] = df['y'].rolling(window=288).mean()  # 288 * 5min = 24h
        
        # Lag features
        df['y_lag_1h'] = df['y'].shift(12)
        df['y_lag_24h'] = df['y'].shift(288)
        
        return df.fillna(method='bfill').fillna(method='ffill')
    
    def close(self):
        self.db.close()
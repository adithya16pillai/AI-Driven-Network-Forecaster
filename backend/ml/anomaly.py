import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
import logging
from ..data.processors import DataProcessor

logger = logging.getLogger(__name__)

class AnomalyDetector:
    def __init__(self):
        self.data_processor = DataProcessor()
        self.models = {}
        self.scalers = {}
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for anomaly detection"""
        if df.empty:
            return df
        
        # Create features
        df_features = self.data_processor.create_features(df)
        
        # Select relevant features for anomaly detection
        feature_columns = [
            'y', 'hour', 'day_of_week', 'y_rolling_mean_1h', 
            'y_rolling_std_1h', 'y_lag_1h', 'y_lag_24h'
        ]
        
        # Filter columns that exist
        available_columns = [col for col in feature_columns if col in df_features.columns]
        
        if not available_columns:
            logger.warning("No features available for anomaly detection")
            return pd.DataFrame()
        
        return df_features[available_columns].dropna()
    
    def train_anomaly_model(self, device_id: str, metric_name: str, days_back: int = 30):
        """Train anomaly detection model"""
        # Fetch data
        df = self.data_processor.fetch_time_series(device_id, metric_name, days_back)
        
        if df.empty or len(df) < 100:
            logger.warning(f"Insufficient data for anomaly detection: {device_id}_{metric_name}")
            return False
        
        # Prepare features
        df_features = self.prepare_features(df)
        
        if df_features.empty:
            logger.warning(f"No features available for anomaly detection: {device_id}_{metric_name}")
            return False
        
        # Scale features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(df_features)
        
        # Train Isolation Forest
        model = IsolationForest(
            contamination=0.1,  # Expect 10% anomalies
            random_state=42,
            n_estimators=100
        )
        model.fit(features_scaled)
        
        # Store model and scaler
        model_key = f"{device_id}_{metric_name}"
        self.models[model_key] = model
        self.scalers[model_key] = scaler
        
        logger.info(f"Trained anomaly detection model for {model_key}")
        return True
    
    def detect_anomalies(
        self, 
        device_id: str, 
        metric_name: str, 
        recent_hours: int = 24
    ) -> List[Dict]:
        """Detect anomalies in recent data"""
        model_key = f"{device_id}_{metric_name}"
        
        if model_key not in self.models:
            logger.warning(f"No anomaly model found for {model_key}")
            return []
        
        # Get recent data
        df = self.data_processor.fetch_time_series(
            device_id, metric_name, days_back=recent_hours/24
        )
        
        if df.empty:
            return []
        
        # Prepare features
        df_features = self.prepare_features(df)
        
        if df_features.empty:
            return []
        
        # Scale features
        scaler = self.scalers[model_key]
        features_scaled = scaler.transform(df_features)
        
        # Predict anomalies
        model = self.models[model_key]
        anomaly_scores = model.decision_function(features_scaled)
        predictions = model.predict(features_scaled)
        
        # Identify anomalies
        anomalies = []
        for i, (score, pred) in enumerate(zip(anomaly_scores, predictions)):
            if pred == -1:  # Anomaly
                anomalies.append({
                    'device_id': device_id,
                    'metric_name': metric_name,
                    'timestamp': df.iloc[i]['ds'],
                    'value': float(df.iloc[i]['y']),
                    'anomaly_score': float(score),
                    'severity': 'high' if score < -0.5 else 'medium'
                })
        
        return anomalies
    
    def close(self):
        self.data_processor.close()
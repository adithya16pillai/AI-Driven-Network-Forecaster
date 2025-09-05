from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import logging
from .forecaster import NetworkForecaster
from ..data.processors import DataProcessor
from sqlalchemy.orm import Session
from ..app.database import SessionLocal
from ..app.models import Prediction

logger = logging.getLogger(__name__)

class PredictionService:
    def __init__(self):
        self.forecaster = NetworkForecaster()
        self.data_processor = DataProcessor()
        
    def generate_predictions(
        self, 
        device_id: str, 
        metric_name: str, 
        hours_ahead: int = 4
    ) -> List[Dict]:
        """Generate predictions for a device-metric combination"""
        try:
            # Calculate periods (5-minute intervals)
            periods = hours_ahead * 12  # 12 periods per hour
            
            # Make predictions
            forecast_df = self.forecaster.predict(device_id, metric_name, periods)
            
            # Convert to list of dictionaries
            predictions = []
            for _, row in forecast_df.iterrows():
                predictions.append({
                    'device_id': device_id,
                    'metric_name': metric_name,
                    'predicted_timestamp': row['ds'],
                    'predicted_value': float(row['yhat']),
                    'confidence_interval_lower': float(row['yhat_lower']),
                    'confidence_interval_upper': float(row['yhat_upper']),
                    'model_version': row['model_version']
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error generating predictions for {device_id}_{metric_name}: {e}")
            return []
    
    def save_predictions(self, predictions: List[Dict]):
        """Save predictions to database"""
        if not predictions:
            return
            
        db = SessionLocal()
        try:
            # Clear old predictions for this device-metric
            device_id = predictions[0]['device_id']
            metric_name = predictions[0]['metric_name']
            
            db.query(Prediction).filter(
                Prediction.device_id == device_id,
                Prediction.metric_name == metric_name
            ).delete()
            
            # Add new predictions
            for pred_data in predictions:
                prediction = Prediction(**pred_data)
                db.add(prediction)
            
            db.commit()
            logger.info(f"Saved {len(predictions)} predictions for {device_id}_{metric_name}")
            
        except Exception as e:
            logger.error(f"Error saving predictions: {e}")
            db.rollback()
        finally:
            db.close()
    
    def get_stored_predictions(
        self, 
        device_id: str, 
        metric_name: str
    ) -> List[Dict]:
        """Get stored predictions from database"""
        db = SessionLocal()
        try:
            predictions = db.query(Prediction).filter(
                Prediction.device_id == device_id,
                Prediction.metric_name == metric_name,
                Prediction.predicted_timestamp > datetime.utcnow()
            ).order_by(Prediction.predicted_timestamp).all()
            
            return [{
                'device_id': p.device_id,
                'metric_name': p.metric_name,
                'predicted_timestamp': p.predicted_timestamp,
                'predicted_value': float(p.predicted_value),
                'confidence_interval_lower': float(p.confidence_interval_lower) if p.confidence_interval_lower else None,
                'confidence_interval_upper': float(p.confidence_interval_upper) if p.confidence_interval_upper else None,
                'model_version': p.model_version,
                'created_at': p.created_at
            } for p in predictions]
            
        except Exception as e:
            logger.error(f"Error fetching predictions: {e}")
            return []
        finally:
            db.close()
    
    def generate_and_store_predictions(
        self, 
        device_id: str, 
        metric_name: str, 
        hours_ahead: int = 4
    ) -> List[Dict]:
        """Generate predictions and store them"""
        predictions = self.generate_predictions(device_id, metric_name, hours_ahead)
        if predictions:
            self.save_predictions(predictions)
        return predictions
    
    def close(self):
        self.data_processor.close()
import asyncio
from datetime import datetime
import logging
from typing import List, Dict
from ..data.processors import DataProcessor
from .forecaster import NetworkForecaster
from sqlalchemy.orm import Session
from ..app.database import SessionLocal
from ..app.models import NetworkMetric
from sqlalchemy import distinct

logger = logging.getLogger(__name__)

class ModelTrainer:
    def __init__(self):
        self.data_processor = DataProcessor()
        self.forecaster = NetworkForecaster()
        
    def get_training_targets(self) -> List[Dict[str, str]]:
        """Get list of device-metric combinations to train models for"""
        db = SessionLocal()
        try:
            # Get all unique device-metric combinations
            combinations = db.query(
                distinct(NetworkMetric.device_id),
                distinct(NetworkMetric.metric_name)
            ).all()
            
            targets = []
            for device_id, metric_name in combinations:
                if device_id and metric_name:
                    targets.append({
                        'device_id': device_id,
                        'metric_name': metric_name
                    })
            
            return targets
        finally:
            db.close()
    
    def train_single_model(self, device_id: str, metric_name: str, days_back: int = 30) -> Dict:
        """Train model for single device-metric combination"""
        try:
            # Fetch and preprocess data
            df = self.data_processor.fetch_time_series(device_id, metric_name, days_back)
            
            if df.empty:
                logger.warning(f"No data found for {device_id}_{metric_name}")
                return {'status': 'no_data', 'device_id': device_id, 'metric_name': metric_name}
            
            if len(df) < 100:  # Minimum data points for meaningful training
                logger.warning(f"Insufficient data for {device_id}_{metric_name}: {len(df)} points")
                return {'status': 'insufficient_data', 'device_id': device_id, 'metric_name': metric_name}
            
            # Preprocess data
            df_processed = self.data_processor.preprocess_data(df)
            
            # Train model
            result = self.forecaster.train_model(df_processed, device_id, metric_name)
            result['status'] = 'success'
            result['device_id'] = device_id
            result['metric_name'] = metric_name
            result['trained_at'] = datetime.utcnow()
            
            return result
            
        except Exception as e:
            logger.error(f"Error training model for {device_id}_{metric_name}: {e}")
            return {
                'status': 'error',
                'device_id': device_id,
                'metric_name': metric_name,
                'error': str(e)
            }
    
    def train_all_models(self, days_back: int = 30) -> List[Dict]:
        """Train models for all device-metric combinations"""
        targets = self.get_training_targets()
        results = []
        
        logger.info(f"Starting training for {len(targets)} device-metric combinations")
        
        for target in targets:
            result = self.train_single_model(
                target['device_id'], 
                target['metric_name'], 
                days_back
            )
            results.append(result)
            
            # Log progress
            if result['status'] == 'success':
                logger.info(f"✓ Trained model for {target['device_id']}_{target['metric_name']}")
            else:
                logger.warning(f"✗ Failed to train model for {target['device_id']}_{target['metric_name']}: {result.get('status', 'unknown')}")
        
        # Summary statistics
        successful = len([r for r in results if r['status'] == 'success'])
        logger.info(f"Training completed: {successful}/{len(results)} models trained successfully")
        
        return results
    
    def close(self):
        self.data_processor.close()

# CLI function for manual training
if __name__ == "__main__":
    import sys
    
    trainer = ModelTrainer()
    
    if len(sys.argv) > 1:
        # Train specific device-metric
        if len(sys.argv) == 3:
            device_id, metric_name = sys.argv[1], sys.argv[2]
            result = trainer.train_single_model(device_id, metric_name)
            print(f"Training result: {result}")
        else:
            print("Usage: python trainer.py <device_id> <metric_name>")
    else:
        # Train all models
        results = trainer.train_all_models()
        for result in results:
            print(result)
    
    trainer.close()
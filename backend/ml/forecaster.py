import pandas as pd
import numpy as np
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
import pickle
import os
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NetworkForecaster:
    def __init__(self, model_dir: str = "data/models"):
        self.model_dir = model_dir
        self.models = {}
        os.makedirs(model_dir, exist_ok=True)
        
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for Prophet model"""
        if df.empty or len(df) < 10:
            raise ValueError("Insufficient data for training")
        
        # Prophet expects 'ds' (timestamp) and 'y' (value) columns
        prophet_df = df[['ds', 'y']].copy()
        
        # Ensure proper data types
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
        prophet_df['y'] = pd.to_numeric(prophet_df['y'], errors='coerce')
        
        # Remove any rows with NaN values
        prophet_df = prophet_df.dropna()
        
        return prophet_df
    
    def train_model(
        self, 
        df: pd.DataFrame, 
        device_id: str, 
        metric_name: str,
        seasonality_mode: str = 'multiplicative'
    ) -> Dict:
        """Train Prophet model for specific device and metric"""
        try:
            prophet_df = self.prepare_data(df)
            
            # Configure Prophet model
            model = Prophet(
                yearly_seasonality=False,
                weekly_seasonality=True,
                daily_seasonality=True,
                seasonality_mode=seasonality_mode,
                interval_width=0.80,
                changepoint_prior_scale=0.05
            )
            
            # Add custom seasonalities for network traffic patterns
            model.add_seasonality(
                name='hourly',
                period=1,
                fourier_order=8
            )
            
            # Fit the model
            model.fit(prophet_df)
            
            # Store the model
            model_key = f"{device_id}_{metric_name}"
            self.models[model_key] = model
            
            # Save model to disk
            model_path = os.path.join(self.model_dir, f"{model_key}_prophet.pkl")
            with open(model_path, 'wb') as f:
                pickle.dump(model, f)
            
            # Calculate training metrics
            train_predictions = model.predict(prophet_df)
            mae = mean_absolute_error(prophet_df['y'], train_predictions['yhat'])
            rmse = np.sqrt(mean_squared_error(prophet_df['y'], train_predictions['yhat']))
            
            logger.info(f"Model trained for {device_id}_{metric_name} - MAE: {mae:.2f}, RMSE: {rmse:.2f}")
            
            return {
                'model_key': model_key,
                'training_mae': mae,
                'training_rmse': rmse,
                'training_samples': len(prophet_df),
                'model_path': model_path
            }
            
        except Exception as e:
            logger.error(f"Error training model for {device_id}_{metric_name}: {e}")
            raise
    
    def load_model(self, device_id: str, metric_name: str) -> Optional[Prophet]:
        """Load trained model"""
        model_key = f"{device_id}_{metric_name}"
        
        # Check if model is already loaded
        if model_key in self.models:
            return self.models[model_key]
        
        # Load from disk
        model_path = os.path.join(self.model_dir, f"{model_key}_prophet.pkl")
        if os.path.exists(model_path):
            try:
                with open(model_path, 'rb') as f:
                    model = pickle.load(f)
                self.models[model_key] = model
                return model
            except Exception as e:
                logger.error(f"Error loading model {model_key}: {e}")
        
        return None
    
    def predict(
        self, 
        device_id: str, 
        metric_name: str, 
        periods: int = 48  # 48 * 5min = 4 hours ahead
    ) -> pd.DataFrame:
        """Make predictions"""
        model = self.load_model(device_id, metric_name)
        if model is None:
            raise ValueError(f"No trained model found for {device_id}_{metric_name}")
        
        # Create future dataframe
        future = model.make_future_dataframe(periods=periods, freq='5T')
        
        # Make predictions
        forecast = model.predict(future)
        
        # Return only future predictions
        future_forecast = forecast.tail(periods)[
            ['ds', 'yhat', 'yhat_lower', 'yhat_upper']
        ].copy()
        
        # Add metadata
        future_forecast['device_id'] = device_id
        future_forecast['metric_name'] = metric_name
        future_forecast['model_version'] = '1.0'
        
        return future_forecast
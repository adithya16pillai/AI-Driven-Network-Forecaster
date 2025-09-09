import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  timeout: 10000,
});

export interface NetworkMetric {
  id: number;
  timestamp: string;
  device_id: string;
  metric_name: string;
  value: number;
  unit?: string;
}

export interface DeviceStatus {
  device_id: string;
  last_seen: string;
  metrics_count: number;
  status: string;
}

export interface Prediction {
  device_id: string;
  metric_name: string;
  predicted_timestamp: string;
  predicted_value: number;
  confidence_interval_lower?: number;
  confidence_interval_upper?: number;
}

export const api = {
  // Devices
  getDevices: (): Promise<DeviceStatus[]> =>
    apiClient.get('/devices').then(res => res.data),

  // Metrics
  getMetrics: (params?: {
    device_id?: string;
    metric_name?: string;
    limit?: number;
  }): Promise<NetworkMetric[]> =>
    apiClient.get('/metrics', { params }).then(res => res.data),

  getLatestMetrics: (deviceId: string): Promise<NetworkMetric[]> =>
    apiClient.get(`/metrics/${deviceId}/latest`).then(res => res.data),

  // Predictions
  getPredictions: (deviceId: string, metricName: string, hoursAhead?: number): Promise<Prediction[]> =>
    apiClient.get(`/predictions/${deviceId}/${metricName}`, {
      params: { hours_ahead: hoursAhead }
    }).then(res => res.data),

  generatePredictions: (deviceId: string, metricName: string, hoursAhead?: number): Promise<any> =>
    apiClient.post(`/predictions/${deviceId}/${metricName}/generate`, null, {
      params: { hours_ahead: hoursAhead }
    }).then(res => res.data),

  // Model training
  trainModels: (deviceId?: string, metricName?: string): Promise<any> =>
    apiClient.post('/models/train', null, {
      params: { device_id: deviceId, metric_name: metricName }
    }).then(res => res.data),
};
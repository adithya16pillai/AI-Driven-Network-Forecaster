import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export interface DeviceStatus {
  device_id: string;
  device_type?: string;
  status: 'online' | 'offline' | 'warning' | 'unknown';
  ip_address?: string;
  location?: string;
  last_seen?: string;
}

export interface NetworkMetric {
  id: number;
  device_id: string;
  metric_name: string;
  value: number;
  unit: string;
  timestamp: string;
}

export interface Prediction {
  id: number;
  device_id: string;
  metric_name: string;
  predicted_value: number;
  prediction_timestamp: string;
  confidence: number;
}

export interface MetricsQuery {
  device_id?: string;
  metric_name?: string;
  limit?: number;
  start_time?: string;
  end_time?: string;
}

class ApiService {
  private async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  async getDevices(): Promise<DeviceStatus[]> {
    try {
      return await this.request<DeviceStatus[]>('/api/v1/devices');
    } catch (error) {
      console.error('Error fetching devices:', error);
      // Return mock data for development
      return [
        {
          device_id: 'router-001',
          device_type: 'Router',
          status: 'online',
          ip_address: '192.168.1.1',
          location: 'Main Office',
          last_seen: new Date().toISOString(),
        },
        {
          device_id: 'switch-002',
          device_type: 'Switch',
          status: 'online',
          ip_address: '192.168.1.2',
          location: 'Server Room',
          last_seen: new Date().toISOString(),
        },
        {
          device_id: 'ap-003',
          device_type: 'Access Point',
          status: 'warning',
          ip_address: '192.168.1.3',
          location: 'Floor 2',
          last_seen: new Date().toISOString(),
        },
      ];
    }
  }

  async getMetrics(query: MetricsQuery): Promise<NetworkMetric[]> {
    try {
      const params = new URLSearchParams();
      if (query.device_id) params.append('device_id', query.device_id);
      if (query.metric_name) params.append('metric_name', query.metric_name);
      if (query.limit) params.append('limit', query.limit.toString());
      if (query.start_time) params.append('start_time', query.start_time);
      if (query.end_time) params.append('end_time', query.end_time);

      return await this.request<NetworkMetric[]>(`/api/v1/metrics?${params}`);
    } catch (error) {
      console.error('Error fetching metrics:', error);
      // Return mock data for development
      return this.generateMockMetrics(query.device_id || 'router-001');
    }
  }

  async getPredictions(deviceId: string, metricName: string, hours: number): Promise<Prediction[]> {
    try {
      return await this.request<Prediction[]>(
        `/api/v1/predictions/${deviceId}/${metricName}?hours=${hours}`
      );
    } catch (error) {
      console.error('Error fetching predictions:', error);
      return [];
    }
  }

  async generatePredictions(deviceId: string, metricName: string, hours: number): Promise<void> {
    await this.request(`/api/v1/predictions/${deviceId}/${metricName}/generate`, {
      method: 'POST',
      body: JSON.stringify({ hours }),
    });
  }

  async trainModels(deviceId: string, metricName: string): Promise<void> {
    await this.request(`/api/v1/models/${deviceId}/${metricName}/train`, {
      method: 'POST',
    });
  }

  private generateMockMetrics(deviceId: string): NetworkMetric[] {
    const metrics: NetworkMetric[] = [];
    const metricTypes = ['bandwidth', 'latency', 'packet_loss', 'cpu_usage'];
    const now = new Date();

    for (let i = 0; i < 50; i++) {
      const timestamp = new Date(now.getTime() - i * 60000); // Every minute
      
      metricTypes.forEach((metricType, index) => {
        let value: number;
        let unit: string;

        switch (metricType) {
          case 'bandwidth':
            value = Math.random() * 100 + 50; // 50-150 Mbps
            unit = 'Mbps';
            break;
          case 'latency':
            value = Math.random() * 50 + 10; // 10-60 ms
            unit = 'ms';
            break;
          case 'packet_loss':
            value = Math.random() * 5; // 0-5%
            unit = '%';
            break;
          case 'cpu_usage':
            value = Math.random() * 80 + 10; // 10-90%
            unit = '%';
            break;
          default:
            value = Math.random() * 100;
            unit = 'unit';
        }

        metrics.push({
          id: metrics.length + 1,
          device_id: deviceId,
          metric_name: metricType,
          value: parseFloat(value.toFixed(2)),
          unit,
          timestamp: timestamp.toISOString(),
        });
      });
    }

    return metrics.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }
}

export const api = new ApiService();
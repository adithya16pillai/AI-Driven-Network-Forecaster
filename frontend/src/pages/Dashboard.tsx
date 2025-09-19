import React, { useState, useEffect } from 'react';
import { api, DeviceStatus, NetworkMetric, Prediction } from '../services/api';
import { DeviceCard } from '../components/DeviceCard';
import { MetricChart } from '../components/MetricChart';
import { useWebSocket } from '../hooks/useWebSocket';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const [devices, setDevices] = useState<DeviceStatus[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<NetworkMetric[]>([]);
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(false);
  const { isConnected, latestData } = useWebSocket();

  // Load devices on component mount
  useEffect(() => {
    loadDevices();
  }, []);

  // Update metrics when WebSocket data arrives
  useEffect(() => {
    if (latestData.length > 0 && selectedDevice) {
      // Refresh metrics for selected device
      loadMetrics(selectedDevice);
    }
  }, [latestData, selectedDevice]);

  const loadDevices = async () => {
    try {
      const devicesData = await api.getDevices();
      setDevices(devicesData);
    } catch (error) {
      console.error('Error loading devices:', error);
    }
  };

  const loadMetrics = async (deviceId: string) => {
    setLoading(true);
    try {
      const metricsData = await api.getMetrics({
        device_id: deviceId,
        limit: 100
      });
      setMetrics(metricsData);

      // Load predictions for the first metric type if available
      if (metricsData.length > 0) {
        const metricName = metricsData[0].metric_name;
        loadPredictions(deviceId, metricName);
      }
    } catch (error) {
      console.error('Error loading metrics:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPredictions = async (deviceId: string, metricName: string) => {
    try {
      const predictionsData = await api.getPredictions(deviceId, metricName, 4);
      setPredictions(predictionsData);
    } catch (error) {
      console.error('Error loading predictions:', error);
      setPredictions([]);
    }
  };

  const handleDeviceSelect = (deviceId: string) => {
    setSelectedDevice(deviceId);
    loadMetrics(deviceId);
  };

  const handleGeneratePredictions = async () => {
    if (!selectedDevice || metrics.length === 0) return;

    try {
      const metricName = metrics[0].metric_name;
      await api.generatePredictions(selectedDevice, metricName, 4);
      loadPredictions(selectedDevice, metricName);
    } catch (error) {
      console.error('Error generating predictions:', error);
    }
  };

  const handleTrainModels = async () => {
    if (!selectedDevice || metrics.length === 0) return;

    try {
      const metricName = metrics[0].metric_name;
      await api.trainModels(selectedDevice, metricName);
      alert('Model training started successfully!');
    } catch (error) {
      console.error('Error training models:', error);
      alert('Error starting model training');
    }
  };

  // Group metrics by metric type
  const groupedMetrics = metrics.reduce((acc, metric) => {
    if (!acc[metric.metric_name]) {
      acc[metric.metric_name] = [];
    }
    acc[metric.metric_name].push(metric);
    return acc;
  }, {} as Record<string, NetworkMetric[]>);

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1 className="dashboard-title">Network Forecaster Dashboard</h1>
          <div className="connection-status">
            <div className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
            <span className="status-text">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </header>

      <main className="dashboard-main">
        <div className="dashboard-grid">
          {/* Device List Section */}
          <aside className="devices-section">
            <div className="section-header">
              <h2 className="section-title">Devices</h2>
              <span className="device-count">{devices.length} connected</span>
            </div>
            <div className="devices-list">
              {devices.map(device => (
                <DeviceCard
                  key={device.device_id}
                  device={device}
                  onClick={handleDeviceSelect}
                  isSelected={selectedDevice === device.device_id}
                />
              ))}
              {devices.length === 0 && (
                <div className="empty-state">
                  <p>No devices found</p>
                </div>
              )}
            </div>
          </aside>

          {/* Main Content Section */}
          <section className="content-section">
            {selectedDevice ? (
              <div className="device-details">
                <div className="device-header">
                  <div className="device-info">
                    <h2 className="device-name">Device: {selectedDevice}</h2>
                    <span className="device-status">Active</span>
                  </div>
                  <div className="action-buttons">
                    <button
                      onClick={handleGeneratePredictions}
                      disabled={loading || metrics.length === 0}
                      className="btn btn-primary"
                    >
                      Generate Predictions
                    </button>
                    <button
                      onClick={handleTrainModels}
                      disabled={loading || metrics.length === 0}
                      className="btn btn-secondary"
                    >
                      Train Models
                    </button>
                  </div>
                </div>

                {loading && (
                  <div className="loading-state">
                    <div className="spinner"></div>
                    <p>Loading metrics...</p>
                  </div>
                )}

                {!loading && metrics.length === 0 && (
                  <div className="empty-state">
                    <h3>No Data Available</h3>
                    <p>No metrics available for this device</p>
                  </div>
                )}

                {!loading && metrics.length > 0 && (
                  <div className="metrics-container">
                    <h3 className="metrics-title">Metrics & Predictions</h3>
                    <div className="metrics-grid">
                      {Object.entries(groupedMetrics).map(([metricName, metricData]) => (
                        <div key={metricName} className="metric-card">
                          <div className="metric-header">
                            <h4 className="metric-name">{metricName}</h4>
                          </div>
                          
                          <div className="chart-container">
                            <MetricChart
                              metrics={metricData}
                              predictions={predictions.filter(p => p.metric_name === metricName)}
                              title={`${metricName} Trends`}
                            />
                          </div>
                          
                          {/* Metric Statistics */}
                          <div className="metric-stats">
                            <div className="stat-item">
                              <span className="stat-label">Current</span>
                              <span className="stat-value">
                                {metricData[0]?.value.toFixed(2)} {metricData[0]?.unit}
                              </span>
                            </div>
                            <div className="stat-item">
                              <span className="stat-label">Average</span>
                              <span className="stat-value">
                                {(metricData.reduce((sum, m) => sum + m.value, 0) / metricData.length).toFixed(2)} {metricData[0]?.unit}
                              </span>
                            </div>
                            <div className="stat-item">
                              <span className="stat-label">Data Points</span>
                              <span className="stat-value">{metricData.length}</span>
                            </div>
                            {predictions.length > 0 && (
                              <div className="stat-item prediction">
                                <span className="stat-label">Next Prediction</span>
                                <span className="stat-value">
                                  {predictions[0]?.predicted_value.toFixed(2)} {metricData[0]?.unit}
                                </span>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="device-placeholder">
                <div className="placeholder-content">
                  <h3>Select a Device</h3>
                  <p>Choose a device from the list to view its metrics and predictions</p>
                </div>
              </div>
            )}
          </section>
        </div>
      </main>
    </div>
  );
};
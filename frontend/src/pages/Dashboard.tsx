import React, { useState, useEffect } from 'react';
import { api, DeviceStatus, NetworkMetric, Prediction } from '../services/api';
import { DeviceCard } from '../components/DeviceCard';
import { MetricChart } from '../components/MetricChart';
import { useWebSocket } from '../hooks/useWebSocket';

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
      // Reload predictions after generation
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
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>Network Forecaster Dashboard</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            backgroundColor: isConnected ? 'green' : 'red'
          }} />
          <span style={{ fontSize: '14px', color: '#666' }}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
        {/* Device List */}
        <div>
          <h2>Devices ({devices.length})</h2>
          <div style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {devices.map(device => (
              <DeviceCard
                key={device.device_id}
                device={device}
                onClick={handleDeviceSelect}
              />
            ))}
          </div>
        </div>

        {/* Device Details */}
        <div>
          {selectedDevice ? (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <h2>Device: {selectedDevice}</h2>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <button
                    onClick={handleGeneratePredictions}
                    disabled={loading || metrics.length === 0}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#007bff',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      opacity: loading ? 0.6 : 1
                    }}
                  >
                    Generate Predictions
                  </button>
                  <button
                    onClick={handleTrainModels}
                    disabled={loading || metrics.length === 0}
                    style={{
                      padding: '8px 16px',
                      backgroundColor: '#28a745',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: loading ? 'not-allowed' : 'pointer',
                      opacity: loading ? 0.6 : 1
                    }}
                  >
                    Train Models
                  </button>
                </div>
              </div>

              {loading && (
                <div style={{ textAlign: 'center', padding: '20px' }}>
                  <div>Loading metrics...</div>
                </div>
              )}

              {!loading && metrics.length === 0 && (
                <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                  No metrics available for this device
                </div>
              )}

              {!loading && metrics.length > 0 && (
                <div>
                  <h3>Metrics & Predictions</h3>
                  {Object.entries(groupedMetrics).map(([metricName, metricData]) => (
                    <div key={metricName} style={{ marginBottom: '30px' }}>
                      <div style={{
                        backgroundColor: '#f8f9fa',
                        padding: '20px',
                        borderRadius: '8px',
                        border: '1px solid #dee2e6'
                      }}>
                        <MetricChart
                          metrics={metricData}
                          predictions={predictions.filter(p => p.metric_name === metricName)}
                          title={`${metricName} - ${selectedDevice}`}
                        />
                      </div>
                      
                      {/* Metric Statistics */}
                      <div style={{ 
                        marginTop: '10px', 
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
                        gap: '10px' 
                      }}>
                        <div style={{ 
                          padding: '10px', 
                          backgroundColor: '#e3f2fd', 
                          borderRadius: '4px',
                          textAlign: 'center'
                        }}>
                          <div style={{ fontSize: '12px', color: '#666' }}>Current</div>
                          <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                            {metricData[0]?.value.toFixed(2)} {metricData[0]?.unit}
                          </div>
                        </div>
                        <div style={{ 
                          padding: '10px', 
                          backgroundColor: '#e8f5e8', 
                          borderRadius: '4px',
                          textAlign: 'center'
                        }}>
                          <div style={{ fontSize: '12px', color: '#666' }}>Average</div>
                          <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                            {(metricData.reduce((sum, m) => sum + m.value, 0) / metricData.length).toFixed(2)} {metricData[0]?.unit}
                          </div>
                        </div>
                        <div style={{ 
                          padding: '10px', 
                          backgroundColor: '#fff3e0', 
                          borderRadius: '4px',
                          textAlign: 'center'
                        }}>
                          <div style={{ fontSize: '12px', color: '#666' }}>Data Points</div>
                          <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                            {metricData.length}
                          </div>
                        </div>
                        {predictions.length > 0 && (
                          <div style={{ 
                            padding: '10px', 
                            backgroundColor: '#fce4ec', 
                            borderRadius: '4px',
                            textAlign: 'center'
                          }}>
                            <div style={{ fontSize: '12px', color: '#666' }}>Next Prediction</div>
                            <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
                              {predictions[0]?.predicted_value.toFixed(2)} {metricData[0]?.unit}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div style={{ 
              textAlign: 'center', 
              padding: '60px 20px', 
              color: '#666',
              backgroundColor: '#f8f9fa',
              borderRadius: '8px',
              border: '2px dashed #dee2e6'
            }}>
              <h3 style={{ margin: '0 0 10px 0' }}>Select a Device</h3>
              <p style={{ margin: 0 }}>Choose a device from the list to view its metrics and predictions</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
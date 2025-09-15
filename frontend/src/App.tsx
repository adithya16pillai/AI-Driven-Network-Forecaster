import React, { useState, useEffect } from 'react';
import './App.css';

interface NetworkMetrics {
  timestamp: string;
  bandwidth: number;
  latency: number;
  packetLoss: number;
  throughput: number;
}

interface ForecastData {
  predictedBandwidth: number[];
  predictedLatency: number[];
  timestamps: string[];
  accuracy: number;
}

function App() {
  const [networkData, setNetworkData] = useState<NetworkMetrics[]>([]);
  const [forecastData, setForecastData] = useState<ForecastData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      const newMetric: NetworkMetrics = {
        timestamp: new Date().toISOString(),
        bandwidth: Math.random() * 100 + 50,
        latency: Math.random() * 50 + 10,
        packetLoss: Math.random() * 5,
        throughput: Math.random() * 80 + 20
      };
      
      setNetworkData(prev => [...prev.slice(-19), newMetric]);
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  const generateForecast = async () => {
    setLoading(true);
    setTimeout(() => {
      const forecast: ForecastData = {
        predictedBandwidth: Array.from({length: 24}, () => Math.random() * 100 + 50),
        predictedLatency: Array.from({length: 24}, () => Math.random() * 50 + 10),
        timestamps: Array.from({length: 24}, (_, i) => 
          new Date(Date.now() + i * 3600000).toLocaleTimeString()
        ),
        accuracy: 85 + Math.random() * 10
      };
      setForecastData(forecast);
      setLoading(false);
    }, 2000);
  };

  const currentMetrics = networkData[networkData.length - 1];

  return (
    <div className="app">
      <header className="app-header">
        <h1>🌐 AI-Driven Network Forecaster</h1>
        <div className="connection-status">
          <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`}></span>
          {isConnected ? 'Connected' : 'Monitoring'}
        </div>
      </header>

      <main className="main-content">
        <section className="metrics-section">
          <h2>Real-time Network Metrics</h2>
          <div className="metrics-grid">
            <div className="metric-card">
              <h3>Bandwidth</h3>
              <div className="metric-value">
                {currentMetrics?.bandwidth.toFixed(1) || '0'} Mbps
              </div>
              <div className="metric-trend">↗️ +2.3%</div>
            </div>
            
            <div className="metric-card">
              <h3>Latency</h3>
              <div className="metric-value">
                {currentMetrics?.latency.toFixed(1) || '0'} ms
              </div>
              <div className="metric-trend">↘️ -1.8%</div>
            </div>
            
            <div className="metric-card">
              <h3>Packet Loss</h3>
              <div className="metric-value">
                {currentMetrics?.packetLoss.toFixed(2) || '0'}%
              </div>
              <div className="metric-trend">↘️ -0.5%</div>
            </div>
            
            <div className="metric-card">
              <h3>Throughput</h3>
              <div className="metric-value">
                {currentMetrics?.throughput.toFixed(1) || '0'} Mbps
              </div>
              <div className="metric-trend">↗️ +4.2%</div>
            </div>
          </div>
        </section>

        <section className="chart-section">
          <h2>Network Performance Trends</h2>
          <div className="chart-container">
            <div className="chart-placeholder">
              <h4>Bandwidth Over Time</h4>
              <div className="simple-chart">
                {networkData.slice(-10).map((data, index) => (
                  <div 
                    key={index} 
                    className="chart-bar" 
                    style={{height: `${data.bandwidth}%`}}
                  ></div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="forecast-section">
          <div className="forecast-header">
            <h2>AI Network Forecasting</h2>
            <button 
              className="forecast-btn" 
              onClick={generateForecast}
              disabled={loading}
            >
              {loading ? '🔄 Generating...' : '🤖 Generate 24h Forecast'}
            </button>
          </div>

          {forecastData && (
            <div className="forecast-results">
              <div className="forecast-accuracy">
                <h3>Model Accuracy: {forecastData.accuracy.toFixed(1)}%</h3>
              </div>
              
              <div className="forecast-charts">
                <div className="forecast-chart">
                  <h4>Predicted Bandwidth (Next 24h)</h4>
                  <div className="forecast-visualization">
                    {forecastData.predictedBandwidth.slice(0, 12).map((value, index) => (
                      <div key={index} className="forecast-point">
                        <div 
                          className="forecast-bar" 
                          style={{height: `${value}%`}}
                        ></div>
                        <span className="forecast-time">
                          {forecastData.timestamps[index].slice(0, 5)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="forecast-insights">
                <h4>📊 AI Insights</h4>
                <ul>
                  <li>🔴 Peak traffic expected at 2:00 PM - 4:00 PM</li>
                  <li>🟡 Moderate latency increase predicted around 6:00 PM</li>
                  <li>🟢 Optimal performance window: 10:00 PM - 6:00 AM</li>
                  <li>⚠️ Potential congestion at 85% bandwidth utilization</li>
                </ul>
              </div>
            </div>
          )}
        </section>

        <section className="control-section">
          <h2>Network Controls</h2>
          <div className="controls-grid">
            <button className="control-btn primary">🔄 Refresh Data</button>
            <button className="control-btn secondary">📊 Export Report</button>
            <button className="control-btn secondary">⚙️ Configure Alerts</button>
            <button className="control-btn secondary">📈 Historical Analysis</button>
          </div>
        </section>
      </main>

      <footer className="app-footer">
        <p>AI-Driven Network Forecaster | Last Updated: {new Date().toLocaleString()}</p>
      </footer>
    </div>
  );
}

export default App;

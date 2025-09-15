import React from 'react';
import { DeviceStatus } from '../services/api';
import './DeviceCard.css';

interface DeviceCardProps {
  device: DeviceStatus;
  onClick: (deviceId: string) => void;
  isSelected: boolean;
}

export const DeviceCard: React.FC<DeviceCardProps> = ({ device, onClick, isSelected }) => {
  const handleClick = () => {
    onClick(device.device_id);
  };

  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'online':
      case 'active':
        return 'status-online';
      case 'offline':
        return 'status-offline';
      case 'warning':
        return 'status-warning';
      default:
        return 'status-unknown';
    }
  };

  // Ensure we have valid device data
  if (!device || !device.device_id) {
    return null;
  }

  return (
    <div 
      className={`device-card ${isSelected ? 'selected' : ''}`}
      onClick={handleClick}
    >
      <div className="device-card-header">
        <div className="device-info">
          <h4 className="device-id">{device.device_id}</h4>
          <span className="device-type">
            {device.device_type || 'Network Device'}
          </span>
        </div>
        <div className={`device-status-badge ${getStatusColor(device.status || 'unknown')}`}>
          {device.status || 'Unknown'}
        </div>
      </div>
      
      <div className="device-card-body">
        <div className="device-metrics">
          <div className="metric-item">
            <span className="metric-label">IP Address</span>
            <span className="metric-value">{device.ip_address || 'N/A'}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Location</span>
            <span className="metric-value">{device.location || 'Unknown'}</span>
          </div>
          <div className="metric-item">
            <span className="metric-label">Last Seen</span>
            <span className="metric-value">
              {device.last_seen 
                ? new Date(device.last_seen).toLocaleTimeString() 
                : 'Never'
              }
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
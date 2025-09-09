import React from 'react';
import { DeviceStatus } from '../services/api';

interface DeviceCardProps {
  device: DeviceStatus;
  onClick: (deviceId: string) => void;
}

export const DeviceCard: React.FC<DeviceCardProps> = ({ device, onClick }) => {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'green';
      case 'offline':
        return 'red';
      default:
        return 'gray';
    }
  };

  return (
    <div 
      className="device-card"
      onClick={() => onClick(device.device_id)}
      style={{
        border: '1px solid #ddd',
        borderRadius: '8px',
        padding: '16px',
        margin: '8px',
        cursor: 'pointer',
        backgroundColor: '#fff',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>{device.device_id}</h3>
        <div 
          style={{
            width: '12px',
            height: '12px',
            borderRadius: '50%',
            backgroundColor: getStatusColor(device.status)
          }}
        />
      </div>
      <p style={{ margin: '8px 0 0 0', color: '#666' }}>
        Last seen: {new Date(device.last_seen).toLocaleString()}
      </p>
      <p style={{ margin: '4px 0 0 0', color: '#666' }}>
        Metrics: {device.metrics_count}
      </p>
    </div>
  );
};
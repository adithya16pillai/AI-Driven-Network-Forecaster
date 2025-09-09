import { useEffect, useState, useRef } from 'react';
import io, { Socket } from 'socket.io-client';

const WS_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws';

interface MetricUpdate {
  type: string;
  device_id: string;
  metric_name: string;
  value: number;
  timestamp: string;
}

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(false);
  const [latestData, setLatestData] = useState<MetricUpdate[]>([]);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    // Create WebSocket connection
    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLatestData(data);
      } catch (error) {
        console.error('Error parsing WebSocket message:', error);
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    };

    ws.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    // Cleanup on component unmount
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []);

  return { isConnected, latestData };
};
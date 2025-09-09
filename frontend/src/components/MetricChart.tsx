import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { NetworkMetric, Prediction } from '../services/api';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

interface MetricChartProps {
  metrics: NetworkMetric[];
  predictions?: Prediction[];
  title: string;
}

export const MetricChart: React.FC<MetricChartProps> = ({
  metrics,
  predictions,
  title
}) => {
  const chartData = {
    labels: [
      ...metrics.map(m => new Date(m.timestamp).toLocaleTimeString()),
      ...(predictions || []).map(p => new Date(p.predicted_timestamp).toLocaleTimeString())
    ],
    datasets: [
      {
        label: 'Actual',
        data: metrics.map(m => m.value),
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.2)',
        fill: false,
      },
      ...(predictions ? [{
        label: 'Predicted',
        data: [
          ...Array(metrics.length).fill(null),
          ...predictions.map(p => p.predicted_value)
        ],
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        borderDash: [5, 5],
        fill: false,
      }] : []),
      ...(predictions ? [{
        label: 'Confidence Interval',
        data: [
          ...Array(metrics.length).fill(null),
          ...predictions.map(p => p.confidence_interval_upper || p.predicted_value)
        ],
        borderColor: 'rgba(255, 99, 132, 0.3)',
        backgroundColor: 'rgba(255, 99, 132, 0.1)',
        fill: '+1',
      }] : [])
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top' as const,
      },
      title: {
        display: true,
        text: title,
      },
    },
    scales: {
      y: {
        beginAtZero: true,
      },
    },
  };

  return <Line data={chartData} options={options} />;
};
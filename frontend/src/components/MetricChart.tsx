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
import './MetricChart.css'; // Add this import

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
  predictions = [],
  title
}) => {
  // Handle empty data
  if (!metrics || metrics.length === 0) {
    return (
      <div className="chart-placeholder">
        <p>No data available for {title}</p>
      </div>
    );
  }

  // Sort metrics by timestamp
  const sortedMetrics = [...metrics].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  // Sort predictions by timestamp
  const sortedPredictions = [...predictions].sort((a, b) => 
    new Date(a.prediction_timestamp).getTime() - new Date(b.prediction_timestamp).getTime()
  );

  // Create labels combining actual and predicted timestamps
  const actualLabels = sortedMetrics.map(m => 
    new Date(m.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );
  
  const predictionLabels = sortedPredictions.map(p => 
    new Date(p.prediction_timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  );

  const allLabels = [...actualLabels, ...predictionLabels];

  // Create datasets
  const datasets: any[] = [
    {
      label: 'Actual Values',
      data: [
        ...sortedMetrics.map(m => m.value),
        ...Array(sortedPredictions.length).fill(null)
      ],
      borderColor: 'rgb(59, 130, 246)',
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderWidth: 2,
      pointRadius: 3,
      pointHoverRadius: 5,
      fill: false,
      tension: 0.1,
    }
  ];

  // Add predictions if available
  if (sortedPredictions.length > 0) {
    datasets.push({
      label: 'Predictions',
      data: [
        ...Array(sortedMetrics.length).fill(null),
        ...sortedPredictions.map(p => p.predicted_value)
      ],
      borderColor: 'rgb(239, 68, 68)',
      backgroundColor: 'rgba(239, 68, 68, 0.1)',
      borderWidth: 2,
      borderDash: [5, 5],
      pointRadius: 3,
      pointHoverRadius: 5,
      fill: false,
      tension: 0.1,
    });

    // Add confidence interval if available
    const hasConfidence = sortedPredictions.some(p => p.confidence !== undefined);
    if (hasConfidence) {
      const confidenceUpper = sortedPredictions.map(p => 
        p.predicted_value + (p.confidence || 0) * 0.1
      );
      const confidenceLower = sortedPredictions.map(p => 
        p.predicted_value - (p.confidence || 0) * 0.1
      );

      datasets.push({
        label: 'Confidence Upper',
        data: [
          ...Array(sortedMetrics.length).fill(null),
          ...confidenceUpper
        ],
        borderColor: 'rgba(239, 68, 68, 0.3)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderWidth: 1,
        pointRadius: 0,
        fill: false,
        tension: 0.1,
      });

      datasets.push({
        label: 'Confidence Lower',
        data: [
          ...Array(sortedMetrics.length).fill(null),
          ...confidenceLower
        ],
        borderColor: 'rgba(239, 68, 68, 0.3)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderWidth: 1,
        pointRadius: 0,
        fill: '-1',
        tension: 0.1,
      });
    }
  }

  const chartData = {
    labels: allLabels,
    datasets: datasets,
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top' as const,
        labels: {
          filter: (legendItem: any) => {
            // Hide confidence interval lines from legend
            return !legendItem.text.includes('Confidence');
          },
        },
      },
      title: {
        display: true,
        text: title,
        font: {
          size: 14,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          title: (context: any) => {
            return context[0].label;
          },
          label: (context: any) => {
            const label = context.dataset.label || '';
            const value = context.parsed.y;
            const unit = sortedMetrics[0]?.unit || '';
            return `${label}: ${value?.toFixed(2)} ${unit}`;
          },
        },
      },
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time',
        },
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
      y: {
        display: true,
        title: {
          display: true,
          text: `${title} (${sortedMetrics[0]?.unit || ''})`,
        },
        beginAtZero: false,
        grid: {
          display: true,
          color: 'rgba(0, 0, 0, 0.1)',
        },
      },
    },
    elements: {
      point: {
        hoverBackgroundColor: 'white',
        hoverBorderWidth: 2,
      },
    },
  };

  return (
    <div className="metric-chart-container">
      <Line data={chartData} options={options} />
    </div>
  );
};
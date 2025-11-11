import { useEffect, useRef } from 'react';
import type { FC } from 'react';
import { Chart, registerables } from 'chart.js';
import { SpendingResult } from '@app-types/spending';

Chart.register(...registerables);

interface ChartSelectorProps {
  features: { key: string; label: string }[];
  chartTypes: { key: string; label: string }[];
  selectedFeature: string;
  selectedChartType: string;
  onFeatureChange: (feature: string) => void;
  onChartTypeChange: (chartType: string) => void;
  data: SpendingResult[];
}

const ChartSelector: FC<ChartSelectorProps> = ({
  features,
  chartTypes,
  selectedFeature,
  selectedChartType,
  onFeatureChange,
  onChartTypeChange,
  data
}) => {
  const chartRef = useRef<HTMLCanvasElement>(null);
  const chartInstance = useRef<Chart | null>(null);

  useEffect(() => {
    if (chartInstance.current) {
      chartInstance.current.destroy();
    }
    createChart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedFeature, selectedChartType, data]);

  const processData = () => {
    if (selectedFeature === 'award_amount') {
      const ranges = [
        { label: 'Under $1M', min: 0, max: 1000000 },
        { label: '$1M - $5M', min: 1000000, max: 5000000 },
        { label: '$5M - $20M', min: 5000000, max: 20000000 },
        { label: 'Over $20M', min: 20000000, max: Infinity }
      ];
      
      const counts = ranges.map(range => 
        data.filter(item => item.award_amount >= range.min && item.award_amount < range.max).length
      );
      
      return {
        labels: ranges.map(r => r.label),
        datasets: [{
          data: counts,
          backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0']
        }]
      };
    } else {
      const groupedData = data.reduce((acc, item) => {
        const key = item[selectedFeature as keyof SpendingResult] as string;
        acc[key] = (acc[key] || 0) + 1;
        return acc;
      }, {} as Record<string, number>);
      
      return {
        labels: Object.keys(groupedData),
        datasets: [{
          data: Object.values(groupedData),
          backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40']
        }]
      };
    }
  };

  const createChart = () => {
    if (!chartRef.current) return;
    
    const chartData = processData();
    
    chartInstance.current = new Chart(chartRef.current, {
      type: selectedChartType as any,
      data: chartData,
      options: {
        responsive: true,
        plugins: {
          legend: {
            position: 'bottom'
          },
          title: {
            display: true,
            text: `${features.find(f => f.key === selectedFeature)?.label} Distribution`
          }
        }
      }
    });
  };

  return (
    <div className="chart-selector">
      <div className="controls">
        <div className="control-group">
          <label>Data Feature:</label>
          <select value={selectedFeature} onChange={(e) => onFeatureChange(e.target.value)}>
            {features.map(feature => (
              <option key={feature.key} value={feature.key}>
                {feature.label}
              </option>
            ))}
          </select>
        </div>
        
        <div className="control-group">
          <label>Chart Type:</label>
          <select value={selectedChartType} onChange={(e) => onChartTypeChange(e.target.value)}>
            {chartTypes.map(type => (
              <option key={type.key} value={type.key}>
                {type.label}
              </option>
            ))}
          </select>
        </div>
      </div>
      
      <div className="chart-container">
        <canvas ref={chartRef}></canvas>
      </div>
    </div>
  );
};

export default ChartSelector;


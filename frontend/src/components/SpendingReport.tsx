import React, { useState, useEffect } from 'react';
import { SpendingData, SpendingResult } from '../types/spending';
import DataTable from './DataTable';
import ChartSelector from './ChartSelector';
import SummaryPanel from './SummaryPanel';
import './SpendingReport.css';

interface SpendingReportProps {
  data: SpendingData;
}

const SpendingReport: React.FC<SpendingReportProps> = ({ data }) => {
  const [selectedFeature, setSelectedFeature] = useState<string>('award_amount');
  const [chartType, setChartType] = useState<string>('pie');
  const [summary, setSummary] = useState<string>('');

  const features = [
    { key: 'award_amount', label: 'Award Amount' },
    { key: 'awarding_agency', label: 'Awarding Agency' },
    { key: 'recipient_name', label: 'Recipient' },
    { key: 'place_of_performance_zip5', label: 'Location (ZIP)' }
  ];

  const chartTypes = [
    { key: 'pie', label: 'Pie Chart' },
    { key: 'bar', label: 'Bar Chart' },
    { key: 'line', label: 'Line Chart' }
  ];

  useEffect(() => {
    generateSummary();
  }, [data]);

  const generateSummary = async () => {
    try {
      const response = await fetch('/api/generate-summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: data.results })
      });
      const result = await response.json();
      setSummary(result.summary);
    } catch (error) {
      setSummary('Unable to generate summary at this time.');
    }
  };

  return (
    <div className="spending-report">
      <h2>Federal Spending Report</h2>
      
      <SummaryPanel summary={summary} />
      
      <div className="report-content">
        <div className="table-section">
          <h3>Spending Data</h3>
          <DataTable data={data.results} />
        </div>
        
        <div className="chart-section">
          <ChartSelector
            features={features}
            chartTypes={chartTypes}
            selectedFeature={selectedFeature}
            selectedChartType={chartType}
            onFeatureChange={setSelectedFeature}
            onChartTypeChange={setChartType}
            data={data.results}
          />
        </div>
      </div>
    </div>
  );
};

export default SpendingReport;
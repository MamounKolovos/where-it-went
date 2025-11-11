import { useState, useEffect } from "react";
import type { FC } from 'react';
import { SpendingData } from "@app-types/spending";
import SummaryPanel from "@components/spending_report_component/SummaryPanel";
import DataTable from "@components/spending_report_component/DataTable";
import ChartSelector from "@components/spending_report_component/ChartSelector";
import "./SpendingReport.css";

interface SpendingReportPopupProps {
  data: SpendingData;
  onClose: () => void;
}

const SpendingReport: FC<SpendingReportPopupProps> = ({ data, onClose }) => {
  const [activeTab, setActiveTab] = useState<"summary" | "charts" | "table">("summary");
  const [isVisible, setIsVisible] = useState(true);
  const [summary, setSummary] = useState<string>("");
  const [isLoadingSummary, setIsLoadingSummary] = useState(false);

  const [selectedFeature, setSelectedFeature] = useState<string>("award_amount");
  const [selectedChartType, setSelectedChartType] = useState<string>("pie");

  const handleFeatureChange = (feature: string) => {
    setSelectedFeature(feature);
  };

  const handleChartTypeChange = (chartType: string) => {
    setSelectedChartType(chartType);
  };

  // Fetch summary when the component is rendered
  useEffect(() => {
    const fetchSummary = async () => {
      setIsLoadingSummary(true);
      try {
        const response = await fetch("/api/generate-summary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ data: data.results }),
        });
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        setSummary(result.summary || "No summary available");
      } catch (error) {
        console.error("Error fetching summary:", error);
        setSummary("Unable to generate summary at this time. Please try again later.");
      } finally {
        setIsLoadingSummary(false);
      }
    };

    if (data.results && data.results.length > 0) {
      fetchSummary();
    } else {
      console.log('[SpendingReport] No results to generate summary for');
      setSummary('No federal spending records found for this location.');
    }
  }, [data.results]); // Trigger only when results change

  const handleClose = () => {
    setIsVisible(false);
    onClose();
  };

  if (!isVisible) return null;

  return (
    <div className="popup-overlay">
      <div className="popup-container">
        <div className="popup-header">
          <h2>Spending Report</h2>
          <button className="close-button" onClick={handleClose}>
            &times;
          </button>
        </div>
        <div className="popup-tabs">
          <button
            className={activeTab === "summary" ? "active-tab" : ""}
            onClick={() => setActiveTab("summary")}
          >
            Summary
          </button>
          <button
            className={activeTab === "charts" ? "active-tab" : ""}
            onClick={() => setActiveTab("charts")}
          >
            Charts
          </button>
          <button
            className={activeTab === "table" ? "active-tab" : ""}
            onClick={() => setActiveTab("table")}
          >
            Table
          </button>
        </div>
        <div className="popup-content">
          {activeTab === "summary" && (
            <SummaryPanel summary={summary} isLoading={isLoadingSummary} />
          )}
          {activeTab === "charts" && (
            <ChartSelector
              features={[
                { key: "award_amount", label: "Award Amount" },
                { key: "awarding_agency", label: "Awarding Agency" },
                { key: "recipient_name", label: "Recipient" },
                { key: "place_of_performance_zip5", label: "Location (ZIP)" },
              ]}
              chartTypes={[
                { key: "pie", label: "Pie Chart" },
                { key: "bar", label: "Bar Chart" },
                { key: "line", label: "Line Chart" },
              ]}
              selectedFeature={selectedFeature}
              selectedChartType={selectedChartType}
              onFeatureChange={handleFeatureChange}
              onChartTypeChange={handleChartTypeChange}
              data={data.results}
            />
          )}
          {activeTab === "table" && <DataTable data={data.results} />}
        </div>
      </div>
    </div>
  );
};

export default SpendingReport;


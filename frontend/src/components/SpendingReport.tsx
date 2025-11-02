import React, { useState, useEffect } from "react";
import "./SpendingReport.css";
import SummaryPanel from "./SummaryPanel";
import DataTable from "./DataTable";
import ChartSelector from "./ChartSelector";
import { SpendingData } from "../types/spending";

interface SpendingReportPopupProps {
  data: SpendingData;
  onClose: () => void;
}

const SpendingReport: React.FC<SpendingReportPopupProps> = ({ data, onClose }) => {
  const [activeTab, setActiveTab] = useState<"summary" | "charts" | "table">("summary");
  const [isVisible, setIsVisible] = useState(true);
  const [summary, setSummary] = useState<string>("");

  const [selectedFeature, setSelectedFeature] = useState<string>("award_amount");
  const [selectedChartType, setSelectedChartType] = useState<string>("pie");

  const handleFeatureChange = (feature: string) => {
    setSelectedFeature(feature);
  };

  const handleChartTypeChange = (chartType: string) => {
    setSelectedChartType(chartType);
  };

  // Calculate the total amount
  const totalAmount = data.results.reduce((sum, item) => sum + (item.award_amount || 0), 0);

  // Fetch summary when the component is rendered
  useEffect(() => {
    const fetchSummary = async () => {
      try {
        const response = await fetch("/api/generate-summary", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ data: data.results, totalAmount: totalAmount }),
        });
        const result = await response.json();
        setSummary(result.summary);
      } catch (error) {
        console.error("Error fetching summary:", error);
        setSummary("Unable to generate summary at this time.");
      }
    };

    fetchSummary();
  }, [data, totalAmount]); // Trigger only when data or totalAmount changes

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
          {activeTab === "summary" && <SummaryPanel summary={summary} />}
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
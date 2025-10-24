import React from 'react';

interface SummaryPanelProps {
  summary: string;
}

const SummaryPanel: React.FC<SummaryPanelProps> = ({ summary }) => {
  return (
    <div className="summary-panel">
      <h3>AI-Generated Summary</h3>
      <div 
        className="summary-content"
        dangerouslySetInnerHTML={{ __html: summary || 'Generating summary...' }}
      />
    </div>
  );
};

export default SummaryPanel;
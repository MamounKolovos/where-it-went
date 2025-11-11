import type { FC } from 'react';
import ReactMarkdown from 'react-markdown';

interface SummaryPanelProps {
  summary: string;
  isLoading?: boolean;
}

const SummaryPanel: FC<SummaryPanelProps> = ({ summary, isLoading = false }) => {
  return (
    <div className="summary-panel">
      <h3>AI-Generated Summary</h3>
      {isLoading ? (
        <div className="summary-loading">
          <div className="spinner"></div>
          <p>Generating summary with AI...</p>
        </div>
      ) : (
        <div className="summary-content">
          <ReactMarkdown>{summary || 'No summary available'}</ReactMarkdown>
        </div>
      )}
    </div>
  );
};

export default SummaryPanel;


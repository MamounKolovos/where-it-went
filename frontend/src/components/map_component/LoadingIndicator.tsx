import type { FC } from 'react';

const LoadingIndicator: FC = () => {
  return (
    <div className="loading-indicator">
      <div className="loading-spinner"></div>
      <p>Loading...</p>
    </div>
  );
};

export default LoadingIndicator;


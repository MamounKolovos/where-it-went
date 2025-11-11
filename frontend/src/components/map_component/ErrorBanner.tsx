import type { FC } from 'react';

interface ErrorBannerProps {
  message: string;
  onClose: () => void;
}

const ErrorBanner: FC<ErrorBannerProps> = ({ message, onClose }) => {
  return (
    <div className="error-banner">
      <span>{message}</span>
      <button onClick={onClose}>&times;</button>
    </div>
  );
};

export default ErrorBanner;


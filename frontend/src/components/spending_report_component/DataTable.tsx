import type { FC } from 'react';
import { SpendingResult } from '@app-types/spending';

interface DataTableProps {
  data: SpendingResult[];
}

const DataTable: FC<DataTableProps> = ({ data }) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const truncateText = (text: string, maxLength: number = 50) => {
    return text.length > maxLength ? `${text.substring(0, maxLength)}...` : text;
  };

  if (!data || data.length === 0) {
    return (
      <div className="data-table-empty">
        <p>No data available</p>
      </div>
    );
  }

  return (
    <div className="data-table-container">
      <table className="data-table">
        <thead>
          <tr>
            <th>Award ID</th>
            <th>Amount</th>
            <th>Agency</th>
            <th>Recipient</th>
            <th>Description</th>
            <th>Start Date</th>
            <th>End Date</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item, index) => (
            <tr key={item.award_id || index}>
              <td>{item.award_id || 'N/A'}</td>
              <td className="currency">{formatCurrency(item.award_amount)}</td>
              <td>{item.awarding_agency || 'N/A'}</td>
              <td>{item.recipient_name || 'N/A'}</td>
              <td title={item.description}>
                {truncateText(item.description || 'N/A')}
              </td>
              <td>{item.start_date || 'N/A'}</td>
              <td>{item.end_date || 'N/A'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;


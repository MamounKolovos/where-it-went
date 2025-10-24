import React from 'react';
import { SpendingResult } from '../types/spending';

interface DataTableProps {
  data: SpendingResult[];
}

const DataTable: React.FC<DataTableProps> = ({ data }) => {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount);
  };

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
            <tr key={index}>
              <td>{item.award_id}</td>
              <td>{formatCurrency(item.award_amount)}</td>
              <td>{item.awarding_agency}</td>
              <td>{item.recipient_name}</td>
              <td title={item.description}>
                {item.description.length > 50 
                  ? `${item.description.substring(0, 50)}...` 
                  : item.description}
              </td>
              <td>{item.start_date}</td>
              <td>{item.end_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
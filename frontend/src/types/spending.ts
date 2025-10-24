export interface SpendingResult {
  award_amount: number;
  award_id: string;
  awarding_agency: string;
  description: string;
  end_date: string;
  place_of_performance_zip5: string;
  recipient_name: string;
  start_date: string;
}

export interface SpendingData {
  messages: string[];
  page_metadata: {
    hasNext: boolean;
    last_record_sort_value: string;
    last_record_unique_id: number;
    page: number;
  };
  results: SpendingResult[];
}
export interface DashboardKpis {
  total_production_mt: string | number;
  total_obr_mcum: string | number;
  total_documents: number;
  active_conflicts: number;
  entity_accuracy_rate: string;
  citation_coverage_rate: string;
}

export interface ProductionSeriesItem {
  subsidiary: string;
  actual: number;
  target: number;
  obr: number;
}

export interface DashboardChartsResponse {
  production_data: ProductionSeriesItem[];
  fiscal_year: string;
}

export interface ValidationFeedItem {
  id: number;
  mine_name: string;
  subsidiary: string;
  metric_name: string;
  fiscal_year: string;
  reported_value: number;
  calculated_value: number;
  standard_unit: string;
  percentage_difference: number;
  validation_status: 'VALIDATED' | 'WARNING_ARITHMETIC' | 'CONFLICT_DETECTED' | 'UNVERIFIED';
  message: string;
  document_id: number;
  filename: string;
}

export interface WordCloudItem {
  word: string;
  weight: number;
  category: string;
}

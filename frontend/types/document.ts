export type DocumentStatus = 'PENDING' | 'PROCESSING' | 'PARSED' | 'INDEXED' | 'FAILED';
export type FileType = 'PDF' | 'DOCX' | 'XLSX' | 'CSV' | 'PNG' | 'JPG' | 'JPEG' | 'TIF' | 'TIFF';
export type MetricValidationStatus = 'VALIDATED' | 'WARNING_ARITHMETIC' | 'CONFLICT_DETECTED' | 'UNVERIFIED';

export interface DocumentItem {
  id: number;
  filename: string;
  file_path: string;
  file_hash: string;
  file_type: FileType;
  file_size_bytes: number;
  subsidiary: string | null;
  fiscal_year: string | null;
  status: DocumentStatus;
  processing_status?: string | null;
  source_type?: string | null;
  source_url?: string | null;
  source_organization?: string | null;
  title?: string | null;
  reporting_period?: string | null;
  extraction_confidence?: number | null;
  processing_warnings?: string[] | null;
  total_pages: number;
  uploaded_by: number | null;
  error_message: string | null;
  created_at: string;
}

export interface DocumentListParams {
  status_filter?: string;
  subsidiary_filter?: string;
  skip?: number;
  limit?: number;
}

export interface DocumentListResponse {
  total: number;
  items: DocumentItem[];
}

export interface DocumentPageItem {
  page_number: number;
  text_snippet: string;
}

export interface DocumentPagesResponse {
  document_id: number;
  filename: string;
  total_pages: number;
  pages: DocumentPageItem[];
}

export interface ExtractedMetricItem {
  id: number;
  mine_name: string;
  metric_name: string;
  numeric_value: number;
  unit: string;
  standard_value: number;
  standard_unit: string;
  fiscal_year: string;
  validation_status: MetricValidationStatus;
  raw_snippet: string;
  confidence_score?: number | null;
  page_number?: number | null;
}

export interface DocumentLineageResponse {
  document_id: number;
  filename: string;
  subsidiary: string | null;
  fiscal_year: string | null;
  file_hash: string;
  metrics: ExtractedMetricItem[];
}

export interface DocumentTableItem {
  id: number;
  page_number: number;
  table_number: number;
  title: string | null;
  headers: unknown[];
  rows: unknown[];
  bounding_box: unknown;
  extraction_confidence: number | null;
  extraction_method: string;
  sheet_name: string | null;
  cells: unknown[];
  merged_cells?: unknown[];
  formulas?: Record<string, unknown>;
  displayed_values?: Record<string, unknown>;
  warnings: string[];
}

export interface DocumentTablesResponse {
  document_id: number;
  filename: string;
  tables: DocumentTableItem[];
}

export interface DocumentWarningsResponse {
  document_id: number;
  processing_status: string | null;
  warnings: string[];
  error: string | null;
}

export interface DocumentHistoryEvent {
  action: string;
  details: string | null;
  created_at: string;
}

export interface DocumentHistoryResponse {
  document_id: number;
  events: DocumentHistoryEvent[];
}

export interface UploadDocumentParams {
  file: File;
  subsidiary?: string;
  fiscal_year?: string;
}

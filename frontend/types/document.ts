export type DocumentStatus = 'PENDING' | 'PROCESSING' | 'PARSED' | 'INDEXED' | 'FAILED';
export type FileType = 'PDF' | 'DOCX' | 'XLSX' | 'CSV';
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

export interface UploadDocumentParams {
  file: File;
  subsidiary?: string;
  fiscal_year?: string;
}

import { apiClient } from './client';

export interface ParliamentaryBriefingRequest {
  question_text: string;
  fiscal_year?: string;
  subsidiary_filter?: string;
  question_type?: string;
}

export interface SubsidiaryMetricItem {
  mine_name: string;
  subsidiary: string;
  metric_name: string;
  numeric_value: number;
  unit: string;
  standard_value: number;
  standard_unit: string;
  fiscal_year: string;
  page_number?: number;
  document_filename?: string;
}

export interface FlaggedDiscrepancyItem {
  entity: string;
  metric_name: string;
  fiscal_year: string;
  doc_a_filename: string;
  doc_a_value: number;
  doc_b_filename: string;
  doc_b_value: number;
  unit: string;
  variance_percentage: number;
  status: string;
  is_seeded_demo: boolean;
  provenance_label: string;
}

export interface BriefingEvidenceItem {
  chunk_id?: number | string;
  document_id: number;
  document_name: string;
  page_number: number;
  chunk_index: number;
  text_snippet: string;
  rrf_score: number;
  subsidiary: string;
}

export interface ParliamentaryBriefingResponse {
  question: string;
  question_type: string;
  fiscal_year: string;
  selected_scope: string;
  executive_summary: string;
  key_findings: string[];
  subsidiary_metrics: SubsidiaryMetricItem[];
  discrepancies: FlaggedDiscrepancyItem[];
  evidence: BriefingEvidenceItem[];
  confidence: number;
  confidence_rating: 'HIGH' | 'MEDIUM' | 'LOW' | 'DEGRADED' | 'INSUFFICIENT_EVIDENCE';
  has_sufficient_evidence: boolean;
  limitations: string[];
  generated_at: string;
}

export async function generateBriefing(
  payload: ParliamentaryBriefingRequest
): Promise<ParliamentaryBriefingResponse> {
  const response = await apiClient.post<ParliamentaryBriefingResponse>('/parliamentary/briefing', payload);
  return response.data;
}

export async function exportBriefingPdf(
  briefing: ParliamentaryBriefingResponse
): Promise<Blob> {
  const response = await apiClient.post('/parliamentary/export-pdf', briefing, {
    responseType: 'blob',
  });
  return response.data;
}

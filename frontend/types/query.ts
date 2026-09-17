export interface CitationTag {
  document_name: string;
  page_number: number;
  citation_tag: string;
}

export interface EvidenceChunk {
  chunk_id?: string;
  document_id: number;
  filename: string;
  page_number: number;
  chunk_index: number;
  text: string;
  vector_score?: number;
  keyword_score?: number;
  rrf_score?: number;
}

export interface QueryAskResponse {
  query: string;
  answer: string;
  citations: CitationTag[];
  evidence_chunks: EvidenceChunk[];
  provider: string;
  degraded_mode: boolean;
}

import type { ConflictEvidence } from '@/lib/api/validationApi';

/**
 * Build the existing Document Workspace link from persisted provenance.
 * DocumentPage and ExtractedMetric page numbers are both human-facing,
 * one-based values, so no additional offset is applied here.
 */
export function buildConflictEvidenceUrl(
  documentId: number | null | undefined,
  evidence?: ConflictEvidence | null,
): string | null {
  if (documentId == null) return null;

  const params = new URLSearchParams();
  if (evidence?.page_number != null && Number.isInteger(evidence.page_number) && evidence.page_number >= 1) {
    params.set('page', String(evidence.page_number));
  }
  if (evidence?.metric_id != null) {
    params.set('evidence', String(evidence.metric_id));
  }
  const query = params.toString();
  return `/documents/${documentId}${query ? `?${query}` : ''}`;
}

export function evidenceLinkLabel(evidence?: ConflictEvidence | null): string {
  if (evidence?.page_number != null) return `View Evidence · Page ${evidence.page_number}`;
  return 'View Document';
}


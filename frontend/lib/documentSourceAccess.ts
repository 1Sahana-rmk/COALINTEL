import type { DocumentItem } from '../types/document';
import { buildOfficialSourceUrl } from './officialSourceLink';

export type DocumentSourceAction =
  | { kind: 'official'; url: string }
  | { kind: 'stored' }
  | { kind: 'unavailable' };

export interface DocumentSourceActions {
  officialUrl: string | null;
  storedArtifactAvailable: boolean;
}

/**
 * Resolve the UI action from persisted provenance only.  A local file path is
 * only used as an indicator that the backend may have a stored copy; the
 * browser never receives or opens that path directly.
 */
export function getDocumentSourceAction(
  document: Pick<DocumentItem, 'source_type' | 'source_url' | 'file_type' | 'file_path'>,
  pageNumber?: number | null,
): DocumentSourceAction {
  const actions = getDocumentSourceActions(document, pageNumber);
  if (actions.officialUrl) return { kind: 'official', url: actions.officialUrl };
  if (actions.storedArtifactAvailable) return { kind: 'stored' };
  return { kind: 'unavailable' };
}

/**
 * Official-source access and stored-artifact access are intentionally separate
 * operations. The persisted path is never exposed to the browser; it only
 * indicates that the authenticated download endpoint can be offered.
 */
export function getDocumentSourceActions(
  document: Pick<DocumentItem, 'source_type' | 'source_url' | 'file_type' | 'file_path'>,
  pageNumber?: number | null,
): DocumentSourceActions {
  return {
    officialUrl: buildOfficialSourceUrl(document, pageNumber),
    storedArtifactAvailable: Boolean(document.file_path?.trim()),
  };
}

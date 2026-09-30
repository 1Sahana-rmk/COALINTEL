import type { DocumentItem, FileType } from '../types/document';

type OfficialSourceLinkDocument = Pick<DocumentItem, 'source_type' | 'source_url'> & {
  file_type?: FileType | null;
};

const VERIFIED_OFFICIAL_SOURCE_TYPES = new Set(['OFFICIAL', 'OFFICIAL_WEBSITE']);

/**
 * Return the persisted official source URL only when the document carries an
 * official provenance type and the value is a safe absolute HTTP(S) URL.
 * Filenames are intentionally never used to construct this link.
 */
export function buildOfficialSourceUrl(
  document: OfficialSourceLinkDocument,
  pageNumber?: number | null,
): string | null {
  if (!VERIFIED_OFFICIAL_SOURCE_TYPES.has((document.source_type || '').trim().toUpperCase())) {
    return null;
  }

  const rawUrl = document.source_url?.trim();
  if (!rawUrl) return null;

  let url: URL;
  try {
    url = new URL(rawUrl);
  } catch {
    return null;
  }

  if (!['http:', 'https:'].includes(url.protocol) || !url.hostname || url.username || url.password) {
    return null;
  }

  // PDF viewers commonly support #page=N. This is best-effort and does not
  // alter the persisted source URL or affect COALINTEL's local page reader.
  if (
    document.file_type?.toUpperCase() === 'PDF' &&
    pageNumber != null &&
    Number.isInteger(pageNumber) &&
    pageNumber >= 1
  ) {
    url.hash = `page=${pageNumber}`;
  }

  return url.toString();
}

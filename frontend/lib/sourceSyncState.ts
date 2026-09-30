export const OFFICIAL_SOURCE_POLL_INTERVAL_MS = 3000;

export interface OfficialSourceSyncSnapshot {
  status?: string | null;
  last_error?: string | null;
}

export const isOfficialSourceSyncing = (
  source?: OfficialSourceSyncSnapshot | null,
  trackingAcceptedJob = false,
): boolean => trackingAcceptedJob || source?.status === 'SYNCING';

export const isTerminalOfficialSourceStatus = (status?: string | null): boolean =>
  Boolean(status) && status !== 'SYNCING';

export const getOfficialSourceSyncError = (
  source?: OfficialSourceSyncSnapshot | null,
): string | null => {
  if (!source || (source.status !== 'ERROR' && source.status !== 'PARTIAL')) return null;
  return source.last_error || `Ministry synchronization ended with status ${source.status}.`;
};

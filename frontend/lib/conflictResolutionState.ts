export function isResolvedConflict(status?: string | null): boolean {
  return (status || '').toUpperCase() === 'RESOLVED';
}

export function canSubmitConflictResolution(status: string | undefined, isLoading: boolean): boolean {
  return !isLoading && !isResolvedConflict(status);
}

export function formatConflictDocumentIdentifier(
  databaseId?: number | null,
  sourceId?: string | null,
): string {
  if (databaseId !== null && databaseId !== undefined) return `ID #${databaseId}`;
  if (sourceId) return `Source ${sourceId}`;
  return 'Identifier unavailable';
}

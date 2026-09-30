export function dashboardKpiSubtitle(
  value: string | number,
  period: string | null | undefined,
  isApiConnected: boolean,
  connectedFallback: string,
  noDataLabel: string,
): string {
  if (!isApiConnected) return connectedFallback;
  if (typeof value === 'string' && value.trim().toUpperCase() === 'N/A') return noDataLabel;
  return period?.trim() || connectedFallback;
}

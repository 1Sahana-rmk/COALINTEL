export interface ConflictPageValidation {
  valid: boolean;
  page?: number;
  error?: string;
}

export function getTotalConflictPages(total: number, pageSize: number): number {
  if (!Number.isFinite(total) || !Number.isFinite(pageSize) || pageSize <= 0) return 1;
  return Math.max(1, Math.ceil(Math.max(0, total) / pageSize));
}

export function getConflictPageSkip(pageNumber: number, pageSize: number): number {
  return (pageNumber - 1) * pageSize;
}

export function validateConflictPageInput(rawValue: string, totalPages: number): ConflictPageValidation {
  const raw = rawValue.trim();
  if (!/^[1-9]\d*$/.test(raw)) {
    return { valid: false, error: `Page must be a positive integer between 1 and ${totalPages.toLocaleString('en-IN')}.` };
  }

  const page = Number(raw);
  if (!Number.isSafeInteger(page) || page < 1 || page > totalPages) {
    return { valid: false, error: `Page must be between 1 and ${totalPages.toLocaleString('en-IN')}.` };
  }

  return { valid: true, page };
}

export function formatConflictCount(value: number): string {
  return value.toLocaleString('en-IN');
}

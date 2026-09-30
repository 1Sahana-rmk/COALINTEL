export function getParliamentaryErrorMessage(error: unknown): string {
  const candidate = (error ?? {}) as {
    code?: string;
    message?: string;
    response?: { data?: { detail?: unknown } };
  };

  const detail = candidate.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    if (/semantic|embedding|vector/i.test(detail)) {
      return 'Semantic evidence retrieval is currently unavailable.';
    }
    return detail;
  }

  if (
    candidate.code === 'ECONNABORTED' ||
    candidate.code === 'ETIMEDOUT' ||
    /timeout/i.test(candidate.message || '')
  ) {
    return 'Briefing generation could not complete within the allowed time.';
  }

  return 'Briefing generation failed. Please try again.';
}

export function getParliamentaryExportErrorMessage(error: unknown): string {
  const candidate = (error ?? {}) as {
    code?: string;
    message?: string;
    response?: { data?: { detail?: unknown } };
  };

  if (
    candidate.code === 'ECONNABORTED' ||
    candidate.code === 'ETIMEDOUT' ||
    /timeout/i.test(candidate.message || '')
  ) {
    return 'Briefing PDF export could not complete within the allowed time.';
  }

  const detail = candidate.response?.data?.detail;
  if (typeof detail === 'string' && detail.trim()) {
    return detail;
  }

  return 'Briefing PDF export failed. Please try again.';
}

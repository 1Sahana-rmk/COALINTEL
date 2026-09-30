'use client';

import { useEffect, useState } from 'react';
import { UserRole } from '@/types/auth';

const USER_ROLES: readonly UserRole[] = ['Admin', 'Analyst', 'Reviewer', 'Viewer'];

function isUserRole(value: unknown): value is UserRole {
  return typeof value === 'string' && USER_ROLES.includes(value as UserRole);
}

/**
 * Reads the role returned by the existing authenticated login flow.
 * This is presentation-only gating; backend dependencies remain authoritative.
 */
export function useCurrentUserRole(): UserRole | null {
  const [role, setRole] = useState<UserRole | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('coalintel_user');
      const parsed = stored ? JSON.parse(stored) : null;
      setRole(isUserRole(parsed?.role) ? parsed.role : null);
    } catch {
      setRole(null);
    }
  }, []);

  return role;
}

export function canIngestDocuments(role: UserRole | null): boolean {
  return role === 'Admin' || role === 'Analyst';
}

export function canSyncOfficialSources(role: UserRole | null): boolean {
  return role === 'Admin';
}

export function canGenerateReports(role: UserRole | null): boolean {
  return role === 'Admin' || role === 'Analyst';
}

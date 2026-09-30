import { UserRole } from '@/types/auth';

export type DemoLoginRole = 'admin' | 'analyst' | 'reviewer' | 'viewer';

export interface DemoAccount {
  role: UserRole;
  username: string;
  password: string;
  label: string;
}

/**
 * Development/demo accounts seeded by backend/database_seed.py.
 * These shortcuts still authenticate through the real login endpoint.
 */
export const DEMO_ACCOUNTS: Record<DemoLoginRole, DemoAccount> = {
  admin: { role: 'Admin', username: 'admin', password: 'Admin@123', label: 'Admin Login' },
  analyst: { role: 'Analyst', username: 'analyst', password: 'Analyst@123', label: 'Analyst Login' },
  reviewer: { role: 'Reviewer', username: 'reviewer', password: 'Reviewer@123', label: 'Reviewer Login' },
  viewer: { role: 'Viewer', username: 'auditor', password: 'Auditor@123', label: 'Viewer Login' },
};

'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { AuditLogsTable } from '@/components/audit/AuditLogsTable';
import { auditApi } from '@/lib/api/auditApi';
import { ShieldAlert } from 'lucide-react';

export default function AuditPage() {
  const {
    data: logs = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['audit-logs'],
    queryFn: () => auditApi.getAuditLogs(),
    staleTime: 60000,
  });

  const isForbidden = (error as any)?.response?.status === 403;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="System Security & Audit Trail Ledger"
        description="Immutable audit trail tracking user authentication events, document ingestions, conflict resolutions, and report approvals."
        breadcrumbs={[{ label: 'Audit Logs' }]}
        badge={<Badge variant="amber">Restricted: Admin</Badge>}
      />

      {/* 403 Forbidden RBAC Notice */}
      {isForbidden ? (
        <div className="p-8 rounded-lg bg-[#1C2226] border border-[#30383D] text-center space-y-3 max-w-xl mx-auto my-8">
          <div className="p-3 rounded-lg bg-[#D6A23A]/10 text-[#D6A23A] border border-[#D6A23A]/30 w-fit mx-auto">
            <ShieldAlert className="h-8 w-8" />
          </div>
          <h3 className="text-base font-bold text-[#E8ECEB]">RBAC Authorization Notice</h3>
          <p className="text-xs text-[#9BA5A8]">
            System security audit logs are restricted to users with <code className="text-[#C58B3A] font-semibold">Admin</code> role authorization.
          </p>
        </div>
      ) : isError ? (
        <ErrorState message={error instanceof Error ? error.message : 'Failed to fetch audit log ledger.'} />
      ) : (
        /* Main Audit Logs Data Table */
        <AuditLogsTable logs={logs} loading={isLoading} />
      )}
    </div>
  );
}

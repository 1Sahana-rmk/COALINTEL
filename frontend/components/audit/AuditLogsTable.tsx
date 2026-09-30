'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { History, User } from 'lucide-react';
import { AuditLogItem } from '@/lib/api/auditApi';

interface AuditLogsTableProps {
  logs: AuditLogItem[];
  loading?: boolean;
}

export const AuditLogsTable: React.FC<AuditLogsTableProps> = ({
  logs,
  loading = false,
}) => {
  return (
    <Card className="border-[#30383D] shadow-sm bg-[#1C2226]">
      <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D]">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold text-[#E8ECEB] flex items-center gap-2">
            <History className="h-4 w-4 text-[#C58B3A]" />
            <span>Immutable System Audit Trail Ledger</span>
          </CardTitle>
          <Badge variant="amber" size="sm">
            {logs.length} Logged Events
          </Badge>
        </div>
        <CardDescription className="text-xs text-[#9BA5A8]">
          Chronological record of user authentication events, document ingestions, conflict resolutions, and report approvals.
        </CardDescription>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#30383D] bg-[#151A1D] text-[11px] font-mono text-[#9BA5A8] uppercase tracking-wider">
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4">Authorized User</th>
                <th className="py-3 px-4">Action Event</th>
                <th className="py-3 px-4">Event Details & Provenance</th>
                <th className="py-3 px-4 text-right">IP Address</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#30383D] text-xs font-mono">
              {loading ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-3.5 px-4"><div className="h-4 w-28 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4"><div className="h-4 w-20 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4"><div className="h-4 w-24 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4"><div className="h-4 w-48 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4 text-right"><div className="h-4 w-20 bg-[#242C30] rounded ml-auto" /></td>
                  </tr>
                ))
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-[#9BA5A8] text-xs">
                    No security audit trail events recorded.
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-[#242C30]/50 transition-colors">
                    <td className="py-3.5 px-4 text-[#9BA5A8] text-[11px]">
                      {log.timestamp}
                    </td>

                    <td className="py-3.5 px-4 text-[#E8ECEB] font-semibold font-sans">
                      <span className="flex items-center gap-1.5">
                        <User className="h-3.5 w-3.5 text-[#C58B3A] shrink-0" />
                        {log.user}
                      </span>
                    </td>

                    <td className="py-3.5 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] bg-[#C58B3A]/15 border border-[#C58B3A]/30 text-[#C58B3A] font-bold uppercase">
                        {log.action}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-[#9BA5A8] font-sans max-w-md truncate" title={log.details}>
                      {log.details}
                    </td>

                    <td className="py-3.5 px-4 text-right text-[#9BA5A8] font-mono text-[11px]">
                      {log.ip}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
};

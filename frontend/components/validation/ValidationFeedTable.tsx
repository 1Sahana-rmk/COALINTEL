'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ShieldCheck } from 'lucide-react';
import { ValidationItem } from '@/lib/api/validationApi';

interface ValidationFeedTableProps {
  items: ValidationItem[];
  loading?: boolean;
}

export const ValidationFeedTable: React.FC<ValidationFeedTableProps> = ({
  items,
  loading = false,
}) => {
  return (
    <Card className="border-[#30383D] shadow-sm bg-[#1C2226]">
      <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D]">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-[#E8ECEB] flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[#4F8A62]" />
            <span>Deterministic Arithmetic Validation Feed</span>
          </CardTitle>
          <Badge variant="amber" size="sm">
            {items.length} Validation Scans
          </Badge>
        </div>
        <CardDescription className="text-xs text-[#9BA5A8]">
          Deterministic arithmetic checks detecting calculation discrepancies ($&gt; 5\%$) and unit conversion anomalies.
        </CardDescription>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#30383D] bg-[#151A1D] text-[11px] font-mono text-[#9BA5A8] uppercase tracking-wider">
                <th className="py-3 px-4">Mine Entity</th>
                <th className="py-3 px-4">Metric Type</th>
                <th className="py-3 px-4">Discrepancy Details</th>
                <th className="py-3 px-4">Confidence</th>
                <th className="py-3 px-4 text-right">Validation Status</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#30383D] text-xs font-mono">
              {loading ? (
                Array.from({ length: 4 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-3.5 px-4"><div className="h-4 w-32 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4"><div className="h-4 w-28 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4"><div className="h-4 w-48 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4"><div className="h-4 w-16 bg-[#242C30] rounded" /></td>
                    <td className="py-3.5 px-4 text-right"><div className="h-6 w-20 bg-[#242C30] rounded ml-auto" /></td>
                  </tr>
                ))
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-[#9BA5A8] text-xs">
                    No arithmetic validation warnings detected across ingested document set.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="hover:bg-[#242C30]/50 transition-colors">
                    <td className="py-3.5 px-4 font-sans font-bold text-[#E8ECEB]">
                      {item.mine_name}
                      <span className="block text-[10px] text-[#9BA5A8] font-mono font-normal">
                        {item.subsidiary}
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-[#E8ECEB]">
                      {item.metric_name}
                    </td>

                    <td className="py-3.5 px-4 text-[#E8ECEB] font-sans">
                      <div className="space-y-0.5">
                        <span className="font-bold text-[#D6A23A] font-mono block">
                          Discrepancy: {item.discrepancy}
                        </span>
                        <span className="text-[11px] text-[#9BA5A8] block">{item.details}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-[#4F8A62] font-bold">
                      {(item.confidence || 0.95).toFixed(2)}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <Badge variant={item.status === 'VALIDATED' ? 'success' : 'warning'}>
                        {item.status || 'WARNING'}
                      </Badge>
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

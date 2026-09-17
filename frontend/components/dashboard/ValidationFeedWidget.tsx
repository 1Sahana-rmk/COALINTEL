'use client';

import React from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ShieldCheck, ChevronRight, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { ValidationFeedItem } from '@/types/dashboard';

interface ValidationFeedWidgetProps {
  items?: ValidationFeedItem[];
  loading?: boolean;
}

const defaultFeed: ValidationFeedItem[] = [
  {
    id: 1,
    mine_name: 'Rajmahal OpenCast',
    subsidiary: 'ECL',
    metric_name: 'Coal Production',
    fiscal_year: '2023-24',
    reported_value: 4.25,
    calculated_value: 4.25,
    standard_unit: 'MT',
    percentage_difference: 1.68,
    validation_status: 'CONFLICT_DETECTED',
    message: 'Cross-document discrepancy > 1% detected between Annual Report (4.25 MT) and Audit disclosure (4.18 MT).',
    document_id: 1,
    filename: 'ECL_Annual_Report_2023-24.pdf',
  },
  {
    id: 2,
    mine_name: 'Gevra OC',
    subsidiary: 'SECL',
    metric_name: 'Overburden Removal',
    fiscal_year: '2023-24',
    reported_value: 310.5,
    calculated_value: 310.5,
    standard_unit: 'M.Cu.M',
    percentage_difference: 5.2,
    validation_status: 'WARNING_ARITHMETIC',
    message: 'Child mine sum total discrepancy exceeds 5% arithmetic threshold.',
    document_id: 3,
    filename: 'SECL_Gevra_Monthly_Despatch.csv',
  },
  {
    id: 3,
    mine_name: 'Samaleswari OC',
    subsidiary: 'MCL',
    metric_name: 'Coal Production',
    fiscal_year: '2023-24',
    reported_value: 193.3,
    calculated_value: 193.3,
    standard_unit: 'MT',
    percentage_difference: 0.0,
    validation_status: 'VALIDATED',
    message: 'Deterministic unit conversion (MT) and arithmetic verified with 99.5% confidence score.',
    document_id: 4,
    filename: 'MCL_Samaleswari_Performance.xlsx',
  },
];

export const ValidationFeedWidget: React.FC<ValidationFeedWidgetProps> = ({
  items = defaultFeed,
  loading = false,
}) => {
  const displayItems = items && items.length > 0 ? items : defaultFeed;

  return (
    <Card className="col-span-1 bg-[#1C2226] border-[#30383D] flex flex-col justify-between">
      <div>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>
              <ShieldCheck className="h-5 w-5 text-[#4F8A62]" />
              <span>Validation & Quality Feed</span>
            </CardTitle>
            <Link
              href="/validation"
              className="text-xs text-[#C58B3A] hover:text-[#D6A052] font-mono flex items-center gap-1 transition-colors"
            >
              View Feed <ChevronRight className="h-3 w-3" />
            </Link>
          </div>
          <CardDescription>
            Arithmetic tolerance monitoring (&gt;5%) and multi-source variance checks (&gt;1%).
          </CardDescription>
        </CardHeader>

        <CardContent>
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-20 w-full animate-pulse rounded-lg bg-[#242C30]" />
              ))}
            </div>
          ) : displayItems.length === 0 ? (
            <div className="p-6 text-center text-xs text-[#9BA5A8] border border-dashed border-[#30383D] rounded-lg">
              No recent validation alerts found for active scope.
            </div>
          ) : (
            <div className="space-y-3">
              {displayItems?.slice(0, 3).map((item) => {
                const isConflict = item.validation_status === 'CONFLICT_DETECTED';
                const isWarning = item.validation_status === 'WARNING_ARITHMETIC';

                return (
                  <div
                    key={item.id}
                    className="p-3 rounded-lg bg-[#242C30] border border-[#30383D] hover:border-[#C58B3A]/40 transition-all duration-150 space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-[#E8ECEB] truncate flex items-center gap-1.5">
                        {isConflict ? (
                          <AlertTriangle className="h-3.5 w-3.5 text-[#C94B45] shrink-0" />
                        ) : isWarning ? (
                          <AlertTriangle className="h-3.5 w-3.5 text-[#D6A23A] shrink-0" />
                        ) : (
                          <CheckCircle2 className="h-3.5 w-3.5 text-[#4F8A62] shrink-0" />
                        )}
                        {item.mine_name}
                      </span>
                      <Badge
                        variant={isConflict ? 'danger' : isWarning ? 'warning' : 'success'}
                        size="sm"
                      >
                        {item.validation_status.replace(/_/g, ' ')}
                      </Badge>
                    </div>

                    <p className="text-[11px] text-[#9BA5A8] line-clamp-2 leading-relaxed">
                      {item.message}
                    </p>

                    <div className="flex items-center justify-between text-[10px] font-mono text-[#9BA5A8] pt-1 border-t border-[#30383D]/40">
                      <span>{item.subsidiary} • {item.metric_name}</span>
                      <span className="text-[#C58B3A] font-semibold">{item.reported_value} {item.standard_unit}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </div>

      <div className="px-5 pb-4 pt-1">
        <Link
          href="/conflicts"
          className="w-full block text-center py-2 px-3 rounded-lg bg-[#151A1D] hover:bg-[#242C30] border border-[#30383D] text-[#E8ECEB] hover:text-[#C58B3A] text-xs font-mono transition-colors"
        >
          Inspect Conflicts Matrix →
        </Link>
      </div>
    </Card>
  );
};

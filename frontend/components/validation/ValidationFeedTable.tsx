'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { ShieldCheck } from 'lucide-react';
import { ValidationItem } from '@/lib/api/validationApi';
import { VALIDATION_FEED_DESCRIPTION } from '@/lib/validationFeedPresentation';
import { useLanguage } from '@/context/LanguageContext';

interface ValidationFeedTableProps {
  items: ValidationItem[];
  loading?: boolean;
}

export const ValidationFeedTable: React.FC<ValidationFeedTableProps> = ({
  items,
  loading = false,
}) => {
  const { t } = useLanguage();
  const validatedCount = items.filter((item) => item.validation_status === 'VALIDATED').length;
  const warningCount = items.filter((item) => item.validation_status === 'WARNING_ARITHMETIC').length;
  const unverifiedCount = items.filter((item) => item.validation_status === 'UNVERIFIED').length;
  return (
    <Card className="border-[#30383D] shadow-sm bg-[#1C2226]">
      <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D]">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold text-[#E8ECEB] flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-[#4F8A62]" />
            <span>{t('validation.title')}</span>
          </CardTitle>
          <div className="flex flex-wrap items-center justify-end gap-1.5">
            <Badge variant="amber" size="sm">
              {items.length} {t('validation.metricsChecked')}
            </Badge>
            <span className="text-[10px] text-[#4F8A62]">{t('validation.validated')}: {validatedCount}</span>
            <span className="text-[10px] text-[#D6A23A]">{t('validation.warnings')}: {warningCount}</span>
            <span className="text-[10px] text-[#9BA5A8]">{t('validation.unverified')}: {unverifiedCount}</span>
          </div>
        </div>
        <CardDescription className="text-xs text-[#9BA5A8]">
          {t('validation.description', VALIDATION_FEED_DESCRIPTION)}
        </CardDescription>
      </CardHeader>

      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#30383D] bg-[#151A1D] text-[11px] font-mono text-[#9BA5A8] uppercase tracking-wider">
                <th className="py-3 px-4">{t('validation.mineEntity')}</th>
                <th className="py-3 px-4">{t('validation.metricType')}</th>
                <th className="py-3 px-4">{t('validation.discrepancyDetails')}</th>
                <th className="py-3 px-4">{t('validation.extractionConfidence')}</th>
                <th className="py-3 px-4 text-right">{t('validation.validationStatus')}</th>
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
                    {t('validation.noWarnings')}
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
                          Discrepancy:{' '}
                          {item.discrepancy_available && item.percentage_difference != null
                            ? `${item.percentage_difference.toFixed(2)}%`
                            : t('validation.unavailable')}
                        </span>
                        <span className="text-[11px] text-[#9BA5A8] block">{item.message}</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 text-[#4F8A62] font-bold">
                      {item.extraction_confidence == null
                        ? t('validation.unavailable')
                        : item.extraction_confidence.toFixed(2)}
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <Badge variant={item.validation_status === 'VALIDATED' ? 'success' : 'warning'}>
                        {item.validation_status || 'UNVERIFIED'}
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

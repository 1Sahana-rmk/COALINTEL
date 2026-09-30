'use client';

import React from 'react';
import { Filter, RefreshCw } from 'lucide-react';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { CIL_SUBSIDIARIES, FISCAL_YEARS } from '@/lib/constants';
import { useLanguage } from '@/context/LanguageContext';

export interface FiscalYearOption {
  value: string;
  label: string;
}

interface FilterBarProps {
  selectedSubsidiary: string;
  onSubsidiaryChange: (sub: string) => void;
  selectedFiscalYear: string;
  onFiscalYearChange: (year: string) => void;
  onRefresh?: () => void;
  isLoading?: boolean;
  fiscalYearOptions?: readonly FiscalYearOption[];
}

export const FilterBar: React.FC<FilterBarProps> = ({
  selectedSubsidiary,
  onSubsidiaryChange,
  selectedFiscalYear,
  onFiscalYearChange,
  onRefresh,
  isLoading = false,
  fiscalYearOptions = FISCAL_YEARS,
}) => {
  const { t } = useLanguage();
  return (
    <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 p-4 rounded-lg bg-[#1C2226] border border-[#30383D] shadow-sm">
      <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#E8ECEB]">
        <Filter className="h-4 w-4 text-[#C58B3A]" />
        <span>{t('dashboard.operationalScope')}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 flex-1 max-w-2xl">
        <Select
          value={selectedSubsidiary}
          onChange={(e) => onSubsidiaryChange(e.target.value)}
          options={CIL_SUBSIDIARIES}
          className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] text-xs font-medium py-2"
        />

        <Select
          value={selectedFiscalYear}
          onChange={(e) => onFiscalYearChange(e.target.value)}
          options={fiscalYearOptions}
          className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] text-xs font-medium py-2"
        />

        {onRefresh && (
          <Button
            variant="secondary"
            size="sm"
            onClick={onRefresh}
            isLoading={isLoading}
            leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            className="text-xs"
          >
            {t('dashboard.applyFilters')}
          </Button>
        )}
      </div>
    </div>
  );
};

'use client';

import React from 'react';
import { StatCard } from '@/components/ui/StatCard';
import { Pickaxe, Layers, FileText, AlertTriangle, CheckCircle2, ShieldCheck } from 'lucide-react';
import { DashboardKpis } from '@/types/dashboard';
import { useLanguage } from '@/context/LanguageContext';
import { dashboardKpiSubtitle } from '@/lib/dashboardKpiPresentation';

interface KpiGridProps {
  kpis?: DashboardKpis | null;
  loading?: boolean;
  isApiConnected?: boolean;
}

const formatKpiMetric = (
  val: string | number | undefined | null,
  isApiConnected: boolean
): string => {
  if (val === undefined || val === null || val === '') {
    return isApiConnected ? '0.00' : '—';
  }

  // Handle number type directly
  if (typeof val === 'number') {
    if (isNaN(val)) return isApiConnected ? '0.00' : '—';
    return val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Handle string: strip comma thousand-separators and parse
  const cleanStr = String(val).replace(/,/g, '').trim();
  const num = parseFloat(cleanStr);
  if (isNaN(num)) {
    return String(val);
  }

  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export const KpiGrid: React.FC<KpiGridProps> = ({ kpis, loading = false, isApiConnected = false }) => {
  const { t } = useLanguage();
  const productionValue = formatKpiMetric(kpis?.total_production_mt, isApiConnected);
  const obrValue = formatKpiMetric(kpis?.total_obr_mcum, isApiConnected);

  const conflictsCount =
    typeof kpis?.active_conflicts === 'number' && !isNaN(kpis.active_conflicts)
      ? kpis.active_conflicts
      : typeof kpis?.active_conflicts === 'string' && !isNaN(parseInt(kpis.active_conflicts, 10))
      ? parseInt(kpis.active_conflicts, 10)
      : 0;

  const docsCount =
    typeof kpis?.total_documents === 'number' && !isNaN(kpis.total_documents)
      ? kpis.total_documents
      : typeof kpis?.total_documents === 'string' && !isNaN(parseInt(kpis.total_documents, 10))
      ? parseInt(kpis.total_documents, 10)
      : 0;

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
      {/* Primary KPI: Coal Production */}
      <StatCard
        title={t('dashboard.coalProduction')}
        value={productionValue}
        unit="MT"
        icon={<Pickaxe className="h-4 w-4" />}
        subtitle={dashboardKpiSubtitle(
          productionValue,
          kpis?.total_production_period,
          isApiConnected,
          t('dashboard.productionScopeTotal'),
          t('dashboard.noDataAvailable'),
        )}
        variant="primary"
        loading={loading}
      />

      {/* Primary KPI: Overburden Removal */}
      <StatCard
        title={t('dashboard.overburdenRemoval')}
        value={obrValue}
        unit="M.Cu.M"
        icon={<Layers className="h-4 w-4" />}
        subtitle={dashboardKpiSubtitle(
          obrValue,
          kpis?.total_obr_period,
          isApiConnected,
          t('dashboard.totalMineVolume'),
          t('dashboard.noDataAvailable'),
        )}
        variant="primary"
        loading={loading}
      />

      {/* Actionable Alert KPI: Active Conflicts */}
      <StatCard
        title={t('dashboard.activeConflicts')}
        value={conflictsCount}
        unit={t('dashboard.open')}
        icon={<AlertTriangle className="h-4 w-4" />}
        subtitle={t('dashboard.discrepancyFlagged')}
        trend={conflictsCount > 0 ? { value: `${conflictsCount} ${t('dashboard.reviewNeeded')}`, isPositive: false } : undefined}
        variant={conflictsCount > 0 ? 'danger' : 'default'}
        loading={loading}
      />

      {/* Secondary Supporting Metric: Ingested Documents */}
      <StatCard
        title={t('dashboard.ingestedDocuments')}
        value={docsCount}
        unit={t('dashboard.docs')}
        icon={<FileText className="h-4 w-4 text-[#54788A]" />}
        subtitle={t('dashboard.parsedVectorChunked')}
        variant="default"
        loading={loading}
      />

      {/* Secondary Supporting Metric: Entity Accuracy */}
      <StatCard
        title={t('dashboard.entityAccuracy')}
        value={kpis?.entity_accuracy_rate || (isApiConnected ? 'N/A' : '—')}
        icon={<CheckCircle2 className="h-4 w-4 text-[#4F8A62]" />}
        subtitle={t('dashboard.regexNlpNormalization')}
        variant="default"
        loading={loading}
      />

      {/* Secondary Supporting Metric: Citation Coverage */}
      <StatCard
        title={t('dashboard.citationCoverage')}
        value={kpis?.citation_coverage_rate || (isApiConnected ? 'N/A' : '—')}
        icon={<ShieldCheck className="h-4 w-4 text-[#4F8A62]" />}
        subtitle={t('dashboard.ragGroundingVerified')}
        variant="default"
        loading={loading}
      />
    </div>
  );
};

'use client';

import React from 'react';
import { StatCard } from '@/components/ui/StatCard';
import { Pickaxe, Layers, FileText, AlertTriangle, CheckCircle2, ShieldCheck } from 'lucide-react';
import { DashboardKpis } from '@/types/dashboard';

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
    return isApiConnected ? '0.00' : '—';
  }

  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
};

export const KpiGrid: React.FC<KpiGridProps> = ({ kpis, loading = false, isApiConnected = false }) => {
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
        title="Coal Production"
        value={productionValue}
        unit="MT"
        icon={<Pickaxe className="h-4 w-4" />}
        subtitle={isApiConnected ? 'Verified Extracted Metric' : 'Production Scope Total'}
        variant="primary"
        loading={loading}
      />

      {/* Primary KPI: Overburden Removal */}
      <StatCard
        title="Overburden Removal"
        value={obrValue}
        unit="M.Cu.M"
        icon={<Layers className="h-4 w-4" />}
        subtitle={isApiConnected ? 'Normalized Stripping Volume' : 'Total Mine Volume'}
        variant="primary"
        loading={loading}
      />

      {/* Actionable Alert KPI: Active Conflicts */}
      <StatCard
        title="Active Conflicts"
        value={conflictsCount}
        unit="Open"
        icon={<AlertTriangle className="h-4 w-4" />}
        subtitle="Discrepancy > 1% Flagged"
        trend={conflictsCount > 0 ? { value: `${conflictsCount} Review Needed`, isPositive: false } : undefined}
        variant={conflictsCount > 0 ? 'danger' : 'default'}
        loading={loading}
      />

      {/* Secondary Supporting Metric: Ingested Documents */}
      <StatCard
        title="Ingested Documents"
        value={docsCount}
        unit="Docs"
        icon={<FileText className="h-4 w-4 text-[#54788A]" />}
        subtitle="Parsed & Vector Chunked"
        variant="default"
        loading={loading}
      />

      {/* Secondary Supporting Metric: Entity Accuracy */}
      <StatCard
        title="Entity Accuracy"
        value={kpis?.entity_accuracy_rate || (isApiConnected ? 'N/A' : '—')}
        icon={<CheckCircle2 className="h-4 w-4 text-[#4F8A62]" />}
        subtitle="Regex & NLP Normalization"
        variant="default"
        loading={loading}
      />

      {/* Secondary Supporting Metric: Citation Coverage */}
      <StatCard
        title="Citation Coverage"
        value={kpis?.citation_coverage_rate || (isApiConnected ? 'N/A' : '—')}
        icon={<ShieldCheck className="h-4 w-4 text-[#4F8A62]" />}
        subtitle="RAG Grounding Verified"
        variant="default"
        loading={loading}
      />
    </div>
  );
};

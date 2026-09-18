'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  GitCompare,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Eye,
  Filter,
  RefreshCw,
  Info,
  Building2,
  Calendar,
  Layers,
  ExternalLink,
  ShieldCheck,
  CheckSquare,
  Square,
  X,
  FileSpreadsheet,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { useScope } from '@/context/ScopeContext';
import { formatStandardValue } from '@/lib/utils/cn';
import {
  fetchComparisonMatrix,
  fetchComparisonOptions,
  ComparisonMatrixResponse,
  ComparisonMatrixItem,
  ComparisonSourceItem,
  DocumentMetadataItem,
  ComparisonConflictItem,
} from '@/lib/api/comparisonApi';

export default function ComparisonPage() {
  const { selectedSubsidiary, selectedFiscalYear } = useScope();

  // Control state
  const [metricName, setMetricName] = useState<string>('Coal Production');
  const [fiscalYearFilter, setFiscalYearFilter] = useState<string>(selectedFiscalYear || '2024-25');
  const [entityFilter, setEntityFilter] = useState<string>('');

  // Selector options & documents
  const [availableMetrics, setAvailableMetrics] = useState<string[]>([
    'Coal Production',
    'Coal Dispatch',
    'Production Target',
    'Production Achievement',
    'Overburden Removal',
    'Star Rating',
  ]);
  const [availableFiscalYears, setAvailableFiscalYears] = useState<string[]>([
    '2026-27',
    '2025-26',
    '2024-25',
    '2023-24',
    '2022-23',
  ]);
  const [documentsCatalog, setDocumentsCatalog] = useState<DocumentMetadataItem[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  // Data & loading state
  const [data, setData] = useState<ComparisonMatrixResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Source Traceability Modal state (Section 12)
  const [inspectSource, setInspectSource] = useState<ComparisonSourceItem | null>(null);

  // 1. Fetch dynamic options and available documents on mount
  useEffect(() => {
    async function loadOptions() {
      try {
        const opts = await fetchComparisonOptions();
        if (opts.metrics && opts.metrics.length > 0) setAvailableMetrics(opts.metrics);
        if (opts.fiscal_years && opts.fiscal_years.length > 0) setAvailableFiscalYears(opts.fiscal_years);
        if (opts.documents && opts.documents.length > 0) {
          setDocumentsCatalog(opts.documents);
          // Default to all documents selected
          setSelectedDocIds(opts.documents.map((d) => d.id));
        }
      } catch (err) {
        console.warn('Could not load dynamic comparison options:', err);
      }
    }
    loadOptions();
  }, []);

  // 2. Fetch comparison matrix when filters change
  const loadMatrix = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      // Log developer diagnostics (without logging secrets or tokens)
      console.log('[COALINTEL Comparison Audit] Executing matrix request:', {
        metric: metricName,
        fiscal_year: fiscalYearFilter,
        subsidiary: selectedSubsidiary,
        entity_filter: entityFilter || 'ALL',
        selected_documents_count: selectedDocIds.length,
      });

      const res = await fetchComparisonMatrix({
        metric_name: metricName,
        fiscal_year: fiscalYearFilter,
        entity_filter: entityFilter || undefined,
        subsidiary_filter: selectedSubsidiary,
        document_ids: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      });
      setData(res);
      if (res.available_documents && res.available_documents.length > 0 && documentsCatalog.length === 0) {
        setDocumentsCatalog(res.available_documents);
        setSelectedDocIds(res.available_documents.map((d) => d.id));
      }
    } catch (err: any) {
      console.error('[COALINTEL Comparison Error] API request failed:', {
        error_name: err?.name,
        error_message: err?.message,
        status: err?.response?.status,
        status_text: err?.response?.statusText,
      });
      setError('Unable to load comparison data. The comparison service is currently unavailable.');
    } finally {
      setIsLoading(false);
    }
  }, [metricName, fiscalYearFilter, entityFilter, selectedSubsidiary, selectedDocIds, documentsCatalog.length]);

  useEffect(() => {
    loadMatrix();
  }, [loadMatrix]);

  // Document selection toggles
  const handleToggleDoc = (docId: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleSelectAllDocs = () => {
    setSelectedDocIds(documentsCatalog.map((d) => d.id));
  };

  const handleClearAllDocs = () => {
    setSelectedDocIds([]);
  };

  return (
    <div className="space-y-6">
      {/* Page Title & Operational Scope Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-[#30383D] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-[#242C30] text-[#C58B3A] border border-[#30383D]">
              <GitCompare className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-[#E8ECEB]">Cross-Document Metric Comparison Matrix</h1>
              <p className="text-xs text-[#9BA5A8] font-mono mt-0.5">
                Authoritative Multi-Source Government Verification, Variance Audit & Conflict Detection
              </p>
            </div>
          </div>
        </div>

        {/* Scope Context & Refresh Action */}
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-2 rounded-lg bg-[#151A1D] border border-[#30383D] flex items-center gap-2 text-xs font-mono shadow-sm">
            <Building2 className="h-4 w-4 text-[#C58B3A]" />
            <span className="text-[#9BA5A8]">Active Scope:</span>
            <span className="text-[#C58B3A] font-bold">{selectedSubsidiary}</span>
          </div>

          <Button
            variant="secondary"
            size="sm"
            onClick={loadMatrix}
            leftIcon={<RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />}
          >
            Refresh Matrix
          </Button>
        </div>
      </div>

      {/* SECTION 6 & 7: Official Document Display & Multi-Selection Interface */}
      {documentsCatalog.length > 0 && (
        <Card className="p-4 bg-[#1C2226] border border-[#30383D] space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#30383D] pb-2.5">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="h-4 w-4 text-[#C58B3A]" />
              <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-[#E8ECEB]">
                Authoritative Government Documents Catalog & Selection
              </h2>
              <span className="text-[11px] font-mono text-[#9BA5A8]">
                ({selectedDocIds.length} of {documentsCatalog.length} Selected)
              </span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSelectAllDocs}
                className="text-[11px] font-mono text-[#C58B3A] hover:underline flex items-center gap-1"
              >
                <CheckSquare className="h-3 w-3" /> Select All
              </button>
              <span className="text-[#30383D]">|</span>
              <button
                type="button"
                onClick={handleClearAllDocs}
                className="text-[11px] font-mono text-[#9BA5A8] hover:underline flex items-center gap-1"
              >
                <Square className="h-3 w-3" /> Clear Selection
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-6 gap-2.5 max-h-56 overflow-y-auto pr-1">
            {documentsCatalog.map((doc) => {
              const isChecked = selectedDocIds.includes(doc.id);
              return (
                <div
                  key={doc.id}
                  onClick={() => handleToggleDoc(doc.id)}
                  className={`p-2.5 rounded-lg border text-xs font-mono cursor-pointer transition-all ${
                    isChecked
                      ? 'bg-[#242C30] border-[#C58B3A]/60 shadow-sm'
                      : 'bg-[#151A1D]/60 border-[#30383D] opacity-60 hover:opacity-90'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => {}}
                      className="mt-0.5 rounded border-[#30383D] text-[#C58B3A] focus:ring-0 focus:ring-offset-0 cursor-pointer"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-[#E8ECEB] truncate" title={doc.document_title}>
                        {doc.document_title}
                      </p>
                      <p className="text-[10px] text-[#9BA5A8] truncate mt-0.5" title={doc.organization}>
                        {doc.organization}
                      </p>
                      <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                        <span className="px-1.5 py-0.2 rounded bg-[#151A1D] text-[10px] text-[#C58B3A] border border-[#30383D]">
                          FY {doc.financial_year}
                        </span>
                        <span className="px-1.5 py-0.2 rounded bg-[#151A1D] text-[10px] text-[#9BA5A8] border border-[#30383D]">
                          {doc.document_type}
                        </span>
                        {doc.verification_status === 'verified' ? (
                          <span className="text-[#4F8A62] text-[10px] font-bold">✓ Verified</span>
                        ) : (
                          <span className="text-[#D6A23A] text-[10px] font-bold">~ Provisional</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* SECTION 8: Filter Controls (Metric, FY Context, Entity Filter) */}
      <Card className="p-4 bg-[#1C2226] border border-[#30383D]">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Target Metric Selector */}
          <div>
            <label className="block text-[11px] font-mono text-[#9BA5A8] uppercase tracking-wider mb-1.5 font-semibold">
              <Layers className="h-3.5 w-3.5 inline mr-1 text-[#C58B3A]" /> Target Metric
            </label>
            <select
              value={metricName}
              onChange={(e) => setMetricName(e.target.value)}
              className="w-full bg-[#151A1D] border border-[#30383D] text-[#E8ECEB] text-xs font-mono rounded-lg px-3 py-2 focus:outline-none focus:border-[#C58B3A]"
            >
              {availableMetrics.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          {/* Fiscal Year Context Filter */}
          <div>
            <label className="block text-[11px] font-mono text-[#9BA5A8] uppercase tracking-wider mb-1.5 font-semibold">
              <Calendar className="h-3.5 w-3.5 inline mr-1 text-[#C58B3A]" /> Contextual Fiscal Year
            </label>
            <select
              value={fiscalYearFilter}
              onChange={(e) => setFiscalYearFilter(e.target.value)}
              className="w-full bg-[#151A1D] border border-[#30383D] text-[#E8ECEB] text-xs font-mono rounded-lg px-3 py-2 focus:outline-none focus:border-[#C58B3A]"
            >
              <option value="">All Fiscal Years</option>
              {availableFiscalYears.map((fy) => (
                <option key={fy} value={fy}>
                  FY {fy} {fy === '2026-27' ? '(Q1 YTD)' : ''}
                </option>
              ))}
            </select>
          </div>

          {/* Mine Entity Filter */}
          <div>
            <label className="block text-[11px] font-mono text-[#9BA5A8] uppercase tracking-wider mb-1.5 font-semibold">
              <Filter className="h-3.5 w-3.5 inline mr-1 text-[#C58B3A]" /> Entity / Mine Filter
            </label>
            <input
              type="text"
              placeholder="e.g. Gevra, Kusmunda, Rajmahal, SECL..."
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="w-full bg-[#151A1D] border border-[#30383D] text-[#E8ECEB] text-xs font-mono rounded-lg px-3 py-2 focus:outline-none focus:border-[#C58B3A] placeholder:text-[#9BA5A8]/60"
            />
          </div>

          {/* Matrix Summary Stats */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-[#242C30] border border-[#30383D]">
            <div>
              <span className="text-[10px] font-mono text-[#9BA5A8] uppercase block">Entities Compared</span>
              <span className="text-lg font-bold font-mono text-[#C58B3A]">
                {data?.total_entities_compared || 0}
              </span>
            </div>
            <div className="text-right">
              <span className="text-[10px] font-mono text-[#9BA5A8] uppercase block">Domain Class</span>
              <Badge variant="amber" size="sm">
                {data?.target_domain || 'PRODUCTION'}
              </Badge>
            </div>
          </div>
        </div>
      </Card>

      {/* SECTION 13: Official Source Conflict Callout */}
      {data?.conflicts && data.conflicts.length > 0 && (
        <Card className="p-4 bg-[#C94B45]/10 border border-[#C94B45]/40 space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-[#C94B45] shrink-0" />
            <h3 className="text-sm font-bold text-[#E8ECEB] font-mono">
              ⚠ Official Source Conflict ({data.conflicts.length} Active Records Detected)
            </h3>
          </div>
          <p className="text-xs text-[#9BA5A8] font-mono">
            Discrepancies identified between official government publications. Neither value is silently overwritten. Both values are displayed below with variance calculations and official statutory reconciliation notes.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
            {data.conflicts.map((c) => (
              <div
                key={c.conflict_id}
                className="p-3 rounded-lg bg-[#151A1D] border border-[#30383D] text-xs font-mono space-y-2"
              >
                <div className="flex items-center justify-between border-b border-[#30383D] pb-1.5">
                  <span className="font-bold text-[#E8ECEB]">{c.entity}</span>
                  <Badge variant="danger" size="sm">
                    {c.difference_percent}% Variance ({c.difference} MT)
                  </Badge>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px]">
                  <div className="p-2 rounded bg-[#242C30]/60 border border-[#30383D]">
                    <span className="text-[#9BA5A8] block truncate" title={c.source_a}>
                      Source A: {c.source_a}
                    </span>
                    <span className="text-[#E8ECEB] font-bold text-sm">{c.value_a} MT</span>
                  </div>
                  <div className="p-2 rounded bg-[#242C30]/60 border border-[#30383D]">
                    <span className="text-[#9BA5A8] block truncate" title={c.source_b}>
                      Source B: {c.source_b}
                    </span>
                    <span className="text-[#E8ECEB] font-bold text-sm">{c.value_b} MT</span>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-[#30383D]">
                  <div className="text-[11px] text-[#9BA5A8]">
                    <span className="text-[#C58B3A] font-semibold">Possible Reason: </span>
                    {c.possible_reason.replace(/_/g, ' ')}
                  </div>
                  <Link
                    href={c.conflict_id ? `/conflicts?id=${c.conflict_id}` : '/conflicts'}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-[#C94B45]/20 hover:bg-[#C94B45]/30 text-[#E8ECEB] border border-[#C94B45]/50 text-[10px] font-mono font-semibold transition-colors shrink-0"
                  >
                    Resolve →
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* SECTION 15: Loading State Skeleton */}
      {isLoading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="p-6 bg-[#1C2226] border border-[#30383D] animate-pulse space-y-4">
              <div className="flex items-center justify-between">
                <div className="h-6 w-1/3 bg-[#242C30] rounded" />
                <div className="h-6 w-28 bg-[#242C30] rounded" />
              </div>
              <div className="h-28 w-full bg-[#242C30] rounded" />
            </Card>
          ))}
        </div>
      )}

      {/* SECTION 15: API Failure / Error State with Retry Button */}
      {error && !isLoading && (
        <Card className="p-8 bg-[#1C2226] border border-[#C94B45]/40 text-center space-y-4">
          <div className="h-12 w-12 rounded-full bg-[#C94B45]/15 border border-[#C94B45]/30 flex items-center justify-center mx-auto text-[#C94B45]">
            <AlertCircle className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-[#E8ECEB] font-mono">Unable to load comparison data.</h3>
            <p className="text-xs text-[#9BA5A8] font-mono mt-1 max-w-md mx-auto">
              The comparison service is currently unavailable or returned an error. Please verify your connection or retry.
            </p>
          </div>
          <Button
            variant="primary"
            size="md"
            onClick={loadMatrix}
            leftIcon={<RefreshCw className="h-4 w-4" />}
            className="font-mono text-xs"
          >
            Retry Comparison
          </Button>
        </Card>
      )}

      {/* SECTION 15: Empty State */}
      {!isLoading && !error && data && data.matrices.length === 0 && (
        <Card className="p-12 text-center bg-[#1C2226] border border-[#30383D] space-y-3">
          <GitCompare className="h-10 w-10 text-[#9BA5A8] mx-auto" />
          <h3 className="text-base font-bold text-[#E8ECEB]">No comparison data available</h3>
          <p className="text-xs text-[#9BA5A8] max-w-md mx-auto font-mono">
            No compatible metrics were found across the selected documents. Try selecting all documents above or adjusting the Fiscal Year filter to FY 2024-25.
          </p>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              handleSelectAllDocs();
              setFiscalYearFilter('');
              setEntityFilter('');
            }}
            className="font-mono text-xs mt-2"
          >
            Reset Filters & Documents
          </Button>
        </Card>
      )}

      {/* SECTION 9: Comparison Matrix Tables List */}
      {!isLoading && !error && data && data.matrices.length > 0 && (
        <div className="space-y-6">
          {data.matrices.map((matrix: ComparisonMatrixItem, idx: number) => {
            const isYtd = matrix.period_type === 'YTD' || matrix.fiscal_year === '2026-27';
            return (
              <Card key={`${matrix.entity}-${matrix.fiscal_year}-${idx}`} className="p-5 bg-[#1C2226] border border-[#30383D] space-y-4">
                {/* Matrix Card Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#30383D] pb-3">
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-lg bg-[#242C30] border border-[#30383D] flex items-center justify-center text-[#C58B3A] font-extrabold text-xs">
                      #{idx + 1}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-lg font-bold text-[#E8ECEB]">{matrix.entity}</h3>
                        {/* SECTION 14: Strict YTD formatting for 2026-27 */}
                        {isYtd ? (
                          <span className="px-2 py-0.5 rounded bg-[#C58B3A]/15 text-[#C58B3A] border border-[#C58B3A]/30 text-xs font-mono font-bold">
                            FY 2026-27 — YTD (As of: June 2026)
                          </span>
                        ) : (
                          <Badge variant="amber" size="sm">
                            FY {matrix.fiscal_year}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs font-mono text-[#9BA5A8] mt-0.5">
                        Metric: <span className="text-[#E8ECEB] font-semibold">{matrix.metric_name}</span> • {matrix.source_count} Document Source{matrix.source_count === 1 ? '' : 's'} Evaluated
                      </p>
                    </div>
                  </div>

                  {/* Status Badges & Action */}
                  <div className="flex items-center gap-2 flex-wrap">
                    {matrix.is_seeded_demo && (
                      <Badge variant="warning" size="sm" className="font-mono">
                        Seeded Mine-Level Discrepancy
                      </Badge>
                    )}

                    {matrix.has_discrepancy || matrix.has_conflict ? (
                      <div className="flex items-center gap-2">
                        <Badge variant="danger" size="md" className="gap-1 font-bold">
                          <AlertTriangle className="h-4 w-4" />
                          DISCREPANCY DETECTED ({matrix.variance_percentage}% Variance)
                        </Badge>
                        <Link
                          href={matrix.canonical_conflict_id ? `/conflicts?id=${matrix.canonical_conflict_id}` : '/conflicts'}
                          className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-[#C94B45]/20 hover:bg-[#C94B45]/30 text-[#E8ECEB] border border-[#C94B45]/50 text-xs font-mono font-semibold transition-colors"
                        >
                          <AlertTriangle className="h-3.5 w-3.5 text-[#C94B45]" />
                          Resolve Conflict{matrix.canonical_conflict_id ? ` #${matrix.canonical_conflict_id}` : ''}
                        </Link>
                      </div>
                    ) : (
                      <Badge variant="success" size="md" className="gap-1 font-bold">
                        <CheckCircle2 className="h-4 w-4" />
                        CONSISTENT ({matrix.variance_percentage}% Variance)
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Source Comparison Table (Section 9) */}
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs font-mono">
                    <thead>
                      <tr className="border-b border-[#30383D] bg-[#242C30] text-[#E8ECEB] uppercase text-[10px]">
                        <th className="py-2.5 px-3">Metric</th>
                        <th className="py-2.5 px-3">Document Source</th>
                        <th className="py-2.5 px-3">Reporting FY</th>
                        <th className="py-2.5 px-3 text-right">Reported Value</th>
                        <th className="py-2.5 px-3 text-right">Standardized</th>
                        <th className="py-2.5 px-3 text-right">Difference</th>
                        <th className="py-2.5 px-3">Data Status</th>
                        <th className="py-2.5 px-3 text-center">Traceability</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#30383D]">
                      {matrix.sources.map((src: ComparisonSourceItem, sIdx: number) => {
                        const isSourceYtd = src.period_type === 'YTD' || src.fiscal_year === '2026-27';
                        return (
                          <tr key={sIdx} className="hover:bg-[#242C30]/50 transition-colors">
                            {/* Metric Name */}
                            <td className="py-3 px-3 font-semibold text-[#E8ECEB]">
                              <div>{matrix.metric_name}</div>
                              <div className="text-[10px] text-[#9BA5A8] font-normal truncate max-w-[140px]" title={src.original_metric_name}>
                                {src.original_metric_name || matrix.metric_name}
                              </div>
                            </td>

                            {/* Source Document */}
                            <td className="py-3 px-3 text-[#E8ECEB]">
                              <div className="flex items-center gap-1.5 font-semibold">
                                <FileText className="h-3.5 w-3.5 text-[#C58B3A] shrink-0" />
                                <span className="truncate max-w-[200px]" title={src.document_title || src.filename}>
                                  {src.document_title || src.filename}
                                </span>
                              </div>
                              <div className="text-[10px] text-[#9BA5A8] truncate max-w-[200px]">
                                {src.organization} • {src.page_number ? `Pg ${src.page_number}` : 'Pg N/A'}
                              </div>
                            </td>

                            {/* Reporting FY & Period */}
                            <td className="py-3 px-3">
                              {isSourceYtd ? (
                                <span className="text-[#C58B3A] font-bold text-[11px] block">
                                  2026-27 (YTD)
                                </span>
                              ) : (
                                <span className="text-[#E8ECEB]">{src.fiscal_year}</span>
                              )}
                              <span className="text-[10px] text-[#9BA5A8] block">
                                {src.as_of_date ? `As of: ${src.as_of_date}` : (src.period_type || 'Annual')}
                              </span>
                            </td>

                            {/* Extracted Raw Value & Unit */}
                            <td className="py-3 px-3 text-right text-[#9BA5A8]">
                              {src.raw_value.toLocaleString(undefined, { minimumFractionDigits: 2 })} {src.raw_unit}
                            </td>

                            {/* Standardized Value */}
                            <td className="py-3 px-3 text-right font-bold text-[#C58B3A]">
                              {formatStandardValue(src.standard_value)} {src.standard_unit}
                            </td>

                            {/* Difference vs Group */}
                            <td className="py-3 px-3 text-right font-mono text-[#9BA5A8]">
                              {matrix.sources.length >= 2 && matrix.difference_value !== undefined ? (
                                matrix.difference_value > 0 ? (
                                  <span className="text-[#C94B45] font-bold">
                                    ±{matrix.difference_value.toFixed(2)} {src.standard_unit}
                                  </span>
                                ) : (
                                  <span className="text-[#4F8A62] font-semibold">— (0.00)</span>
                                )
                              ) : (
                                <span className="text-[#9BA5A8]">—</span>
                              )}
                            </td>

                            {/* Data Status Badge (Section 14) */}
                            <td className="py-3 px-3">
                              {src.is_seeded_demo ? (
                                <Badge variant="warning" size="sm">Seeded Discrepancy</Badge>
                              ) : isSourceYtd ? (
                                <Badge variant="amber" size="sm">YTD / Provisional</Badge>
                              ) : src.verification_status === 'verified' || src.data_status === 'final' ? (
                                <Badge variant="success" size="sm">Government Verified</Badge>
                              ) : (
                                <Badge variant="secondary" size="sm">Provisional</Badge>
                              )}
                            </td>

                            {/* View Source Action (Section 12) */}
                            <td className="py-3 px-3 text-center">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setInspectSource(src)}
                                leftIcon={<Eye className="h-3.5 w-3.5 text-[#C58B3A]" />}
                                className="text-xs py-1 text-[#C58B3A] hover:text-[#D6A052] hover:bg-[#242C30]"
                              >
                                View Source
                              </Button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                {/* Provenance Notice Footer */}
                <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between text-[11px] font-mono text-[#9BA5A8] gap-2 border-t border-[#30383D]">
                  <div className="flex items-center gap-2">
                    <span>Unit Compatibility:</span>
                    <span className={matrix.units_compatible ? 'text-[#4F8A62] font-bold' : 'text-[#C94B45] font-bold'}>
                      {matrix.units_compatible ? '✓ VERIFIED COMPATIBLE' : '⚠ INCOMPATIBLE UNITS'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-3.5 w-3.5 text-[#54788A]" />
                    <span>{matrix.provenance_notice}</span>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* SECTION 12: Source Traceability Modal (Displays all 11 required fields) */}
      {inspectSource && (
        <div className="fixed inset-0 bg-black/75 z-50 flex items-center justify-center p-4">
          <div className="bg-[#1C2226] border border-[#30383D] rounded-xl max-w-xl w-full p-6 space-y-4 shadow-2xl relative">
            <div className="flex items-center justify-between border-b border-[#30383D] pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-[#C58B3A]" />
                <h3 className="text-base font-bold text-[#E8ECEB] font-mono">Official Source Traceability</h3>
              </div>
              <button
                type="button"
                onClick={() => setInspectSource(null)}
                className="text-[#9BA5A8] hover:text-[#E8ECEB] p-1 rounded hover:bg-[#242C30]"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs font-mono">
              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">1. Organization</span>
                <span className="font-semibold text-[#E8ECEB]">{inspectSource.organization || 'Not Available'}</span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">2. Document Title</span>
                <span className="font-semibold text-[#E8ECEB] truncate block" title={inspectSource.document_title || inspectSource.filename}>
                  {inspectSource.document_title || inspectSource.filename}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">3. Financial Year</span>
                <span className="font-semibold text-[#C58B3A]">
                  FY {inspectSource.fiscal_year} {inspectSource.period_type === 'YTD' ? '(YTD)' : ''}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">4. Publication Date</span>
                <span className="font-semibold text-[#E8ECEB]">{inspectSource.publication_date || 'Not Available'}</span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">5. Original Metric Name</span>
                <span className="font-semibold text-[#E8ECEB]">{inspectSource.original_metric_name || inspectSource.metric_name}</span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">6 & 7. Reported Value & Unit</span>
                <span className="font-bold text-[#C58B3A] text-sm">
                  {inspectSource.raw_value.toLocaleString(undefined, { minimumFractionDigits: 2 })} {inspectSource.raw_unit}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">8. Source Page</span>
                <span className="font-semibold text-[#E8ECEB]">
                  {inspectSource.page_number ? `Page ${inspectSource.page_number}` : 'Page: Not Available'}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">9. Source Table</span>
                <span className="font-semibold text-[#E8ECEB] truncate block" title={inspectSource.table_number || 'Not Available'}>
                  {inspectSource.table_number ? inspectSource.table_number : 'Table: Not Available'}
                </span>
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">10. Official Source URL</span>
                {inspectSource.source_url ? (
                  <a
                    href={inspectSource.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#C58B3A] hover:underline flex items-center gap-1 truncate"
                    title={inspectSource.source_url}
                  >
                    <ExternalLink className="h-3 w-3 shrink-0" />
                    <span className="truncate">{inspectSource.source_url}</span>
                  </a>
                ) : (
                  <span className="text-[#9BA5A8]">URL: Not Available</span>
                )}
              </div>

              <div className="p-2.5 rounded bg-[#151A1D] border border-[#30383D]">
                <span className="text-[#9BA5A8] text-[10px] uppercase block">11. Verification Status</span>
                <span className="font-bold text-[#4F8A62]">
                  {inspectSource.verification_status ? inspectSource.verification_status.toUpperCase() : 'GOVERNMENT VERIFIED'}
                </span>
              </div>
            </div>

            {/* Snippet / Evidence text */}
            <div className="p-3 rounded bg-[#151A1D] border border-[#30383D] text-xs font-mono space-y-1">
              <span className="text-[10px] uppercase text-[#9BA5A8] font-bold block">Document Evidence Text</span>
              <p className="text-[#E8ECEB] leading-relaxed italic">
                &ldquo;{inspectSource.snippet || 'No text snippet attached to this observation.'}&rdquo;
              </p>
            </div>

            <div className="flex justify-end pt-2">
              <Button variant="secondary" size="sm" onClick={() => setInspectSource(null)}>
                Close
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

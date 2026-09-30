'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useSearchParams } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { DocumentHeaderCard } from '@/components/documents/DocumentHeaderCard';
import { DocumentPageReader } from '@/components/documents/DocumentPageReader';
import { DocumentTablesOnPage } from '@/components/documents/DocumentTablesOnPage';
import { ExtractedMetricsTable } from '@/components/documents/ExtractedMetricsTable';
import { MetricLineageDrawer } from '@/components/documents/MetricLineageDrawer';
import { documentApi } from '@/lib/api/documentApi';
import { useLiveDocument } from '@/hooks/useLiveDocument';
import {
  DOCUMENT_POLL_INTERVAL_MS,
  getDocumentPageCount,
  shouldContinueDocumentPolling,
} from '@/lib/documentPolling';
import { ExtractedMetricItem } from '@/types/document';
import { metricForEvidence, tablesForPage } from '@/lib/documentEvidencePresentation';
import { ArrowLeft, BookOpen, FileText, Sparkles } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';

export default function DocumentDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const docId = Number(params?.id);
  const queryClient = useQueryClient();
  const { t } = useLanguage();

  const requestedPage = (() => {
    const raw = searchParams.get('page');
    if (!raw || !/^\d+$/.test(raw)) return null;
    const parsed = Number(raw);
    return Number.isSafeInteger(parsed) && parsed >= 1 ? parsed : null;
  })();
  const evidenceLocator = searchParams.get('evidence');
  const [activePage, setActivePage] = useState<number>(requestedPage ?? 1);
  const [selectedMetric, setSelectedMetric] = useState<ExtractedMetricItem | null>(null);

  // The metadata rendered by this page is owned by an explicit live polling
  // hook. This avoids a stale React Query cache being the only state source
  // for status and the authoritative page count.
  const { document, isLoading: isDocLoading, isError: isDocError, error: docError } = useLiveDocument(docId);
  const documentId = document?.id;

  const isDocumentProcessing = shouldContinueDocumentPolling(document);

  // A terminal transition must refresh every workspace panel once. The
  // dependent queries also poll while active, but invalidation guarantees the
  // final FAILED/PARSED/REVIEW state is accompanied by current pages, tables,
  // warnings, metrics, and audit history without a browser reload.
  useEffect(() => {
    if (!documentId || isNaN(docId)) return;
    const detailQueries = [
      ['document-pages', docId],
      ['document-lineage', docId],
      ['document-tables', docId],
      ['document-warnings', docId],
      ['document-history', docId],
    ] as const;
    void Promise.all(detailQueries.map((queryKey) => queryClient.invalidateQueries({ queryKey })));
  }, [documentId, document?.status, document?.processing_status, docId, queryClient]);

  // Fetch document page breakdown
  const {
    data: pagesData,
    isLoading: isPagesLoading,
  } = useQuery({
    queryKey: ['document-pages', docId],
    queryFn: () => documentApi.getDocumentPages(docId),
    enabled: !isNaN(docId) && !!document,
    refetchInterval: isDocumentProcessing ? DOCUMENT_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  // Fetch document metric lineage
  const {
    data: lineageData,
    isLoading: isLineageLoading,
  } = useQuery({
    queryKey: ['document-lineage', docId],
    queryFn: () => documentApi.getDocumentLineage(docId),
    enabled: !isNaN(docId) && !!document,
    refetchInterval: isDocumentProcessing ? DOCUMENT_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  const { data: tablesData, isLoading: isTablesLoading } = useQuery({
    queryKey: ['document-tables', docId],
    queryFn: () => documentApi.getDocumentTables(docId),
    enabled: !isNaN(docId) && !!document,
    refetchInterval: isDocumentProcessing ? DOCUMENT_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  const { data: warningsData } = useQuery({
    queryKey: ['document-warnings', docId],
    queryFn: () => documentApi.getDocumentWarnings(docId),
    enabled: !isNaN(docId) && !!document,
    refetchInterval: isDocumentProcessing ? DOCUMENT_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  const { data: historyData } = useQuery({
    queryKey: ['document-history', docId],
    queryFn: () => documentApi.getDocumentHistory(docId),
    enabled: !isNaN(docId) && !!document,
    refetchInterval: isDocumentProcessing ? DOCUMENT_POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  useEffect(() => {
    if (requestedPage == null || !pagesData || !document) return;
    // ExtractedMetric.page_number and DocumentPage.page_number are persisted
    // as human-facing one-based values. Convert nowhere else.
    const maxPage = getDocumentPageCount(document, pagesData.pages.length);
    setActivePage(Math.min(requestedPage, Math.max(maxPage, 1)));
  }, [document, pagesData, requestedPage]);

  if (isDocLoading) {
    return <LoadingState label={t('common.loading')} />;
  }

  if (isDocError || !document) {
    return (
      <div className="space-y-4 max-w-2xl mx-auto pt-8">
        <ErrorState message={docError instanceof Error ? docError.message : `Document #${docId} not found.`} />
        <Link href="/documents">
          <Button variant="secondary" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            {t('nav.documents')}
          </Button>
        </Link>
      </div>
    );
  }

  const pages = pagesData?.pages || [];
  const metrics = lineageData?.metrics || [];
  const evidenceMetric = metricForEvidence(metrics, evidenceLocator);
  const pageTables = tablesForPage(tablesData?.tables || [], activePage);

  const handleSelectMetric = (metric: ExtractedMetricItem) => {
    setSelectedMetric(metric);
  };

  const handleJumpToPage = (pageNum: number) => {
    setActivePage(pageNum);
  };

  return (
    <div className="space-y-6">
      {/* Page Navigation Header */}
      <PageHeader
        title={document.filename}
        description="Provenanced Extracted Text Canvas, Deterministic Unit Normalization, and Arithmetic Validation Suite."
        breadcrumbs={[
          { label: 'Document Repository', href: '/documents' },
          { label: document.filename },
        ]}
        badge={<Badge variant="amber">Document Workspace</Badge>}
        actions={
          <Link href="/documents">
            <Button variant="ghost" size="sm" leftIcon={<ArrowLeft className="h-4 w-4" />}>
              {t('nav.documents')}
            </Button>
          </Link>
        }
      />

      {/* Primary Header Card with Metadata & Pipeline Stepper */}
      <DocumentHeaderCard document={document} sourcePage={activePage} />

      {evidenceLocator && (
        <div className="rounded-xl border border-[#C58B3A]/40 bg-[#C58B3A]/10 px-4 py-3 text-xs text-[#E8ECEB]">
          {evidenceMetric ? (
            <>
              Evidence <span className="font-mono font-semibold">#{evidenceMetric.id}</span>: <span className="font-semibold">{evidenceMetric.metric_name}</span> for <span className="font-semibold">{evidenceMetric.mine_name}</span>, value <span className="font-semibold">{evidenceMetric.standard_value} {evidenceMetric.standard_unit || evidenceMetric.unit}</span>, persisted on page <span className="font-semibold">{evidenceMetric.page_number ?? activePage}</span>.
              {pageTables.length > 0 ? ` ${pageTables.length} persisted table artifact(s) are shown below; exact metric-to-cell provenance is unavailable.` : ' Exact metric-to-table-cell provenance is unavailable.'}
            </>
          ) : (
            <>Evidence locator <span className="font-mono font-semibold">#{evidenceLocator}</span> could not be resolved from persisted metric lineage. Exact cell provenance is unavailable.</>
          )}
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-[#30383D] bg-[#151A1D] p-4">
          <h2 className="text-sm font-semibold text-[#E8ECEB]">{t('workspace.persistedTables')}</h2>
          <p className="mt-2 text-xs text-[#9BA5A8]">{tablesData?.tables.length ?? 0} generic table records with source provenance.</p>
        </div>
        <div className="rounded-xl border border-[#30383D] bg-[#151A1D] p-4">
          <h2 className="text-sm font-semibold text-[#E8ECEB]">{t('workspace.warnings')}</h2>
          <p className="mt-2 text-xs text-[#9BA5A8]">{warningsData?.warnings.length ?? 0} warning(s){warningsData?.error ? ` · ${warningsData.error}` : ''}</p>
        </div>
        <div className="rounded-xl border border-[#30383D] bg-[#151A1D] p-4">
          <h2 className="text-sm font-semibold text-[#E8ECEB]">{t('workspace.history')}</h2>
          <p className="mt-2 text-xs text-[#9BA5A8]">{historyData?.events.length ?? 0} persisted audit event(s).</p>
        </div>
      </section>

      {/* Two-Column Document Intelligence Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: Extracted Metrics & Validation (5 cols) */}
        <div className="h-[600px] min-h-0 lg:h-[720px] lg:col-span-5">
          <ExtractedMetricsTable
            metrics={metrics}
            onSelectMetric={handleSelectMetric}
            loading={isLineageLoading}
          />
        </div>

        {/* RIGHT COLUMN: Document Page Reader Canvas (7 cols) */}
        <div className="h-[600px] min-h-0 lg:h-[720px] lg:col-span-7">
          <DocumentPageReader
            filename={document.filename}
            totalPages={getDocumentPageCount(document, pages.length)}
            pages={pages}
            pageTables={pageTables}
            activePageNumber={activePage}
            onPageChange={setActivePage}
            loading={isPagesLoading}
          />
        </div>
      </div>

      {/* Full-width persisted table evidence section */}
      <DocumentTablesOnPage tables={tablesData?.tables || []} pageNumber={activePage} loading={isTablesLoading} />

      {/* Metric Lineage Drawer */}
      <MetricLineageDrawer
        metric={selectedMetric}
        onClose={() => setSelectedMetric(null)}
        onJumpToPage={handleJumpToPage}
      />
    </div>
  );
}

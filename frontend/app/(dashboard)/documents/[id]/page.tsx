'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { DocumentHeaderCard } from '@/components/documents/DocumentHeaderCard';
import { DocumentPageReader } from '@/components/documents/DocumentPageReader';
import { ExtractedMetricsTable } from '@/components/documents/ExtractedMetricsTable';
import { MetricLineageDrawer } from '@/components/documents/MetricLineageDrawer';
import { documentApi } from '@/lib/api/documentApi';
import { ExtractedMetricItem } from '@/types/document';
import { ArrowLeft, BookOpen, FileText, Sparkles } from 'lucide-react';

export default function DocumentDetailPage() {
  const params = useParams();
  const docId = Number(params?.id);

  const [activePage, setActivePage] = useState<number>(1);
  const [selectedMetric, setSelectedMetric] = useState<ExtractedMetricItem | null>(null);

  // Fetch document metadata with live polling while processing or pending
  const {
    data: document,
    isLoading: isDocLoading,
    isError: isDocError,
    error: docError,
  } = useQuery({
    queryKey: ['document', docId],
    queryFn: () => documentApi.getDocumentById(docId),
    enabled: !isNaN(docId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === 'PROCESSING' || status === 'PENDING' ? 3000 : false;
    },
  });

  const isDocumentProcessing = document?.status === 'PROCESSING' || document?.status === 'PENDING';

  // Fetch document page breakdown
  const {
    data: pagesData,
    isLoading: isPagesLoading,
  } = useQuery({
    queryKey: ['document-pages', docId],
    queryFn: () => documentApi.getDocumentPages(docId),
    enabled: !isNaN(docId) && !!document && document.status !== 'FAILED',
    refetchInterval: isDocumentProcessing ? 3000 : false,
  });

  // Fetch document metric lineage
  const {
    data: lineageData,
    isLoading: isLineageLoading,
  } = useQuery({
    queryKey: ['document-lineage', docId],
    queryFn: () => documentApi.getDocumentLineage(docId),
    enabled: !isNaN(docId) && !!document && document.status !== 'FAILED',
    refetchInterval: isDocumentProcessing ? 3000 : false,
  });

  if (isDocLoading) {
    return <LoadingState label="Retrieving Document Metadata & Intelligence Analysis..." />;
  }

  if (isDocError || !document) {
    return (
      <div className="space-y-4 max-w-2xl mx-auto pt-8">
        <ErrorState message={docError instanceof Error ? docError.message : `Document #${docId} not found.`} />
        <Link href="/documents">
          <Button variant="secondary" leftIcon={<ArrowLeft className="h-4 w-4" />}>
            Back to Document Repository
          </Button>
        </Link>
      </div>
    );
  }

  const pages = pagesData?.pages || [];
  const metrics = lineageData?.metrics || [];

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
              Back to Repository
            </Button>
          </Link>
        }
      />

      {/* Primary Header Card with Metadata & Pipeline Stepper */}
      <DocumentHeaderCard document={document} />

      {/* Two-Column Document Intelligence Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT COLUMN: Extracted Metrics & Validation (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <ExtractedMetricsTable
            metrics={metrics}
            onSelectMetric={handleSelectMetric}
            loading={isLineageLoading}
          />
        </div>

        {/* RIGHT COLUMN: Document Page Reader Canvas (7 cols) */}
        <div className="lg:col-span-7">
          <DocumentPageReader
            filename={document.filename}
            totalPages={document.total_pages || pages.length || 1}
            pages={pages}
            activePageNumber={activePage}
            onPageChange={setActivePage}
            loading={isPagesLoading}
          />
        </div>
      </div>

      {/* Metric Lineage Drawer */}
      <MetricLineageDrawer
        metric={selectedMetric}
        onClose={() => setSelectedMetric(null)}
        onJumpToPage={handleJumpToPage}
      />
    </div>
  );
}

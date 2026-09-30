'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { DocumentTable } from '@/components/documents/DocumentTable';
import { UploadModal } from '@/components/documents/UploadModal';
import { documentApi } from '@/lib/api/documentApi';
import { useScope } from '@/context/ScopeContext';
import { Upload, FileText, Database, ShieldCheck } from 'lucide-react';
import { sourceApi } from '@/lib/api/sourceApi';
import { DOCUMENT_POLL_INTERVAL_MS, shouldContinueDocumentPolling } from '@/lib/documentPolling';
import { canIngestDocuments, canSyncOfficialSources, useCurrentUserRole } from '@/hooks/useCurrentUserRole';
import {
  OFFICIAL_SOURCE_POLL_INTERVAL_MS,
  getOfficialSourceSyncError,
  isOfficialSourceSyncing,
  isTerminalOfficialSourceStatus,
} from '@/lib/sourceSyncState';

export default function DocumentsPage() {
  const { selectedSubsidiary, setSelectedSubsidiary } = useScope();
  const userRole = useCurrentUserRole();
  const canIngest = canIngestDocuments(userRole);
  const canSync = canSyncOfficialSources(userRole);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState('ALL');

  // React Query data fetching for document repository list
  const {
    data: documentData,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['documents', selectedStatus, selectedSubsidiary],
    queryFn: () =>
      documentApi.getDocuments({
        status_filter: selectedStatus,
        subsidiary_filter: selectedSubsidiary,
      }, { cacheBust: Date.now() }),
    staleTime: 0,
    refetchInterval: (query) => {
      const items = query.state.data?.items || [];
      return !query.state.data || items.some((item) => shouldContinueDocumentPolling(item))
        ? DOCUMENT_POLL_INTERVAL_MS
        : false;
    },
    refetchIntervalInBackground: true,
  });

  const documents = documentData?.items || [];
  const [startingSync, setStartingSync] = useState(false);
  const [trackingSyncJob, setTrackingSyncJob] = useState(false);
  const [syncError, setSyncError] = useState<string | null>(null);
  const previousMinistryStatus = useRef<string | null>(null);
  const sourceQuery = useQuery({
    queryKey: ['official-sources'],
    queryFn: sourceApi.getSources,
    staleTime: 0,
    refetchInterval: (query) => {
      const source = query.state.data?.find((item) => item.name === 'Ministry of Coal');
      return isOfficialSourceSyncing(source, trackingSyncJob) ? OFFICIAL_SOURCE_POLL_INTERVAL_MS : false;
    },
    refetchIntervalInBackground: true,
  });
  const { refetch: refetchSources } = sourceQuery;
  const ministrySource = sourceQuery.data?.find((source) => source.name === 'Ministry of Coal');
  const sourceIsSyncing = startingSync || isOfficialSourceSyncing(ministrySource, trackingSyncJob);

  useEffect(() => {
    const status = ministrySource?.status || null;
    const wasSyncing = previousMinistryStatus.current === 'SYNCING';
    previousMinistryStatus.current = status;
    if (!isTerminalOfficialSourceStatus(status) || (!trackingSyncJob && !wasSyncing)) return;

    setTrackingSyncJob(false);
    const terminalError = getOfficialSourceSyncError(ministrySource);
    setSyncError(terminalError);
    if (!terminalError) void refetch();
  }, [ministrySource, refetch, trackingSyncJob]);

  const syncMinistry = async () => {
    if (sourceIsSyncing) return;
    setStartingSync(true);
    setSyncError(null);
    try {
      const accepted = await sourceApi.syncMinistryOfCoal();
      const refreshed = await refetchSources();
      const source = refreshed.data?.find((item) => item.name === 'Ministry of Coal');
      setStartingSync(false);
      // HTTP 202 means accepted by the worker, not completed. Track only
      // after a fresh source read so an old CONNECTED snapshot cannot clear
      // the monitor before the accepted job is observed.
      if (accepted.accepted && source?.status === 'SYNCING') {
        setTrackingSyncJob(true);
        return;
      }
      if (source && isTerminalOfficialSourceStatus(source.status)) {
        setTrackingSyncJob(false);
        const terminalError = getOfficialSourceSyncError(source);
        setSyncError(terminalError);
        if (!terminalError) await refetch();
        return;
      }
      setTrackingSyncJob(true);
    } catch (error) {
      setStartingSync(false);
      setSyncError(error instanceof Error ? error.message : 'Ministry synchronization failed.');
      setTrackingSyncJob(false);
      try {
        const refreshed = await refetchSources();
        const source = refreshed.data?.find((item) => item.name === 'Ministry of Coal');
        if (source?.status === 'SYNCING') {
          setSyncError(null);
          setTrackingSyncJob(true);
        }
      } catch {
        // Preserve the original start error if the status read also fails.
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Document Repository & Digitization Hub"
        titleKey="page.documents.title"
        description="Centralized geological reports, annual performance reviews, RTI disclosures, and production audit files for Coal India Limited and CMPDI."
        descriptionKey="page.documents.description"
        breadcrumbs={[{ label: 'Document Repository' }]}
        badge={<Badge variant="amber">V2 Intelligence Hub</Badge>}
        actions={canIngest ? (
          <Button
            variant="primary"
            leftIcon={<Upload className="h-4 w-4" />}
            onClick={() => setIsUploadModalOpen(true)}
          >
            Ingest Document
          </Button>
        ) : undefined}
      />

      <section className="rounded-xl border border-[#30383D] bg-[#151A1D] p-5 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-sm font-semibold text-[#E8ECEB]">Official Sources</h2>
            <p className="text-xs text-[#9BA5A8] mt-1">Bounded discovery and version-aware synchronization.</p>
          </div>
          {canSync && <Button variant="secondary" onClick={syncMinistry} disabled={sourceIsSyncing}>{sourceIsSyncing ? 'Syncing…' : 'Sync Ministry of Coal'}</Button>}
        </div>
        {syncError && <ErrorState message={syncError} />}
        {sourceQuery.isLoading ? <p className="text-xs text-[#9BA5A8]">Loading official sources…</p> : sourceQuery.isError ? <ErrorState message="Official source status is temporarily unavailable." /> : sourceQuery.data?.length ? sourceQuery.data.map((source) => (
          <div key={source.id} className="flex items-center justify-between border-t border-[#30383D] pt-3 text-xs">
            <div><div className="font-semibold text-[#E8ECEB]">{source.name}</div><div className="text-[#9BA5A8]">{source.status} · {source.documents} current documents · every {source.sync_frequency}</div></div>
            <span className="text-[#9BA5A8]">{source.last_success_at ? `Last sync ${new Date(source.last_success_at).toLocaleString()}` : 'Not synced yet'}</span>
          </div>
        )) : <p className="text-xs text-[#9BA5A8]">No official source has been synced yet.</p>}
      </section>

      {/* Main Document Data Table */}
      {isError ? (
        <ErrorState message="Document ingestion history is temporarily unavailable." />
      ) : (
        <DocumentTable
          documents={documents}
          loading={isLoading}
          onRefresh={() => refetch()}
          selectedStatus={selectedStatus}
          onStatusChange={setSelectedStatus}
          selectedSubsidiary={selectedSubsidiary}
          onSubsidiaryChange={setSelectedSubsidiary}
        />
      )}

      {/* Ingest Document Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={() => refetch()}
      />
    </div>
  );
}

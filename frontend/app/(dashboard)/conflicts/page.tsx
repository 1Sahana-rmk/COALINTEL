'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingState } from '@/components/ui/LoadingState';
import { ConflictResolveModal } from '@/components/validation/ConflictResolveModal';
import { validationApi, ConflictItem, ResolveConflictPayload } from '@/lib/api/validationApi';
import { useScope } from '@/context/ScopeContext';
import { buildConflictEvidenceUrl, evidenceLinkLabel } from '@/lib/conflictEvidence';
import { ChevronLeft, ChevronRight, GitCompare, RefreshCw } from 'lucide-react';
import {
  canRefreshConflictList,
  getConflictListViewState,
  shouldFetchConflictDetail,
  shouldRenderConflictListSkeleton,
} from '@/lib/conflictFetchState';
import {
  formatConflictCount,
  getConflictPageSkip,
  getTotalConflictPages,
  validateConflictPageInput,
} from '@/lib/conflictPagination';

const EMPTY_CONFLICTS: ConflictItem[] = [];

function ConflictsContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const targetId = searchParams.get('id') || searchParams.get('resolve');
  const { selectedSubsidiary } = useScope();
  const queryClient = useQueryClient();
  const [selectedStatus] = useState('ALL');
  const [page, setPage] = useState(0);
  const pageSize = 50;
  const currentPageNumber = page + 1;
  const [pageInput, setPageInput] = useState('');
  const [pageInputError, setPageInputError] = useState<string | null>(null);
  const [activeConflict, setActiveConflict] = useState<ConflictItem | null>(null);
  const [directFetchError, setDirectFetchError] = useState<string | null>(null);
  const directFetchTargetRef = React.useRef<string | null>(null);
  const directFetchVersionRef = React.useRef(0);

  const {
    data: conflictData,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['conflicts', selectedStatus, selectedSubsidiary, page, pageSize],
    queryFn: ({ signal }) => validationApi.getConflicts(
      selectedStatus,
      selectedSubsidiary,
      signal,
      getConflictPageSkip(currentPageNumber, pageSize),
      pageSize,
    ),
    staleTime: 30000,
    retry: false,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  });

  const conflicts = conflictData?.items ?? EMPTY_CONFLICTS;
  const totalPages = getTotalConflictPages(conflictData?.total ?? 0, pageSize);
  const listViewState = getConflictListViewState(isLoading, isError, conflictData?.total ?? conflicts.length);

  const changePage = (nextPage: number) => {
    setPage(nextPage);
    setPageInput('');
    setPageInputError(null);
  };

  const goToPage = () => {
    const result = validateConflictPageInput(pageInput, totalPages);
    if (!result.valid || result.page == null) {
      setPageInputError(result.error || `Page must be between 1 and ${totalPages.toLocaleString('en-IN')}.`);
      return;
    }

    setPageInputError(null);
    changePage(result.page - 1);
  };

  useEffect(() => {
    if (!targetId) {
      directFetchTargetRef.current = null;
      directFetchVersionRef.current += 1;
      return;
    }

    const match = conflicts.find((c) => String(c.id) === targetId || c.conflict_key === targetId);
    if (match) {
      directFetchTargetRef.current = `list:${targetId}`;
      directFetchVersionRef.current += 1;
      setActiveConflict(match);
      setDirectFetchError(null);
      return;
    }

    if (!shouldFetchConflictDetail({
      targetId,
      listLoading: isLoading,
      hasListMatch: false,
      requestedTargetId: directFetchTargetRef.current === targetId ? targetId : null,
    })) return;

    // Direct lookup by ID only after the list has settled and only once per
    // explicit target. List/detail loading are intentionally independent.
    directFetchTargetRef.current = targetId;
    const requestVersion = ++directFetchVersionRef.current;
    let isMounted = true;
    validationApi
      .getConflictById(targetId)
      .then((item) => {
        if (isMounted && requestVersion === directFetchVersionRef.current && item) {
          setActiveConflict(item);
          setDirectFetchError(null);
        }
      })
      .catch((err) => {
        console.warn('Could not load specific conflict by ID:', err);
        if (isMounted && requestVersion === directFetchVersionRef.current) {
          setDirectFetchError(`Discrepancy record #${targetId} could not be loaded or was not found.`);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [targetId, conflicts, isLoading]);

  const resolveMutation = useMutation({
    mutationFn: ({ id, payload }: { id: number | string; payload: ResolveConflictPayload }) =>
      validationApi.resolveConflict(id, payload),
    onSuccess: () => {
      setActiveConflict(null);
      // A conflict opened from ?id=... must not be reopened when the
      // invalidated list returns the now-resolved record.
      router.replace('/conflicts');
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      queryClient.invalidateQueries({ queryKey: ['comparison'] });
    },
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Cross-Document Conflict Resolver"
        titleKey="page.conflicts.title"
        description="Detects and resolves metric discrepancies (> 1% threshold) across distinct ingested document sources."
        descriptionKey="page.conflicts.description"
        breadcrumbs={[{ label: 'Conflict Resolver' }]}
        badge={<Badge variant="amber">Restricted: Admin / Reviewer</Badge>}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => { if (canRefreshConflictList(isFetching)) void refetch(); }}
            disabled={!canRefreshConflictList(isFetching)}
            leftIcon={<RefreshCw className={`h-3.5 w-3.5 ${isFetching ? 'animate-spin' : ''}`} />}
          >
            {isFetching ? 'Loading Conflicts…' : 'Refresh Conflicts'}
          </Button>
        }
      />

      {/* Error Alert */}
      {isError && <ErrorState message={error instanceof Error ? error.message : 'Failed to fetch conflict list.'} />}
      {directFetchError && <ErrorState message={directFetchError} />}

      {/* Main Conflicts Data Table Card */}
      <Card className="border-[#30383D] bg-[#1C2226]">
        <CardHeader className="py-3.5 px-4 bg-[#242C30] border-b border-[#30383D]">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-semibold text-[#E8ECEB] flex items-center gap-2">
              <GitCompare className="h-4 w-4 text-[#C58B3A]" />
              <span>Cross-Document Metric Discrepancies</span>
            </CardTitle>
            <Badge variant="amber" size="sm">
              {isError ? 'Unavailable' : isLoading && !conflictData ? 'Loading…' : `${conflictData?.total ?? 0} Discrepancy Pairs`}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[#30383D] bg-[#242C30] text-[11px] font-mono text-[#E8ECEB] uppercase tracking-wider">
                  <th className="py-3 px-4">Mine & Metric Entity</th>
                  <th className="py-3 px-4">Document A Value</th>
                  <th className="py-3 px-4">Document B Value</th>
                  <th className="py-3 px-4">Discrepancy %</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-[#30383D] text-xs font-mono">
                {shouldRenderConflictListSkeleton(isLoading) ? (
                  Array.from({ length: 3 }).map((_, idx) => (
                    <tr key={idx} className="animate-pulse">
                      <td className="py-3.5 px-4"><div className="h-4 w-36 bg-[#242C30] rounded-md" /></td>
                      <td className="py-3.5 px-4"><div className="h-4 w-28 bg-[#242C30] rounded-md" /></td>
                      <td className="py-3.5 px-4"><div className="h-4 w-28 bg-[#242C30] rounded-md" /></td>
                      <td className="py-3.5 px-4"><div className="h-4 w-16 bg-[#242C30] rounded-md" /></td>
                      <td className="py-3.5 px-4"><div className="h-4 w-20 bg-[#242C30] rounded-md" /></td>
                      <td className="py-3.5 px-4 text-right"><div className="h-6 w-20 bg-[#242C30] rounded-md ml-auto" /></td>
                    </tr>
                  ))
                ) : listViewState === 'ERROR' ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-[#C94B45] text-xs">
                      Conflict retrieval failed. Use the error message above or retry when the backend is available.
                    </td>
                  </tr>
                ) : listViewState === 'EMPTY' ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-[#9BA5A8] text-xs">
                      No cross-document metric discrepancies detected.
                    </td>
                  </tr>
                ) : (
                  conflicts.map((c) => (
                    <tr key={c.id} className="hover:bg-[#242C30]/50 transition-colors">
                      <td className="py-3.5 px-4 font-sans font-semibold text-[#E8ECEB]">
                        {c.mine_name}
                        <span className="block text-[11px] text-[#9BA5A8] font-mono font-normal">
                          {c.metric_name} ({c.fiscal_year})
                        </span>
                      </td>

                      <td className="py-3.5 px-4 text-[#9BA5A8]">
                        <span className="font-bold text-[#E8ECEB] block">
                          {c.document_a_value} {c.document_a_unit}
                        </span>
                        <span className="text-[10px] text-[#9BA5A8] truncate block max-w-xs" title={c.document_a_filename}>
                          {c.document_a_filename}
                        </span>
                        {buildConflictEvidenceUrl(c.document_a_id, c.evidence_a) ? (
                          <a
                            href={buildConflictEvidenceUrl(c.document_a_id, c.evidence_a) as string}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1 inline-block text-[10px] text-[#C58B3A] hover:underline"
                          >
                            {evidenceLinkLabel(c.evidence_a)}
                          </a>
                        ) : null}
                        {c.evidence_a?.page_number == null && (
                          <span className="mt-1 block text-[10px] text-[#9BA5A8]" title={c.evidence_a?.warning || undefined}>
                            Page-level provenance unavailable
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 text-[#9BA5A8]">
                        <span className="font-bold text-[#E8ECEB] block">
                          {c.document_b_value} {c.document_b_unit}
                        </span>
                        <span className="text-[10px] text-[#9BA5A8] truncate block max-w-xs" title={c.document_b_filename}>
                          {c.document_b_filename}
                        </span>
                        {buildConflictEvidenceUrl(c.document_b_id, c.evidence_b) ? (
                          <a
                            href={buildConflictEvidenceUrl(c.document_b_id, c.evidence_b) as string}
                            target="_blank"
                            rel="noreferrer"
                            className="mt-1 inline-block text-[10px] text-[#C58B3A] hover:underline"
                          >
                            {evidenceLinkLabel(c.evidence_b)}
                          </a>
                        ) : null}
                        {c.evidence_b?.page_number == null && (
                          <span className="mt-1 block text-[10px] text-[#9BA5A8]" title={c.evidence_b?.warning || undefined}>
                            Page-level provenance unavailable
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-4 font-bold text-[#D6A23A]">
                        {c.discrepancy_percentage?.toFixed(2)}%
                      </td>

                      <td className="py-3.5 px-4">
                        <Badge variant={c.status === 'OPEN' ? 'danger' : 'success'}>
                          {c.status || 'OPEN'}
                        </Badge>
                      </td>

                      <td className="py-3.5 px-4 text-right font-sans">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setActiveConflict(c)}
                        >
                          {c.status === 'RESOLVED' ? 'View Resolution' : 'Resolve Conflict'}
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          {listViewState === 'RESULTS' && conflictData && conflictData.total > 0 && (
            <div className="flex flex-col gap-3 border-t border-[#30383D] px-4 py-3 text-xs text-[#9BA5A8] sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
              <span>
                Showing {formatConflictCount(conflictData.skip + 1)}–{formatConflictCount(Math.min(conflictData.skip + conflicts.length, conflictData.total))} of {formatConflictCount(conflictData.total)}
              </span>
              <div className="flex flex-wrap items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page === 0 || isFetching}
                  onClick={() => changePage(Math.max(0, page - 1))}
                  leftIcon={<ChevronLeft className="h-3.5 w-3.5" />}
                >
                  Previous
                </Button>
                <span className="min-w-24 text-center">Page {currentPageNumber} of {formatConflictCount(totalPages)}</span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPageNumber >= totalPages || !conflictData.has_next || isFetching}
                  onClick={() => changePage(Math.min(totalPages - 1, page + 1))}
                  rightIcon={<ChevronRight className="h-3.5 w-3.5" />}
                >
                  Next
                </Button>
                <div className="flex flex-wrap items-center gap-2 sm:ml-2">
                  <label htmlFor="conflict-go-to-page" className="whitespace-nowrap">Go to page</label>
                  <input
                    id="conflict-go-to-page"
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    value={pageInput}
                    onChange={(event) => {
                      setPageInput(event.target.value);
                      if (pageInputError) setPageInputError(null);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter') {
                        event.preventDefault();
                        goToPage();
                      }
                    }}
                    aria-describedby={pageInputError ? 'conflict-go-to-page-error' : undefined}
                    className="h-8 w-20 rounded-md border border-[#30383D] bg-[#151A1D] px-2 text-center text-xs text-[#E8ECEB] outline-none focus:border-[#C58B3A]"
                  />
                  <Button variant="outline" size="sm" onClick={goToPage} disabled={isFetching}>
                    Go
                  </Button>
                </div>
              </div>
              {pageInputError && (
                <p id="conflict-go-to-page-error" className="basis-full text-right text-[11px] text-[#C94B45]">
                  {pageInputError}
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Resolution Modal */}
      <ConflictResolveModal
        conflict={activeConflict}
        onClose={() => setActiveConflict(null)}
        onResolve={(id, payload) => resolveMutation.mutate({ id, payload })}
        isLoading={resolveMutation.isPending}
        error={resolveMutation.error instanceof Error ? resolveMutation.error.message : resolveMutation.error ? 'Conflict resolution failed.' : null}
      />
    </div>
  );
}

export default function ConflictsPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading Cross-Document Conflicts..." />}>
      <ConflictsContent />
    </Suspense>
  );
}

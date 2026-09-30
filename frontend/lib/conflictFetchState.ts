export interface ConflictDetailFetchDecision {
  targetId: string | null;
  listLoading: boolean;
  hasListMatch: boolean;
  requestedTargetId: string | null;
}

/**
 * Direct detail lookup is allowed only for an explicit URL target after the
 * list has reached a settled state and only once for that target.
 */
export const shouldFetchConflictDetail = ({
  targetId,
  listLoading,
  hasListMatch,
  requestedTargetId,
}: ConflictDetailFetchDecision): boolean =>
  Boolean(targetId) && !listLoading && !hasListMatch && requestedTargetId !== targetId;

export const shouldRenderConflictListSkeleton = (listLoading: boolean): boolean => listLoading;

export const canRefreshConflictList = (isFetching: boolean): boolean => !isFetching;

export type ConflictListViewState = 'LOADING' | 'ERROR' | 'EMPTY' | 'RESULTS';

export const getConflictListViewState = (
  isLoading: boolean,
  isError: boolean,
  conflictCount: number,
): ConflictListViewState => {
  if (isLoading) return 'LOADING';
  if (isError) return 'ERROR';
  return conflictCount === 0 ? 'EMPTY' : 'RESULTS';
};

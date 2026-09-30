import { apiClient } from './client';

export interface OfficialSourceItem {
  id: number;
  name: string;
  organization: string;
  base_url: string;
  source_type: string;
  enabled: boolean;
  sync_frequency: string;
  last_sync_at: string | null;
  last_success_at: string | null;
  status: string;
  last_error: string | null;
  documents: number;
}

export interface SyncStartResponse {
  source_id: number;
  job_id: string;
  status: string;
  accepted: boolean;
}

export const sourceApi = {
  getSources: async (): Promise<OfficialSourceItem[]> =>
    (await apiClient.get<OfficialSourceItem[]>('/sources', {
      params: { _coalintel_live: Date.now() },
      headers: {
        'Cache-Control': 'no-cache, no-store, max-age=0',
        Pragma: 'no-cache',
      },
    })).data,
  syncMinistryOfCoal: async (): Promise<SyncStartResponse> =>
    (await apiClient.post<SyncStartResponse>('/sources/ministry-of-coal/sync')).data,
};

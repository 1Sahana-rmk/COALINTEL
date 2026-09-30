import { apiClient } from './client';

export interface AuditLogItem {
  id: number;
  user: string;
  action: string;
  details: string;
  ip: string;
  timestamp: string;
}

export const auditApi = {
  getAuditLogs: async (limit: number = 50): Promise<AuditLogItem[]> => {
    const response = await apiClient.get<AuditLogItem[]>('/audit/logs', {
      params: { limit },
    });
    return response.data;
  },
};

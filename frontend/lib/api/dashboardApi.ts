import { apiClient } from './client';
import {
  DashboardKpis,
  DashboardChartsResponse,
  ValidationFeedItem,
  WordCloudItem,
} from '@/types/dashboard';
import { ALL_FISCAL_YEARS_VALUE } from '@/lib/constants';

export interface DashboardFilterParams {
  fiscal_year?: string;
  subsidiary_filter?: string;
}

export function normalizeDashboardFiscalYear(fiscalYear?: string): string | undefined {
  if (!fiscalYear || fiscalYear.toUpperCase() === ALL_FISCAL_YEARS_VALUE) {
    return undefined;
  }
  return fiscalYear;
}

export const dashboardApi = {
  getKpis: async (params?: DashboardFilterParams): Promise<DashboardKpis> => {
    const sub = params?.subsidiary_filter;
    const isAll =
      !sub ||
      sub.toUpperCase() === 'ALL' ||
      sub.toUpperCase() === 'ALL CIL' ||
      sub.toUpperCase() === 'ALL SUBSIDIARIES' ||
      sub.toUpperCase() === 'ALL_CIL' ||
      sub.toUpperCase() === 'ALL_SUBSIDIARIES';

    const response = await apiClient.get<DashboardKpis>('/dashboard/kpis', {
      params: {
        fiscal_year: normalizeDashboardFiscalYear(params?.fiscal_year),
        subsidiary_filter: isAll ? undefined : sub,
      },
    });
    return response.data;
  },
  getCharts: async (params?: DashboardFilterParams): Promise<DashboardChartsResponse> => {
    const sub = params?.subsidiary_filter;
    const isAll =
      !sub ||
      sub.toUpperCase() === 'ALL' ||
      sub.toUpperCase() === 'ALL CIL' ||
      sub.toUpperCase() === 'ALL SUBSIDIARIES' ||
      sub.toUpperCase() === 'ALL_CIL' ||
      sub.toUpperCase() === 'ALL_SUBSIDIARIES';

    const response = await apiClient.get<DashboardChartsResponse>('/dashboard/charts', {
      params: {
        fiscal_year: normalizeDashboardFiscalYear(params?.fiscal_year),
        subsidiary_filter: isAll ? undefined : sub,
      },
    });
    return response.data;
  },
  getValidationFeed: async (): Promise<ValidationFeedItem[]> => {
    const response = await apiClient.get<ValidationFeedItem[]>('/validation/feed');
    return response.data;
  },
  getWordCloud: async (): Promise<WordCloudItem[]> => {
    const response = await apiClient.get<WordCloudItem[]>('/analytics/wordcloud');
    return response.data;
  },
};

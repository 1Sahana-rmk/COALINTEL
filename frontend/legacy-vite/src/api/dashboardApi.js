import { apiClient } from './client';

export const dashboardApi = {
  getKpis: async () => {
    const response = await apiClient.get('/dashboard/kpis');
    return response.data;
  },
  getCharts: async () => {
    const response = await apiClient.get('/dashboard/charts');
    return response.data;
  },
  getWordCloud: async () => {
    const response = await apiClient.get('/analytics/wordcloud');
    return response.data;
  },
  getValidationFeed: async () => {
    const response = await apiClient.get('/validation/feed');
    return response.data;
  }
};

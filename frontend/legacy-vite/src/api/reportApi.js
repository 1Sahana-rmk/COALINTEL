import { apiClient } from './client';

export const reportApi = {
  generateReport: async (reportParams) => {
    const response = await apiClient.post('/reports/generate', reportParams);
    return response.data;
  },
  getReports: async () => {
    const response = await apiClient.get('/reports');
    return response.data;
  }
};

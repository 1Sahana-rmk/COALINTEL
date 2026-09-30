import { apiClient } from './client';

export const validationApi = {
  getFeed: async () => {
    const response = await apiClient.get('/validation/feed');
    return response.data;
  },
  resolveConflict: async (conflictId, resolutionData) => {
    const response = await apiClient.post(`/conflicts/${conflictId}/resolve`, resolutionData);
    return response.data;
  }
};

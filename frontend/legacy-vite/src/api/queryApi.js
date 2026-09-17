import { apiClient } from './client';

export const queryApi = {
  askQuery: async (prompt, filters = {}) => {
    const response = await apiClient.post('/query/ask', { prompt, filters });
    return response.data;
  }
};

import { apiClient } from './client';

export const documentApi = {
  uploadDocument: async (formData, onUploadProgress) => {
    const response = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress,
    });
    return response.data;
  },
  getDocuments: async (params) => {
    const response = await apiClient.get('/documents', { params });
    return response.data;
  },
  getDocumentById: async (id) => {
    const response = await apiClient.get(`/documents/${id}`);
    return response.data;
  },
  getDocumentPages: async (id) => {
    const response = await apiClient.get(`/documents/${id}/pages`);
    return response.data;
  },
  getDocumentLineage: async (id) => {
    const response = await apiClient.get(`/documents/${id}/lineage`);
    return response.data;
  }
};

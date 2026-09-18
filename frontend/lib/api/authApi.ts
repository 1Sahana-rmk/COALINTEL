import { apiClient } from './client';
import { LoginResponse, SignupPayload, UserProfile } from '@/types/auth';

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', { username, password });
    return response.data;
  },
  signup: async (payload: SignupPayload): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>('/auth/signup', payload);
    return response.data;
  },
  getCurrentUser: async (): Promise<UserProfile> => {
    const response = await apiClient.get<UserProfile>('/auth/me');
    return response.data;
  },
};


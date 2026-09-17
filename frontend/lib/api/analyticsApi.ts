import { apiClient } from './client';

export interface WordCloudTopicItem {
  word: string;
  weight: number;
  category: string;
}

export interface WordCloudResponse {
  topics: WordCloudTopicItem[];
}

export const analyticsApi = {
  getWordCloud: async (subsidiary_filter?: string): Promise<WordCloudResponse> => {
    const response = await apiClient.get<WordCloudResponse>('/analytics/wordcloud', {
      params: {
        subsidiary_filter: subsidiary_filter && subsidiary_filter !== 'ALL' && subsidiary_filter !== 'ALL CIL' ? subsidiary_filter : undefined,
      },
    });
    return response.data;
  },
};

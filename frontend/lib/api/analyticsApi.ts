import { apiClient } from './client';

export interface WordCloudTopicItem {
  word: string;
  weight: number;
  category: string;
  occurrence_count?: number;
  document_count?: number;
  score?: number;
}

export interface WordCloudResponse {
  topics: WordCloudTopicItem[];
  status?: string;
  corpus_items?: number;
  method?: string;
}

export interface TopicEvidence {
  document_id: number;
  page_number?: number | null;
  filename?: string;
  source_url?: string | null;
  chunk_id?: number | null;
}

export interface CorpusTopic {
  topic_id: string;
  name: string;
  representative_terms: string[];
  chunk_count: number;
  document_count: number;
  evidence: TopicEvidence[];
}

export interface TopicsResponse {
  topics: CorpusTopic[];
  status: string;
  method: string;
  corpus_items?: number;
}

export interface TrendPoint {
  entity: string;
  period: string;
  unit: string;
  value: number | null;
  status: string;
  fact_ids: number[];
}

export interface TrendResponse {
  status: string;
  metric: string;
  points: TrendPoint[];
  count: number;
  all_years_not_summed: boolean;
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
  getTopics: async (subsidiary_filter?: string): Promise<TopicsResponse> => {
    const response = await apiClient.get<TopicsResponse>('/analytics/topics', {
      params: { subsidiary_filter: subsidiary_filter && subsidiary_filter !== 'ALL' && subsidiary_filter !== 'ALL CIL' ? subsidiary_filter : undefined },
    });
    return response.data;
  },
  getTrend: async (metric: string, subsidiary?: string): Promise<TrendResponse> => {
    const response = await apiClient.get<TrendResponse>('/analytics/trends', {
      params: { metric, subsidiary: subsidiary && subsidiary !== 'ALL' && subsidiary !== 'ALL CIL' ? subsidiary : undefined },
    });
    return response.data;
  },
};

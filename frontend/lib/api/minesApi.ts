import { apiClient } from './client';

export interface MineSummary {
  mine_id: string;
  mine_name: string;
  canonical_name: string;
  company_name: string;
  parent_company?: string;
  subsidiary_name?: string;
  state: string;
  district?: string;
  block?: string;
  coalfield?: string;
  coal_or_lignite?: string;
  mine_type?: string;
  mining_method?: string;
  sector?: string;
  ownership_type?: string;
  captive_or_commercial?: string;
  operational_status: string;
  production_status?: string;
  financial_year?: string;
  verification_status?: string;
  data_origin: string;
  latest_production_mt?: number;
  latest_target_mt?: number;
  latest_achievement_percent?: number;
  latest_fiscal_year?: string;
  period_type?: string;
  data_status?: string;
  star_rating?: number;
  source_document?: string;
  source_url?: string;
  production_fy24_25?: number;
  production_fy25_26?: number;
  production_fy26_27_ytd?: number;
  yoy_growth_percent?: number;
}

export interface DimensionCountItem {
  name: string;
  count: number;
  code?: string;
}

export interface MineYearlyMetric {
  id: number;
  mine_id: string;
  financial_year: string;
  period_type: string;
  data_status: string;
  production_mt?: number;
  production_target_mt?: number;
  production_achievement_percent?: number;
  dispatch_mt?: number;
  dispatch_target_mt?: number;
  dispatch_achievement_percent?: number;
  star_rating?: number;
  obr_mcum?: number;
  manpower?: number;
  source_id: string;
  source_document?: string;
  source_url?: string;
  source_page?: number;
  source_table?: string;
  source_published_date?: string;
  verification_status: string;
  quality_status: string;
  data_origin: string;
}

export interface MineMonthlyMetric {
  id: number;
  mine_id: string;
  financial_year: string;
  month: string;
  period_type: string;
  production_mt?: number;
  dispatch_mt?: number;
  target_mt?: number;
  achievement_percent?: number;
  data_status: string;
  as_of_date?: string;
  source_id: string;
  source_document?: string;
  source_url?: string;
}

export interface DataSourceItem {
  source_id: string;
  organization: string;
  document_title: string;
  document_type: string;
  publication_date?: string;
  financial_year: string;
  url?: string;
  page_number?: number;
  table_number?: string;
  chapter?: string;
  section_name?: string;
  source_priority: number;
  verification_status: string;
}

export interface MineDetail {
  mine_id: string;
  mine_name: string;
  normalized_mine_name: string;
  original_mine_name?: string;
  company_name: string;
  parent_company?: string;
  subsidiary_name?: string;
  state: string;
  district?: string;
  block?: string;
  coalfield?: string;
  coal_or_lignite: string;
  mine_type?: string;
  mining_method?: string;
  sector?: string;
  ownership_type?: string;
  allocation_type?: string;
  end_use?: string;
  operational_status: string;
  production_status?: string;
  mine_opening_permission?: string;
  captive_or_commercial?: string;
  financial_year?: string;
  source_id?: string;
  source_document?: string;
  source_url?: string;
  source_page?: number;
  source_table?: string;
  source_chapter?: string;
  source_publication_date?: string;
  retrieved_at?: string;
  last_verified_at?: string;
  verification_status?: string;
  data_origin?: string;
  yearly_metrics: MineYearlyMetric[];
  monthly_metrics: MineMonthlyMetric[];
  aliases: string[];
  provenance_sources: DataSourceItem[];
}


export interface CoalBlockItem {
  coal_block_id: string;
  coal_block_name: string;
  mine_name?: string;
  mine_id?: string;
  allottee: string;
  company: string;
  state: string;
  district?: string;
  allocation_method?: string;
  end_use?: string;
  sale_of_coal?: string;
  production_status?: string;
  production_mt?: number;
  target_production_mt?: number;
  peak_rated_capacity_mtpa?: number;
  source_id: string;
}

export interface DataConflictRecordItem {
  conflict_id: number;
  entity_type: string;
  entity_id: string;
  metric: string;
  financial_year: string;
  source_a: string;
  value_a: number;
  source_b: string;
  value_b: number;
  difference: number;
  difference_percent: number;
  possible_reason: string;
  resolution_status: string;
  resolved_value?: number;
  resolution_method?: string;
}

export interface DataValidationResultItem {
  id: number;
  validation_type: string;
  entity_id: string;
  financial_year: string;
  calculated_value: number;
  reported_value: number;
  variance: number;
  variance_percent: number;
  status: string;
  notes?: string;
}

export interface MinesSummaryStats {
  total_canonical_mines: number;
  total_coal_blocks: number;
  authoritative_sources_count: number;
  cross_document_conflicts_count: number;
  validation_checks_count: number;
  coverage?: {
    total_canonical_records: number;
    states_covered: number;
    districts_covered: number;
    companies_count: number;
    subsidiaries_count: number;
    coal_mines_count: number;
    lignite_mines_count: number;
    producing_mines_count: number;
    non_producing_mines_count: number;
    records_with_source_citations: number;
    records_missing_key_fields: number;
  };
  breakdowns?: {
    by_state: Record<string, number>;
    by_subsidiary: Record<string, number>;
    by_type: Record<string, number>;
    by_sector: Record<string, number>;
    by_status: Record<string, number>;
    by_fuel: Record<string, number>;
  };
  major_mines_production: {
    fy_2024_25_mt: number;
    fy_2025_26_mt: number;
    fy_2026_27_ytd_mt: number;
    as_of_date: string;
    period_type_26_27: string;
    data_status_26_27: string;
  };
  national_benchmarks: {
    fy_2024_25_all_india_mt: number;
    fy_2024_25_captive_commercial_mt: number;
    fy_2025_26_captive_commercial_mt: number;
    source_authority: string;
  };
}

export interface MineFilterParams {
  fiscal_year?: string;
  subsidiary?: string;
  company?: string;
  state?: string;
  district?: string;
  mine_type?: string;
  sector?: string;
  ownership?: string;
  coal_or_lignite?: string;
  status?: string;
  search?: string;
  sort_by?: string;
  sort_order?: string;
  page?: number;
  page_size?: number;
  skip?: number;
  limit?: number;
}

export interface MinesListResult {
  items: MineSummary[];
  total: number;
}

export const minesApi = {
  getMines: async (params?: MineFilterParams): Promise<MineSummary[]> => {
    const res = await apiClient.get<MineSummary[]>('/mines', { params });
    return res.data;
  },

  getMinesWithCount: async (params?: MineFilterParams): Promise<MinesListResult> => {
    const res = await apiClient.get<MineSummary[]>('/mines', { params });
    const total = parseInt(res.headers['x-total-count'] || '0', 10) || res.data.length;
    return { items: res.data, total };
  },

  getMineDetails: async (mineId: string): Promise<MineDetail> => {
    const res = await apiClient.get<MineDetail>(`/mines/${encodeURIComponent(mineId)}`);
    return res.data;
  },

  getStats: async (): Promise<MinesSummaryStats> => {
    const res = await apiClient.get<MinesSummaryStats>('/mines/stats');
    return res.data;
  },

  getStates: async (): Promise<DimensionCountItem[]> => {
    const res = await apiClient.get<DimensionCountItem[]>('/mines/states');
    return res.data;
  },

  getSubsidiaries: async (): Promise<DimensionCountItem[]> => {
    const res = await apiClient.get<DimensionCountItem[]>('/mines/subsidiaries');
    return res.data;
  },

  getSectors: async (): Promise<DimensionCountItem[]> => {
    const res = await apiClient.get<DimensionCountItem[]>('/mines/sectors');
    return res.data;
  },

  getMineTypes: async (): Promise<DimensionCountItem[]> => {
    const res = await apiClient.get<DimensionCountItem[]>('/mines/types');
    return res.data;
  },

  getCompanies: async (): Promise<DimensionCountItem[]> => {
    const res = await apiClient.get<DimensionCountItem[]>('/mines/companies');
    return res.data;
  },

  getCoalBlocks: async (params?: { search?: string; state?: string; allocation_status?: string }): Promise<CoalBlockItem[]> => {
    const res = await apiClient.get<CoalBlockItem[]>('/coal-blocks', { params });
    return res.data;
  },

  getDataSources: async (): Promise<DataSourceItem[]> => {
    const res = await apiClient.get<DataSourceItem[]>('/data-sources');
    return res.data;
  },

  getDataConflicts: async (resolutionStatus?: string): Promise<DataConflictRecordItem[]> => {
    const res = await apiClient.get<DataConflictRecordItem[]>('/data-conflicts', {
      params: resolutionStatus ? { resolution_status: resolutionStatus } : undefined,
    });
    return res.data;
  },

  getDataValidations: async (statusFilter?: string): Promise<DataValidationResultItem[]> => {
    const res = await apiClient.get<DataValidationResultItem[]>('/data-validations', {
      params: statusFilter ? { status_filter: statusFilter } : undefined,
    });
    return res.data;
  },

  getMinesSummaryStats: async (): Promise<MinesSummaryStats> => {
    const res = await apiClient.get<MinesSummaryStats>('/mines-summary-stats');
    return res.data;
  },
};

'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Card } from '@/components/ui/Card';
import { WordCloudTagCloud } from '@/components/analytics/WordCloudTagCloud';
import { TfidfMatrixTable } from '@/components/analytics/TfidfMatrixTable';
import { analyticsApi } from '@/lib/api/analyticsApi';
import { useScope } from '@/context/ScopeContext';
import { Database } from 'lucide-react';

export default function AnalyticsPage() {
  const { selectedSubsidiary } = useScope();
  const {
    data: wordcloudData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['analytics-wordcloud', selectedSubsidiary],
    queryFn: () => analyticsApi.getWordCloud(selectedSubsidiary),
    staleTime: 60000,
  });

  const topics = wordcloudData?.topics || [
    { word: 'Overburden Removal', weight: 98, category: 'Operational' },
    { word: 'Opencast Mining', weight: 85, category: 'Methodology' },
    { word: 'Stripping Ratio', weight: 72, category: 'Metric' },
    { word: 'Washing Capacity', weight: 64, category: 'Infrastructure' },
    { word: 'Coal Production MT', weight: 94, category: 'Production' },
    { word: 'Environmental Clearance', weight: 58, category: 'Regulatory' },
    { word: 'HEMM Availability', weight: 52, category: 'Equipment' },
    { word: 'Coal Despatch MT', weight: 88, category: 'Logistics' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Automated Word Cloud & Topic Identification Module"
        description="Statistical TF-IDF term frequency analysis, operational keyword clustering, and entity recognition breakdown across ingested CIL documents."
        breadcrumbs={[{ label: 'Topic Analytics' }]}
        badge={<Badge variant="amber">Topic Engine</Badge>}
      />

      {/* Error Alert */}
      {isError && <ErrorState message={error instanceof Error ? error.message : 'Failed to fetch topic analytics.'} />}

      {/* Loading Indicator */}
      {isLoading ? (
        <LoadingState label="Extracting TF-IDF Keyword Vectors & Frequency Matrix..." />
      ) : (
        <div className="space-y-6">
          {/* Tag Cloud & Summary Cards */}
          <WordCloudTagCloud topics={topics} />

          {/* Detailed TF-IDF Table & Entity Recognition Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-8">
              <TfidfMatrixTable topics={topics} />
            </div>

            {/* Entity Recognition Summary Side Card */}
            <div className="lg:col-span-4 space-y-4">
              <Card className="border-[#30383D] bg-[#1C2226]">
                <div className="p-6 space-y-4 text-center">
                  <div className="inline-flex p-3.5 rounded-lg bg-[#242C30] text-[#C58B3A] border border-[#30383D]">
                    <Database className="h-8 w-8" />
                  </div>

                  <h3 className="text-base font-bold text-[#E8ECEB]">Mining Named Entity Recognition</h3>
                  <p className="text-xs text-[#9BA5A8] leading-relaxed">
                    Automated entity tagger identifying Opencast Mines, Coalfields, CIL Subsidiaries (ECL, BCCL, CCL, WCL, SECL, NCL, MCL), and target production metrics.
                  </p>

                  <div className="grid grid-cols-2 gap-3 pt-4 border-t border-[#30383D] text-xs font-mono">
                    <div className="p-3 bg-[#242C30] rounded-lg border border-[#30383D]">
                      <span className="text-[#9BA5A8] block text-[10px]">Reference Mine Coverage</span>
                      <span className="text-lg font-bold text-[#C58B3A] mt-1 block">48 Mines</span>
                    </div>

                    <div className="p-3 bg-[#242C30] rounded-lg border border-[#30383D]">
                      <span className="text-[#9BA5A8] block text-[10px]">Reference Subsidiary Coverage</span>
                      <span className="text-lg font-bold text-[#4F8A62] mt-1 block">8 Subsidiaries</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

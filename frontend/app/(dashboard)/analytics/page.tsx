'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { WordCloudTagCloud } from '@/components/analytics/WordCloudTagCloud';
import { TfidfMatrixTable } from '@/components/analytics/TfidfMatrixTable';
import { analyticsApi, WordCloudTopicItem } from '@/lib/api/analyticsApi';
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

  const { data: corpusTopics } = useQuery({
    queryKey: ['analytics-topics', selectedSubsidiary],
    queryFn: () => analyticsApi.getTopics(selectedSubsidiary),
    staleTime: 60000,
  });

  const { data: productionTrend } = useQuery({
    queryKey: ['analytics-trend', 'COAL_PRODUCTION', selectedSubsidiary],
    queryFn: () => analyticsApi.getTrend('COAL_PRODUCTION', selectedSubsidiary),
    staleTime: 60000,
  });

  const topics: WordCloudTopicItem[] = wordcloudData?.topics || [];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Automated Word Cloud & Topic Identification Module"
        titleKey="page.analytics.title"
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
          {topics.length > 0 ? (
            <WordCloudTagCloud topics={topics} />
          ) : (
            <Card className="border-[#30383D] bg-[#1C2226] p-6 text-sm text-[#9BA5A8]">
              No persisted corpus terms are available for this scope.
            </Card>
          )}

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
                    Terms and topics are derived from persisted indexed evidence for the selected scope. Supporting evidence remains available through the underlying document/page references.
                  </p>

                  <div className="grid grid-cols-2 gap-3 pt-4 border-t border-[#30383D] text-xs font-mono">
                    <div className="p-3 bg-[#242C30] rounded-lg border border-[#30383D]">
                      <span className="text-[#9BA5A8] block text-[10px]">Corpus Items</span>
                      <span className="text-lg font-bold text-[#C58B3A] mt-1 block">{wordcloudData?.corpus_items ?? 0}</span>
                    </div>

                    <div className="p-3 bg-[#242C30] rounded-lg border border-[#30383D]">
                      <span className="text-[#9BA5A8] block text-[10px]">Derived Topics</span>
                      <span className="text-lg font-bold text-[#4F8A62] mt-1 block">{corpusTopics?.topics.length ?? 0}</span>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>

          <Card className="border-[#30383D] bg-[#1C2226]">
            <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D]">
              <CardTitle className="text-sm font-bold text-[#E8ECEB]">Corpus topics and supporting evidence</CardTitle>
            </CardHeader>
            <CardContent className="p-4">
              {corpusTopics?.topics?.length ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {corpusTopics.topics.map((topic) => (
                    <div key={topic.topic_id} className="rounded-lg border border-[#30383D] bg-[#151A1D] p-3">
                      <div className="font-semibold text-[#E8ECEB]">{topic.name}</div>
                      <div className="mt-1 text-xs text-[#9BA5A8]">{topic.representative_terms.join(' · ')}</div>
                      <div className="mt-2 text-[11px] text-[#9BA5A8]">{topic.document_count} document(s), {topic.chunk_count} supporting chunk(s)</div>
                      {topic.evidence.slice(0, 2).map((evidence) => (
                        <div key={`${topic.topic_id}-${evidence.document_id}-${evidence.page_number ?? 'page'}`} className="mt-1 text-[11px] text-[#54788A]">
                          Document {evidence.document_id}{evidence.page_number ? ` · Page ${evidence.page_number}` : ''}
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              ) : <div className="text-sm text-[#9BA5A8]">No corpus-supported topics are available for this scope.</div>}
            </CardContent>
          </Card>

          <Card className="border-[#30383D] bg-[#1C2226]">
            <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D]">
              <CardTitle className="text-sm font-bold text-[#E8ECEB]">Production history</CardTitle>
              <p className="text-xs text-[#9BA5A8]">Persisted structured observations by period. Annual values are not summed across years.</p>
            </CardHeader>
            <CardContent className="p-0 overflow-x-auto">
              {productionTrend?.points?.length ? (
                <table className="w-full text-left text-xs font-mono">
                  <thead><tr className="border-b border-[#30383D] text-[#9BA5A8]"><th className="p-3">Entity</th><th className="p-3">Period</th><th className="p-3">Value</th><th className="p-3">Unit</th><th className="p-3">State</th></tr></thead>
                  <tbody>{productionTrend.points.map((point) => <tr key={`${point.entity}-${point.period}-${point.fact_ids.join('-')}`} className="border-b border-[#30383D]"><td className="p-3">{point.entity}</td><td className="p-3">{point.period}</td><td className="p-3">{point.value ?? 'Unavailable'}</td><td className="p-3">{point.unit}</td><td className="p-3">{point.status}</td></tr>)}</tbody>
                </table>
              ) : <div className="p-6 text-sm text-[#9BA5A8]">No comparable persisted production observations are available.</div>}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

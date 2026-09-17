'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { ErrorState } from '@/components/ui/ErrorState';
import { ReportWizardForm } from '@/components/reports/ReportWizardForm';
import { ReportPreviewCard } from '@/components/reports/ReportPreviewCard';
import { ReportHistoryTable } from '@/components/reports/ReportHistoryTable';
import { reportApi, ReportItem } from '@/lib/api/reportApi';
import { useScope } from '@/context/ScopeContext';
import { FileSpreadsheet } from 'lucide-react';

export default function ReportsPage() {
  const { selectedSubsidiary } = useScope();
  const queryClient = useQueryClient();
  const [selectedReport, setSelectedReport] = useState<ReportItem | null>(null);

  // Query: Get report history list
  const {
    data: reports = [],
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['reports', selectedSubsidiary],
    queryFn: () => reportApi.getReports(selectedSubsidiary),
    staleTime: 30000,
  });

  // Mutation: Generate Report
  const generateMutation = useMutation({
    mutationFn: (payload: { report_type: string; fiscal_year?: string; subsidiary?: string; title?: string }) =>
      reportApi.generateReport(payload),
    onSuccess: (newReport) => {
      setSelectedReport(newReport);
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });

  // Mutation: Approve Report
  const approveMutation = useMutation({
    mutationFn: (id: number) => reportApi.approveReport(id),
    onSuccess: (updatedReport) => {
      setSelectedReport(updatedReport);
      queryClient.invalidateQueries({ queryKey: ['reports'] });
    },
  });

  const activeReport = selectedReport || (reports.length > 0 ? reports[0] : null);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        title="Institutional Report Assembly Wizard"
        description="Automated compilation of Parliamentary Inquiry Replies, Annual Summaries, and Production Audits rendered via Python ReportLab engine."
        breadcrumbs={[{ label: 'Report Wizard' }]}
        badge={<Badge variant="amber">ReportLab Engine</Badge>}
      />

      {/* Error Alert */}
      {isError && <ErrorState message={error instanceof Error ? error.message : 'Failed to fetch report history.'} />}

      {/* Main Grid: Config Form & Draft Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        <div className="lg:col-span-5">
          <ReportWizardForm
            onGenerate={(payload) => generateMutation.mutate(payload)}
            isLoading={generateMutation.isPending}
          />
        </div>

        <div className="lg:col-span-7">
          <ReportPreviewCard
            report={activeReport}
            onApprove={() => activeReport && approveMutation.mutate(activeReport.id)}
            isApproving={approveMutation.isPending}
          />
        </div>
      </div>

      {/* Report History Table */}
      <ReportHistoryTable
        reports={reports}
        loading={isLoading}
        onSelectReport={(r) => setSelectedReport(r)}
      />
    </div>
  );
}

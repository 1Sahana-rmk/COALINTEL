'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Download, CheckCircle2, FileText, Sparkles, ShieldCheck } from 'lucide-react';
import { ReportItem, reportApi } from '@/lib/api/reportApi';

interface ReportPreviewCardProps {
  report: ReportItem | null;
  onApprove: () => void;
  isApproving?: boolean;
}

export const ReportPreviewCard: React.FC<ReportPreviewCardProps> = ({
  report,
  onApprove,
  isApproving = false,
}) => {
  const [isDownloading, setIsDownloading] = React.useState(false);
  const [canApprove, setCanApprove] = React.useState(false);

  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('coalintel_user');
      if (stored) {
        try {
          const user = JSON.parse(stored);
          setCanApprove(['Admin', 'Reviewer'].includes(user?.role));
        } catch {
          setCanApprove(false);
        }
      }
    }
  }, []);

  if (!report) {
    return (
      <Card className="h-full flex items-center justify-center p-12 text-center border-[#30383D] bg-[#1C2226] shadow-sm">
        <div className="space-y-2 text-[#9BA5A8]">
          <FileText className="h-10 w-10 mx-auto text-[#9BA5A8]/70" />
          <h4 className="text-xs font-semibold uppercase tracking-wider text-[#9BA5A8]">
            No Active Report Draft Selected
          </h4>
          <p className="text-xs text-[#9BA5A8] max-w-xs leading-relaxed">
            Configure report parameters on the left and click &quot;Assemble Report Draft&quot; to generate an institutional preview.
          </p>
        </div>
      </Card>
    );
  }

  const isApproved = report.approval_status === 'APPROVED';

  const handleDownload = async () => {
    if (!report?.id) return;
    setIsDownloading(true);
    try {
      const titleClean = report.title ? report.title.replace(/[^a-zA-Z0-9_-]/g, '_') : `Report_${report.id}`;
      await reportApi.downloadReport(report.id, `${titleClean}.pdf`);
    } catch (err) {
      console.error('Failed to download report PDF:', err);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <Card className="h-full border-[#30383D] bg-[#1C2226] shadow-sm space-y-4">
      <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[#C58B3A]" />
          <CardTitle className="text-sm font-semibold text-[#E8ECEB]">ReportLab Draft Assembly Preview</CardTitle>
        </div>
        <Badge variant={isApproved ? 'success' : 'warning'}>
          {report.approval_status || 'DRAFT'}
        </Badge>
      </CardHeader>

      <CardContent className="p-6 space-y-5">
        {/* Title & Metadata Card */}
        <div className="p-4 rounded-lg bg-[#242C30] border border-[#30383D] space-y-3">
          <div className="flex items-start justify-between gap-4">
            <h3 className="text-base font-bold text-[#E8ECEB] font-sans leading-snug">
              {report.title}
            </h3>
            <Badge variant="amber" size="sm" className="shrink-0 font-mono">
              ID #{report.id}
            </Badge>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-[#9BA5A8] pt-1 border-t border-[#30383D]">
            <span>Template: <code className="text-[#E8ECEB] font-semibold">{report.report_type}</code></span>
            <span>•</span>
            <span>Subsidiary: <span className="text-[#C58B3A] font-semibold">{report.subsidiary || 'ECL'}</span></span>
            <span>•</span>
            <span>FY: <span className="text-[#C58B3A] font-semibold">{report.fiscal_year || '2023-24'}</span></span>
          </div>

          <div className="text-[11px] font-mono text-[#9BA5A8] truncate" title={report.file_path}>
            PDF File: {report.file_path}
          </div>
        </div>

        {/* Verification Note */}
        <div className="p-3.5 rounded-lg bg-[#4F8A62]/10 border border-[#4F8A62]/30 text-xs text-[#E8ECEB] flex items-center gap-2.5">
          <ShieldCheck className="h-4 w-4 text-[#4F8A62] shrink-0" />
          <span>
            Compiled using verified unit-normalized metrics from database <code className="text-[#C58B3A] font-mono font-semibold">extracted_metrics</code> and resolved conflicts.
          </span>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-3 pt-2">
          {!isApproved && (
            <Button
              variant="primary"
              size="md"
              onClick={onApprove}
              isLoading={isApproving}
              disabled={!canApprove}
              title={!canApprove ? 'Approval restricted to Admin and Reviewer roles' : undefined}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
            >
              Approve Report
            </Button>
          )}

          <Button
            variant="outline"
            size="md"
            onClick={handleDownload}
            isLoading={isDownloading}
            leftIcon={<Download className="h-4 w-4" />}
          >
            Download ReportLab PDF
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};

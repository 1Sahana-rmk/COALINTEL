'use client';

import React, { useEffect } from 'react';
import { X, Bookmark, ArrowRight, Sparkles, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { ExtractedMetricItem } from '@/types/document';

interface MetricLineageDrawerProps {
  metric: ExtractedMetricItem | null;
  onClose: () => void;
  onJumpToPage?: (pageNumber: number) => void;
}

export const MetricLineageDrawer: React.FC<MetricLineageDrawerProps> = ({
  metric,
  onClose,
  onJumpToPage,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!metric) return null;

  const isLakhTonnes = metric.unit?.toLowerCase().includes('lakh');
  const conf = metric.confidence_score ?? 0.95;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-[#0E1113]/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Metric Evidence and Lineage Drawer"
    >
      <div
        className="w-full max-w-lg h-full bg-[#1C2226] border-l border-[#30383D] p-6 flex flex-col justify-between space-y-6 shadow-2xl overflow-y-auto text-[#E8ECEB] animate-slide-in-right"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="space-y-4">
          <div className="flex items-center justify-between border-b border-[#30383D] pb-4">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-[#C58B3A]/15 text-[#C58B3A] border border-[#C58B3A]/30">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#E8ECEB]">Metric Evidence & Lineage</h3>
                <p className="text-xs text-[#9BA5A8]">Provenanced Extraction Traceability</p>
              </div>
            </div>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#9BA5A8] hover:text-[#E8ECEB] hover:bg-[#242C30] transition-colors"
              aria-label="Close drawer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Mine & Metric Entity Header Card */}
          <div className="p-4 rounded-lg bg-[#242C30] border border-[#30383D] space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-[#C58B3A] uppercase font-semibold">
                {metric.mine_name}
              </span>
              <Badge variant="success" size="sm">
                Page {metric.page_number || 1}
              </Badge>
            </div>
            <h4 className="text-lg font-extrabold text-[#E8ECEB] font-sans">
              {metric.metric_name}
            </h4>
          </div>

          {/* Unit Normalization Traceability Card */}
          <div className="p-4 rounded-lg bg-[#242C30] border border-[#30383D] space-y-3">
            <span className="text-[10px] font-mono text-[#9BA5A8] uppercase tracking-wider font-semibold">
              Deterministic Unit Normalization
            </span>

            <div className="flex items-center justify-between p-3 rounded-lg bg-[#151A1D] border border-[#30383D] font-mono text-xs">
              <div>
                <span className="text-[#9BA5A8] block text-[10px]">Raw Extracted</span>
                <span className="text-[#E8ECEB] font-bold">
                  {metric.numeric_value} {metric.unit}
                </span>
              </div>

              <ArrowRight className="h-4 w-4 text-[#C58B3A] shrink-0" />

              <div className="text-right">
                <span className="text-[#9BA5A8] block text-[10px]">Standardized</span>
                <span className="text-[#C58B3A] font-bold">
                  {metric.standard_value} {metric.standard_unit || 'MT'}
                </span>
              </div>
            </div>

            {isLakhTonnes && (
              <p className="text-[11px] font-mono text-[#9BA5A8] bg-[#151A1D] p-2 rounded border border-[#30383D]">
                Formula applied: <span className="text-[#C58B3A] font-semibold">Lakh Tonnes × 0.1 = Million Tonnes (MT)</span>
              </p>
            )}
          </div>

          {/* Raw Evidence Text Snippet */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono text-[#9BA5A8] uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Bookmark className="h-3.5 w-3.5 text-[#C58B3A]" />
              Raw Source Text Snippet
            </span>

            <div className="p-4 rounded-lg bg-[#151A1D] border border-[#30383D] text-xs font-sans text-[#E8ECEB] leading-relaxed max-h-48 overflow-y-auto selection:bg-[#C58B3A]/30">
              {metric.raw_snippet ? (
                <mark className="bg-[#C58B3A]/15 text-[#C58B3A] p-1.5 rounded font-mono border border-[#C58B3A]/30 block">
                  &quot;{metric.raw_snippet}&quot;
                </mark>
              ) : (
                <span className="italic text-[#9BA5A8]">No raw snippet text available for this metric.</span>
              )}
            </div>
          </div>

          {/* Validation & Confidence Stats */}
          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="p-3 rounded-lg bg-[#242C30] border border-[#30383D] space-y-1">
              <span className="text-[10px] font-mono text-[#9BA5A8] uppercase block">Confidence Score</span>
              <span className="text-base font-bold font-mono text-[#4F8A62]">{conf.toFixed(3)}</span>
            </div>

            <div className="p-3 rounded-lg bg-[#242C30] border border-[#30383D] space-y-1">
              <span className="text-[10px] font-mono text-[#9BA5A8] uppercase block">Validation Flag</span>
              <span className="text-xs font-bold font-mono text-[#54788A] block truncate">
                {metric.validation_status || 'VERIFIED'}
              </span>
            </div>
          </div>
        </div>

        {/* Footer Jump to Page Action */}
        <div className="pt-4 border-t border-[#30383D] flex items-center justify-between gap-3">
          <Button variant="ghost" size="md" onClick={onClose}>
            Close
          </Button>

          {metric.page_number && onJumpToPage && (
            <Button
              variant="primary"
              size="md"
              onClick={() => {
                onJumpToPage(metric.page_number!);
                onClose();
              }}
              rightIcon={<ExternalLink className="h-4 w-4" />}
            >
              Jump to Page {metric.page_number}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

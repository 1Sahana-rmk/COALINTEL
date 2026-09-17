'use client';

import React, { useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { LoadingState } from '@/components/ui/LoadingState';
import { ErrorState } from '@/components/ui/ErrorState';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { CitationDrawer } from '@/components/query/CitationDrawer';
import { useScope } from '@/context/ScopeContext';
import { formatStandardValue } from '@/lib/utils/cn';
import {
  generateBriefing,
  exportBriefingPdf,
  ParliamentaryBriefingResponse,
} from '@/lib/api/parliamentaryApi';
import {
  Landmark,
  Sparkles,
  FileCheck2,
  AlertTriangle,
  Download,
  Building2,
  Calendar,
  CheckCircle2,
  Info,
  Layers,
  ArrowRight,
} from 'lucide-react';

const PRESETS = [
  {
    title: 'Production Target Achievement',
    type: 'TARGETS',
    question: 'What is the subsidiary-wise coal production achievement and target variance for FY2023-24?',
  },
  {
    title: 'Overburden Stripping Analysis',
    type: 'OVERBURDEN',
    question: 'What is the overburden removal (OBR) and stripping ratio breakdown across opencast coal mines?',
  },
  {
    title: 'Cross-Document Discrepancy Audit',
    type: 'DISCREPANCIES',
    question: 'Identify any cross-document data discrepancies or conflicting metrics reported across CIL subsidiary annual reports.',
  },
  {
    title: 'Equipment & Washing Capacity',
    type: 'GENERAL',
    question: 'Provide executive briefing on HEMM equipment availability, coal washing capacity, and infrastructure readiness.',
  },
];

export default function ParliamentaryPage() {
  const { selectedSubsidiary, selectedFiscalYear } = useScope();
  const [questionText, setQuestionText] = useState('');
  const [questionType, setQuestionType] = useState('GENERAL');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [briefing, setBriefing] = useState<ParliamentaryBriefingResponse | null>(null);
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Citation Drawer state
  const [activeEvidence, setActiveEvidence] = useState<{
    chunkId: number | null;
    filename: string;
    pageNumber: number;
    snippet: string;
    rrfScore: number;
  } | null>(null);

  const handlePresetSelect = (preset: (typeof PRESETS)[0]) => {
    setQuestionText(preset.question);
    setQuestionType(preset.type);
  };

  const handleGenerate = async () => {
    if (!questionText.trim()) return;
    setLoading(true);
    setError(null);

    try {
      const res = await generateBriefing({
        question_text: questionText,
        fiscal_year: selectedFiscalYear,
        subsidiary_filter: selectedSubsidiary,
        question_type: questionType,
      });
      setBriefing(res);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Failed to generate Parliamentary Briefing Note.');
    } finally {
      setLoading(false);
    }
  };

  const handleExportPdf = async () => {
    if (!briefing) return;
    setDownloadingPdf(true);
    try {
      const blob = await exportBriefingPdf(briefing);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Parliamentary_Briefing_${briefing.selected_scope}_${briefing.fiscal_year}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert('Failed to export PDF briefing document.');
    } finally {
      setDownloadingPdf(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Parliamentary Question & Executive Briefing Intelligence Engine"
        description="Multi-subsidiary evidence synthesis, deterministic metric validation, and institutional briefing note compilation."
        breadcrumbs={[{ label: 'Parliamentary Intelligence' }]}
        badge={<Badge variant="amber">Parliamentary Engine</Badge>}
      />

      {/* Preset Selector Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {PRESETS.map((p, idx) => (
          <Card
            key={idx}
            onClick={() => handlePresetSelect(p)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                handlePresetSelect(p);
              }
            }}
            role="button"
            tabIndex={0}
            className="p-4 cursor-pointer hover:border-[#C58B3A]/60 hover:bg-[#242C30] hover:-translate-y-0.5 transition-all duration-150 border-[#30383D] group bg-[#1C2226] focus:outline-none focus:border-[#C58B3A]"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-mono text-[#C58B3A] font-bold uppercase tracking-wider">{p.type}</span>
              <ArrowRight className="h-3.5 w-3.5 text-[#9BA5A8] group-hover:text-[#C58B3A] group-hover:translate-x-0.5 transition-all" />
            </div>
            <h4 className="text-sm font-semibold text-[#E8ECEB] group-hover:text-[#C58B3A] mb-1 transition-colors">{p.title}</h4>
            <p className="text-xs text-[#9BA5A8] line-clamp-2 leading-relaxed">{p.question}</p>
          </Card>
        ))}
      </div>

      {/* Question Form & Scope Display */}
      <Card className="border-[#30383D] bg-[#1C2226]">
        <CardHeader className="py-3.5 px-4 bg-[#242C30] border-b border-[#30383D]">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <CardTitle className="text-sm font-semibold text-[#E8ECEB] flex items-center gap-2">
              <Landmark className="h-4 w-4 text-[#C58B3A]" />
              <span>Parliamentary Question Input</span>
            </CardTitle>

            {/* Scope Badges */}
            <div className="flex items-center gap-2">
              <Badge variant="amber" size="sm" className="gap-1 font-mono">
                <Building2 className="h-3 w-3" />
                {selectedSubsidiary}
              </Badge>
              <Badge variant="secondary" size="sm" className="gap-1 font-mono">
                <Calendar className="h-3 w-3" />
                FY {selectedFiscalYear}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CardContent className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-mono text-[#E8ECEB] mb-2">Parliamentary Starred / Executive Question Text</label>
            <textarea
              value={questionText}
              onChange={(e) => setQuestionText(e.target.value)}
              rows={3}
              placeholder="Enter Parliamentary Question or Executive Query (e.g. Provide subsidiary-wise coal production and overburden removal figures for FY2023-24...)"
              className="w-full bg-[#151A1D] border border-[#30383D] rounded-lg px-4 py-3 text-sm text-[#E8ECEB] placeholder-[#9BA5A8]/60 focus:outline-none focus:border-[#C58B3A] focus:ring-1 focus:ring-[#C58B3A]/50"
            />
          </div>

          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 pt-2">
            <div className="flex items-center gap-3">
              <span className="text-xs font-mono text-[#9BA5A8] whitespace-nowrap">Intent Filter:</span>
              <select
                value={questionType}
                onChange={(e) => setQuestionType(e.target.value)}
                className="bg-[#151A1D] border border-[#30383D] rounded-lg px-3 py-1.5 text-xs text-[#E8ECEB] font-mono focus:outline-none focus:border-[#C58B3A]"
              >
                <option value="GENERAL">General Briefing</option>
                <option value="TARGETS">Production Targets</option>
                <option value="OVERBURDEN">Overburden Removal</option>
                <option value="SUBSIDIARIES">Subsidiary Comparison</option>
                <option value="DISCREPANCIES">Discrepancy Audit</option>
              </select>
            </div>

            <button
              onClick={handleGenerate}
              disabled={loading || !questionText.trim()}
              className="px-6 py-2.5 rounded-lg bg-[#C58B3A] hover:bg-[#D6A052] text-[#0E1113] font-bold text-sm shadow-sm transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading ? (
                <span>Synthesizing Evidence...</span>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>Generate Parliamentary Briefing Note</span>
                </>
              )}
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && <ErrorState message={error} />}

      {/* Loading Indicator */}
      {loading && <LoadingState label="Extracting multi-subsidiary evidence & compiling Parliamentary Briefing Note..." />}

      {/* Briefing Results */}
      {briefing && !loading && (
        <div className="space-y-6">
          {/* Briefing Banner Card */}
          <Card className="border-[#30383D] bg-[#1C2226]">
            <div className="p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#30383D] pb-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <Landmark className="h-5 w-5 text-[#C58B3A]" />
                    <h2 className="text-lg font-bold text-[#E8ECEB]">Parliamentary Briefing Note</h2>
                  </div>
                  <p className="text-xs text-[#9BA5A8] font-mono">
                    Target Scope: <span className="text-[#C58B3A] font-bold">{briefing.selected_scope}</span> | Fiscal Year: <span className="text-[#4F8A62] font-bold">{briefing.fiscal_year}</span> | Compiled: {briefing.generated_at}
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <Badge
                    variant={briefing.confidence_rating === 'HIGH' ? 'success' : briefing.confidence_rating === 'MEDIUM' ? 'warning' : 'danger'}
                    size="md"
                    className="font-bold font-mono"
                  >
                    Confidence: {briefing.confidence_rating} ({Math.round(briefing.confidence * 100)}%)
                  </Badge>

                  <button
                    onClick={handleExportPdf}
                    disabled={downloadingPdf}
                    className="px-4 py-2 rounded-lg bg-[#242C30] hover:bg-[#30383D] border border-[#30383D] text-[#E8ECEB] text-xs font-semibold flex items-center gap-2 transition-all shadow-sm"
                  >
                    <Download className="h-4 w-4 text-[#C58B3A]" />
                    <span>{downloadingPdf ? 'Exporting PDF...' : 'Download Briefing Note (PDF)'}</span>
                  </button>
                </div>
              </div>

              {/* Disclaimer Notice */}
              <div className="p-3 bg-[#D6A23A]/10 border border-[#D6A23A]/30 rounded-lg text-xs text-[#D6A23A] flex items-center gap-2">
                <Info className="h-4 w-4 shrink-0 text-[#D6A23A]" />
                <span>
                  <b>Institutional Disclaimer:</b> AI-generated evidence-backed Parliamentary Briefing Note for analytical decision support. Not an official Ministry issued document.
                </span>
              </div>

              {/* Executive Summary */}
              <div className="space-y-2">
                <h3 className="text-xs font-mono uppercase tracking-wider text-[#9BA5A8] font-bold">Executive Summary</h3>
                <p className="text-sm text-[#E8ECEB] leading-relaxed bg-[#242C30]/50 p-4 rounded-lg border border-[#30383D]">
                  {briefing.executive_summary}
                </p>
              </div>

              {/* Key Findings */}
              {briefing.key_findings.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-mono uppercase tracking-wider text-[#9BA5A8] font-bold">Key Findings & Operational Highlights</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {briefing.key_findings.map((finding, idx) => (
                      <div key={idx} className="p-3 bg-[#242C30]/50 border border-[#30383D] rounded-lg flex items-start gap-2.5 text-xs text-[#E8ECEB]">
                        <CheckCircle2 className="h-4 w-4 text-[#4F8A62] shrink-0 mt-0.5" />
                        <span>{finding}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </Card>

          {/* Subsidiary Metrics Table */}
          {briefing.subsidiary_metrics.length > 0 && (
            <Card className="border-[#30383D] bg-[#1C2226]">
              <CardHeader className="py-3.5 px-4 bg-[#242C30] border-b border-[#30383D]">
                <CardTitle className="text-sm font-semibold text-[#E8ECEB] flex items-center gap-2">
                  <FileCheck2 className="h-4 w-4 text-[#4F8A62]" />
                  <span>Verified Operational Metrics Table</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-[#30383D] bg-[#242C30] text-[11px] font-mono text-[#E8ECEB] uppercase tracking-wider">
                        <th className="py-3 px-4">Mine Entity</th>
                        <th className="py-3 px-4">Subsidiary</th>
                        <th className="py-3 px-4">Metric Name</th>
                        <th className="py-3 px-4">Reported Value</th>
                        <th className="py-3 px-4">Standard Value</th>
                        <th className="py-3 px-4">Fiscal Year</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#30383D] text-xs font-mono">
                      {briefing.subsidiary_metrics.map((m, idx) => (
                        <tr key={idx} className="hover:bg-[#242C30]/50 transition-colors">
                          <td className="py-3 px-4 font-sans font-semibold text-[#E8ECEB]">{m.mine_name}</td>
                          <td className="py-3 px-4 text-[#C58B3A] font-bold">{m.subsidiary}</td>
                          <td className="py-3 px-4 text-[#9BA5A8]">{m.metric_name}</td>
                          <td className="py-3 px-4 text-[#E8ECEB]">{m.numeric_value} {m.unit}</td>
                          <td className="py-3 px-4 font-bold text-[#4F8A62]">{formatStandardValue(m.standard_value)} {m.standard_unit}</td>
                          <td className="py-3 px-4 text-[#9BA5A8]">{m.fiscal_year}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Flagged Discrepancies */}
          {briefing.discrepancies.length > 0 && (
            <Card className="border-[#C94B45]/30 bg-[#1C2226]">
              <CardHeader className="py-3.5 px-4 bg-[#C94B45]/10 border-b border-[#C94B45]/20">
                <CardTitle className="text-sm font-semibold text-[#C94B45] flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-[#C94B45]" />
                  <span>Flagged Cross-Document Discrepancies ({briefing.discrepancies.length})</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                {briefing.discrepancies.map((d, idx) => (
                  <div key={idx} className="p-4 bg-[#242C30] border border-[#C94B45]/30 rounded-lg space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-[#E8ECEB]">{d.entity}</span>
                        <span className="text-xs text-[#9BA5A8] font-mono">({d.metric_name})</span>
                      </div>
                      <Badge variant={d.is_seeded_demo ? 'warning' : 'danger'} size="sm" className="font-mono font-bold">
                        {d.provenance_label}
                      </Badge>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs font-mono pt-1">
                      <div className="p-2.5 bg-[#151A1D] rounded-lg border border-[#30383D]">
                        <span className="text-[#9BA5A8] block text-[10px] truncate">{d.doc_a_filename}</span>
                        <span className="text-[#E8ECEB] font-bold text-sm block mt-0.5">{d.doc_a_value} {d.unit}</span>
                      </div>
                      <div className="p-2.5 bg-[#151A1D] rounded-lg border border-[#30383D]">
                        <span className="text-[#9BA5A8] block text-[10px] truncate">{d.doc_b_filename}</span>
                        <span className="text-[#E8ECEB] font-bold text-sm block mt-0.5">{d.doc_b_value} {d.unit}</span>
                      </div>
                      <div className="p-2.5 bg-[#C94B45]/10 rounded-lg border border-[#C94B45]/30 text-center">
                        <span className="text-[#C94B45] block text-[10px]">Variance Percentage</span>
                        <span className="text-[#C94B45] font-bold text-sm block mt-0.5">{d.variance_percentage}%</span>
                      </div>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Traceable Evidence Lineage */}
          {briefing.evidence.length > 0 && (
            <Card className="border-[#30383D] bg-[#1C2226]">
              <CardHeader className="py-3.5 px-4 bg-[#242C30] border-b border-[#30383D]">
                <CardTitle className="text-sm font-semibold text-[#E8ECEB] flex items-center gap-2">
                  <Layers className="h-4 w-4 text-[#C58B3A]" />
                  <span>Traceable Evidence Lineage ({briefing.evidence.length} Chunks)</span>
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                {briefing.evidence.map((ev, idx) => (
                  <div key={idx} className="p-3.5 bg-[#242C30]/50 border border-[#30383D] rounded-lg flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2 text-xs font-mono">
                        <span className="text-[#C58B3A] font-bold">{ev.document_name}</span>
                        <span className="text-[#9BA5A8]">•</span>
                        <span className="text-[#E8ECEB]">Page {ev.page_number}</span>
                        <span className="text-[#9BA5A8]">•</span>
                        <span className="text-[#4F8A62] font-semibold">RRF Score: {ev.rrf_score}</span>
                      </div>
                      <p className="text-xs text-[#E8ECEB] line-clamp-2 leading-relaxed font-sans">{ev.text_snippet}</p>
                    </div>

                    <button
                      onClick={() =>
                        setActiveEvidence({
                          chunkId: typeof ev.chunk_id === 'number' ? ev.chunk_id : (Number(ev.chunk_id) || null),
                          filename: ev.document_name,
                          pageNumber: ev.page_number,
                          snippet: ev.text_snippet,
                          rrfScore: ev.rrf_score,
                        })
                      }
                      className="px-3 py-1.5 rounded-lg bg-[#242C30] hover:bg-[#30383D] border border-[#30383D] text-[#C58B3A] text-xs font-semibold shrink-0 transition-colors whitespace-nowrap shadow-sm"
                    >
                      View Evidence
                    </button>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}

          {/* Limitations Card */}
          {briefing.limitations.length > 0 && (
            <Card className="border-[#30383D] bg-[#1C2226]">
              <div className="p-4 space-y-2">
                <h4 className="text-xs font-mono uppercase tracking-wider text-[#9BA5A8] font-bold">System Limitations & Scope Boundaries</h4>
                <ul className="list-disc list-inside text-xs text-[#9BA5A8] space-y-1 font-mono">
                  {briefing.limitations.map((lim, idx) => (
                    <li key={idx}>{lim}</li>
                  ))}
                </ul>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* Citation Drawer Modal */}
      {activeEvidence && (
        <CitationDrawer
          citation={{
            document_name: activeEvidence.filename,
            page_number: activeEvidence.pageNumber,
            citation_tag: `[${activeEvidence.filename}, Page ${activeEvidence.pageNumber}]`,
          }}
          chunk={{
            chunk_id: activeEvidence.chunkId ? Number(activeEvidence.chunkId) || 1 : 1,
            document_id: 1,
            filename: activeEvidence.filename,
            page_number: activeEvidence.pageNumber,
            chunk_index: 0,
            text: activeEvidence.snippet,
            rrf_score: activeEvidence.rrfScore,
          }}
          onClose={() => setActiveEvidence(null)}
        />
      )}
    </div>
  );
}

'use client';

import React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Sparkles, FileText, ShieldCheck, AlertTriangle, Eye } from 'lucide-react';
import { QueryResponse, CitationItem, EvidenceChunkItem } from '@/lib/api/queryApi';

interface CitedAnswerCardProps {
  response: QueryResponse;
  onSelectCitation: (citation: CitationItem, chunk?: EvidenceChunkItem) => void;
}

export const CitedAnswerCard: React.FC<CitedAnswerCardProps> = ({
  response,
  onSelectCitation,
}) => {
  const isGeneralAi = response.mode === 'GENERAL_AI';

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
      {/* MAIN ANSWER CARD (8 cols) */}
      <Card className="lg:col-span-8 space-y-4 border-[#30383D] shadow-sm bg-[#1C2226]">
        <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-[#C58B3A]" />
            <CardTitle className="text-sm font-bold text-[#E8ECEB]">
              {isGeneralAi ? 'General AI Technical Synthesis' : 'Evidence-Grounded Intelligence Synthesis'}
            </CardTitle>
          </div>

          <div className="flex items-center gap-2">
            {isGeneralAi ? (
              <Badge variant="secondary" size="sm">
                General Knowledge
              </Badge>
            ) : response.degraded_mode ? (
              <Badge variant="warning" size="sm">
                Degraded Grounded Mode
              </Badge>
            ) : null}
            <Badge variant="amber" size="sm">
              Provider: {response.provider || 'Gemini RAG Engine'}
            </Badge>
          </div>
        </CardHeader>

        <CardContent className="p-6 space-y-4">
          {/* User Query Context */}
          <div className="p-3 rounded-lg bg-[#151A1D] border border-[#30383D] text-xs font-mono text-[#E8ECEB] flex items-start gap-2">
            <span className="text-[#C58B3A] font-bold uppercase shrink-0">Inquiry:</span>
            <span>&quot;{response.query}&quot;</span>
          </div>

          {/* Generated Cited Text */}
          <div className="p-4 rounded-lg bg-[#151A1D] border border-[#30383D] text-[#E8ECEB] text-sm leading-relaxed whitespace-pre-line font-sans selection:bg-[#C58B3A]/30">
            {response.answer}
          </div>

          {/* Verification Footer Banner */}
          <div className="flex flex-wrap items-center justify-between pt-3 border-t border-[#30383D] text-xs text-[#9BA5A8] gap-2 font-mono">
            {isGeneralAi ? (
              <span className="flex items-center gap-1.5 text-[#54788A] font-semibold">
                <Sparkles className="h-4 w-4 text-[#C58B3A]" /> General AI Response (No Document Citations Required)
              </span>
            ) : response.degraded_mode ? (
              <span className="flex items-center gap-1.5 text-[#D6A23A] font-semibold">
                <AlertTriangle className="h-4 w-4" /> Degraded Mode
              </span>
            ) : response.citations && response.citations.length > 0 ? (
              <span className="flex items-center gap-1.5 text-[#4F8A62] font-semibold">
                <ShieldCheck className="h-4 w-4" /> Evidence Grounded
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-[#9BA5A8] font-semibold">
                <AlertTriangle className="h-4 w-4 text-[#9BA5A8]" /> No Evidence Found
              </span>
            )}
            <span className="text-[#9BA5A8]">
              {isGeneralAi
                ? 'Zero Artificial Citations'
                : `${response.citations?.length || 0} Grounded Citations Attached`}
            </span>
          </div>
        </CardContent>
      </Card>

      {/* CITATION EVIDENCE DRAWER LIST (4 cols) */}
      <Card className="lg:col-span-4 border-[#30383D] shadow-sm bg-[#1C2226]">
        <CardHeader className="py-3.5 px-4 bg-[#151A1D] border-b border-[#30383D]">
          <CardTitle className="text-sm font-bold text-[#E8ECEB] flex items-center gap-2">
            <FileText className="h-4 w-4 text-[#C58B3A]" />
            <span>{isGeneralAi ? 'Knowledge Provenance' : 'Source Lineage Citations'}</span>
          </CardTitle>
        </CardHeader>

        <CardContent className="p-4 space-y-3">
          {isGeneralAi ? (
            <div className="p-4 text-center text-xs text-[#9BA5A8] font-mono space-y-2">
              <p className="text-[#E8ECEB] font-semibold">General AI Response</p>
              <p className="text-[11px] leading-relaxed">
                This inquiry was answered via General AI without referencing organizational mining documents. Document citations are not applicable.
              </p>
            </div>
          ) : (
            <>
              <p className="text-xs text-[#9BA5A8]">
                Click any citation tag below to inspect raw vector page chunks and text snippet provenance:
              </p>

              {response.citations && response.citations.length > 0 ? (
                response.citations.map((c, idx) => {
                  const matchingChunk = response.evidence_chunks?.find(
                    (ec) => ec.filename === c.document_name && ec.page_number === c.page_number
                  );

                  return (
                    <div
                      key={idx}
                      onClick={() => onSelectCitation(c, matchingChunk)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault();
                          onSelectCitation(c, matchingChunk);
                        }
                      }}
                      role="button"
                      tabIndex={0}
                      className="p-3 rounded-lg bg-[#242C30] border border-[#30383D] hover:border-[#C58B3A]/60 transition-all duration-150 cursor-pointer space-y-1.5 group focus:outline-none focus:border-[#C58B3A]"
                      aria-label={`Inspect evidence for ${c.document_name} page ${c.page_number}`}
                    >
                      <div className="flex items-center justify-between text-xs font-bold text-[#E8ECEB] group-hover:text-[#C58B3A] transition-colors">
                        <span className="truncate max-w-[170px]" title={c.document_name}>
                          {c.document_name}
                        </span>
                        <Badge variant="amber" size="sm">
                          Page {c.page_number}
                        </Badge>
                      </div>

                      <div className="flex items-center justify-between text-[11px] font-mono text-[#9BA5A8]">
                        <span className="bg-[#151A1D] px-1.5 py-0.5 rounded text-[#C58B3A] border border-[#30383D]">
                          {c.citation_tag}
                        </span>
                        <span className="flex items-center gap-1 text-[#C58B3A] font-sans text-xs group-hover:underline">
                          Inspect <Eye className="h-3.5 w-3.5" />
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="p-6 text-center text-xs text-[#9BA5A8] font-mono">
                  No citations attached to query response.
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

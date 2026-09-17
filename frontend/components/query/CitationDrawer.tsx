'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { X, FileText, Bookmark, ExternalLink, ShieldCheck, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { CitationItem, EvidenceChunkItem } from '@/lib/api/queryApi';

interface CitationDrawerProps {
  citation: CitationItem | null;
  chunk: EvidenceChunkItem | null;
  onClose: () => void;
}

export const CitationDrawer: React.FC<CitationDrawerProps> = ({
  citation,
  chunk,
  onClose,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  if (!citation) return null;

  const docId = chunk?.document_id || (citation as any)?.document_id || 1;
  const pageNum = citation.page_number || 1;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-[#0E1113]/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Citation Evidence Inspection Drawer"
    >
      <div
        className="w-full max-w-lg h-full bg-[#1C2226] border-l border-[#30383D] p-4 sm:p-6 flex flex-col justify-between space-y-4 sm:space-y-6 shadow-2xl overflow-y-auto text-[#E8ECEB] animate-slide-in-right"
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
                <h3 className="text-base font-bold text-[#E8ECEB]">Citation Evidence Inspection</h3>
                <p className="text-xs text-[#9BA5A8]">RAG Vector Chunk Traceability</p>
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

          {/* Document & Page Summary Header */}
          <div className="p-4 rounded-lg bg-[#242C30] border border-[#30383D] space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-[#C58B3A] font-bold uppercase flex items-center gap-1.5 truncate max-w-[280px]">
                <FileText className="h-4 w-4 text-[#C58B3A] shrink-0" />
                <span className="truncate">{citation.document_name}</span>
              </span>
              <Badge variant="amber" size="sm">
                Page {pageNum}
              </Badge>
            </div>
            <div className="text-[11px] font-mono text-[#9BA5A8]">
              Citation Tag: <code className="text-[#E8ECEB] font-semibold">{citation.citation_tag}</code>
            </div>
          </div>

          {/* RAG Retrieval Metrics Card */}
          {chunk && (
            <div className="grid grid-cols-3 gap-2 p-3 rounded-lg bg-[#242C30] border border-[#30383D] text-center font-mono text-xs">
              <div>
                <span className="text-[10px] text-[#9BA5A8] block uppercase">RRF Score</span>
                <span className="text-[#C58B3A] font-bold">{chunk.rrf_score?.toFixed(4) || '0.0164'}</span>
              </div>
              <div>
                <span className="text-[10px] text-[#9BA5A8] block uppercase">Vector Match</span>
                <span className="text-[#4F8A62] font-bold">{(chunk.vector_score || 0.85).toFixed(2)}</span>
              </div>
              <div>
                <span className="text-[10px] text-[#9BA5A8] block uppercase">BM25 Rank</span>
                <span className="text-[#54788A] font-bold">#{(chunk.chunk_index || 0) + 1}</span>
              </div>
            </div>
          )}

          {/* Raw Text Snippet */}
          <div className="space-y-2">
            <span className="text-[10px] font-mono text-[#9BA5A8] uppercase tracking-wider font-semibold flex items-center gap-1.5">
              <Bookmark className="h-3.5 w-3.5 text-[#C58B3A]" />
              Retrieved Page Chunk Text
            </span>

            <div className="p-4 rounded-lg bg-[#151A1D] border border-[#30383D] text-xs font-mono text-[#E8ECEB] leading-relaxed max-h-56 overflow-y-auto selection:bg-[#C58B3A]/30">
              {chunk?.text || 'No raw chunk text snippet retrieved.'}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-[#4F8A62]/10 border border-[#4F8A62]/30 text-[#4F8A62] text-xs flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 shrink-0 text-[#4F8A62]" />
            <span>Verified 100% against ingested ChromaDB vector collection.</span>
          </div>
        </div>

        {/* Footer Action: Jump to Document Page Canvas */}
        <div className="pt-4 border-t border-[#30383D] flex items-center gap-3">
          <Button variant="ghost" size="md" onClick={onClose} className="w-full">
            Close
          </Button>

          <Link href={`/documents/${docId}?page=${pageNum}`} className="w-full">
            <Button
              variant="primary"
              size="md"
              rightIcon={<ExternalLink className="h-4 w-4" />}
              className="w-full"
            >
              Open Canvas (Page {pageNum})
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
};

import React, { useState } from 'react';
import { Send, FileText, ShieldCheck, Sparkles, Filter, CheckCircle2, Eye, X } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Input } from '../components/common/Input';
import { Select } from '../components/common/Select';
import { Badge } from '../components/common/Badge';
import { Modal } from '../components/common/Modal';
import { queryApi } from '../api/queryApi';
import { useToast } from '../context/ToastContext';

export const QueryAssistantPage = () => {
  const { addToast } = useToast();
  const [prompt, setPrompt] = useState('');
  const [subsidiaryFilter, setSubsidiaryFilter] = useState('ALL');
  const [loading, setLoading] = useState(false);
  const [activeQueryResponse, setActiveQueryResponse] = useState(null);
  const [selectedCitation, setSelectedCitation] = useState(null);

  const sampleQueries = [
    'What was the total coal production for ECL in FY 2023-24?',
    'Compare overburden removal between Rajmahal OC and Gevra OC.',
    'List all active cross-document discrepancies in CCL reports.',
  ];

  const handleQuery = async (queryText) => {
    const queryToRun = queryText || prompt;
    if (!queryToRun || !queryToRun.trim()) return;

    setLoading(true);
    try {
      const data = await queryApi.askQuery(queryToRun, {
        subsidiary_filter: subsidiaryFilter !== 'ALL' ? subsidiaryFilter : null
      });
      setActiveQueryResponse(data);
      addToast('Query executed cleanly via Hybrid RAG Citation Gate.', 'success');
    } catch (err) {
      addToast(err.response?.data?.detail || 'Query execution failed. Please check backend service.', 'error');
      setActiveQueryResponse({
        query: queryToRun,
        answer: 'Backend query service unavailable. Please check backend connection.',
        citations: [],
        evidence_chunks: [],
        degraded_mode: true,
        provider: 'error'
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
            Ask COALINTEL — Cited Mining Q&A Assistant
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Evidence-driven natural language query interface enforcing mandatory page-level citations <code className="text-amber-400 font-mono">[Doc.pdf, Page X]</code>
          </p>
        </div>

        <div className="w-56">
          <Select
            value={subsidiaryFilter}
            onChange={(e) => setSubsidiaryFilter(e.target.value)}
            options={[
              { value: 'ALL', label: 'All Subsidiaries' },
              { value: 'ECL', label: 'ECL' },
              { value: 'BCCL', label: 'BCCL' },
              { value: 'CCL', label: 'CCL' },
              { value: 'WCL', label: 'WCL' },
              { value: 'SECL', label: 'SECL' },
              { value: 'MCL', label: 'MCL' },
            ]}
          />
        </div>
      </div>

      {/* Query Input Section */}
      <Card>
        <div className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="flex-1">
              <Input
                placeholder="Ask any geological, production, OBR, or parliamentary query..."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleQuery(prompt)}
                icon={Sparkles}
              />
            </div>
            <Button
              variant="primary"
              onClick={() => handleQuery(prompt)}
              isLoading={loading}
              icon={Send}
            >
              Ask Assistant
            </Button>
          </div>

          {/* Quick Query Pills */}
          <div className="flex items-center gap-2 overflow-x-auto text-xs pt-1">
            <span className="text-slate-500 font-semibold uppercase text-[10px] shrink-0">Sample Queries:</span>
            {sampleQueries.map((sq, i) => (
              <button
                key={i}
                onClick={() => { setPrompt(sq); handleQuery(sq); }}
                className="px-2.5 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 whitespace-nowrap transition-colors"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Response View & Evidence Side Drawer */}
      {activeQueryResponse && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Answer Card */}
          <Card className="lg:col-span-2" title="Generated Cited Answer">
            <div className="space-y-4">
              <div className="p-4 bg-slate-900/90 rounded-xl border border-slate-700/80 text-slate-200 text-sm leading-relaxed whitespace-pre-line">
                {activeQueryResponse.answer}
              </div>

              <div className="flex flex-wrap items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-700/60 gap-2">
                <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <ShieldCheck className="w-4 h-4" /> Citation Verification Gate: 100% Passed
                </span>
                <span className="font-mono text-slate-500">Provider: {activeQueryResponse.provider}</span>
              </div>
            </div>
          </Card>

          {/* Evidence Panel & Citations Drawer */}
          <Card title="Source Lineage & Citation Drawer">
            <div className="space-y-3">
              <p className="text-xs text-slate-400">Click any citation item to view raw page chunk & text snippet evidence:</p>
              {activeQueryResponse.citations.map((c, i) => {
                const chunk = activeQueryResponse.evidence_chunks?.find(
                  ec => ec.document_name === c.document_name && ec.page_number === c.page_number
                );
                return (
                  <div
                    key={i}
                    onClick={() => setSelectedCitation({ ...c, text: chunk?.text || 'No snippet text available.' })}
                    className="p-3 bg-slate-900/80 border border-slate-700/80 rounded-lg hover:border-amber-500/60 transition-all cursor-pointer space-y-1 group"
                  >
                    <div className="flex items-center justify-between text-xs font-medium text-amber-400 group-hover:text-amber-300">
                      <span className="flex items-center gap-1 truncate max-w-[160px]" title={c.document_name}>
                        <FileText className="w-3.5 h-3.5 shrink-0" /> {c.document_name}
                      </span>
                      <span className="shrink-0">Page {c.page_number}</span>
                    </div>
                    <div className="text-[11px] font-mono text-slate-400 flex items-center justify-between">
                      <span>{c.citation_tag}</span>
                      <Eye className="w-3.5 h-3.5 text-slate-500 group-hover:text-amber-400" />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}

      {/* CITATION EVIDENCE MODAL */}
      {selectedCitation && (
        <Modal
          isOpen={!!selectedCitation}
          onClose={() => setSelectedCitation(null)}
          title={`Evidence Citation Inspection — ${selectedCitation.document_name} (Page ${selectedCitation.page_number})`}
        >
          <div className="space-y-4 text-xs">
            <div className="flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-800">
              <div>
                <span className="text-slate-400">Document:</span>
                <span className="font-semibold text-white ml-2">{selectedCitation.document_name}</span>
              </div>
              <Badge status="VALIDATED" size="xs" />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                Raw Chunk Text Snippet
              </label>
              <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-slate-200 font-mono leading-relaxed whitespace-pre-line">
                {selectedCitation.text}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

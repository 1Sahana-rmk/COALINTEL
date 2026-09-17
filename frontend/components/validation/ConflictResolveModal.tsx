'use client';

import React, { useState, useEffect } from 'react';
import { X, GitCompare, CheckCircle2, FileText, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Select } from '@/components/ui/Select';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { ConflictItem, ResolveConflictPayload } from '@/lib/api/validationApi';

interface ConflictResolveModalProps {
  conflict: ConflictItem | null;
  onClose: () => void;
  onResolve: (id: number, payload: ResolveConflictPayload) => void;
  isLoading?: boolean;
}

export const ConflictResolveModal: React.FC<ConflictResolveModalProps> = ({
  conflict,
  onClose,
  onResolve,
  isLoading = false,
}) => {
  const [action, setAction] = useState('ACCEPT_DOC_A');
  const [overrideValue, setOverrideValue] = useState<string>('');
  const [notes, setNotes] = useState<string>('');

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose, isLoading]);

  if (!conflict) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onResolve(conflict.id, {
      resolution_action: action,
      override_value: action === 'OVERRIDE' && overrideValue ? parseFloat(overrideValue) : undefined,
      notes: notes.trim() || undefined,
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0E1113]/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Cross-Document Conflict Resolution Modal"
    >
      <div
        className="relative w-full max-w-2xl p-6 rounded-lg bg-[#1C2226] border border-[#30383D] shadow-2xl space-y-6 overflow-y-auto max-h-[90vh] animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#30383D] pb-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-[#C58B3A]/15 text-[#C58B3A] border border-[#C58B3A]/30">
              <GitCompare className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-[#E8ECEB]">Cross-Document Conflict Resolution</h3>
              <p className="text-xs text-[#9BA5A8]">
                {conflict.mine_name} • {conflict.metric_name} ({conflict.fiscal_year})
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            disabled={isLoading}
            className="p-1.5 rounded-lg text-[#9BA5A8] hover:text-[#E8ECEB] hover:bg-[#242C30] transition-colors"
            aria-label="Close modal"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Side-by-Side Document Comparison Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Document A */}
          <div className="p-4 rounded-lg bg-[#242C30] border border-[#30383D] space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-[#9BA5A8]">
              <span className="font-bold text-[#C58B3A]">DOCUMENT A</span>
              <span>ID #{conflict.document_a_id}</span>
            </div>
            <div className="flex items-center gap-2 text-xs font-bold text-[#E8ECEB] truncate">
              <FileText className="h-4 w-4 text-[#C58B3A] shrink-0" />
              <span className="truncate" title={conflict.document_a_filename}>{conflict.document_a_filename}</span>
            </div>
            <div className="pt-2 border-t border-[#30383D] flex items-baseline justify-between font-mono">
              <span className="text-xs text-[#9BA5A8]">Reported Value:</span>
              <span className="text-base font-bold text-[#E8ECEB]">
                {conflict.document_a_value} {conflict.document_a_unit}
              </span>
            </div>
          </div>

          {/* Document B */}
          <div className="p-4 rounded-lg bg-[#242C30] border border-[#30383D] space-y-2">
            <div className="flex items-center justify-between text-xs font-mono text-[#9BA5A8]">
              <span className="font-bold text-[#54788A]">DOCUMENT B</span>
              <span>ID #{conflict.document_b_id}</span>
            </div>
            <div className="flex items-center gap-2 text-xs font-bold text-[#E8ECEB] truncate">
              <FileText className="h-4 w-4 text-[#54788A] shrink-0" />
              <span className="truncate" title={conflict.document_b_filename}>{conflict.document_b_filename}</span>
            </div>
            <div className="pt-2 border-t border-[#30383D] flex items-baseline justify-between font-mono">
              <span className="text-xs text-[#9BA5A8]">Reported Value:</span>
              <span className="text-base font-bold text-[#E8ECEB]">
                {conflict.document_b_value} {conflict.document_b_unit}
              </span>
            </div>
          </div>
        </div>

        {/* Discrepancy Banner */}
        <div className="p-3 rounded-lg bg-[#D6A23A]/10 border border-[#D6A23A]/30 text-[#D6A23A] text-xs flex items-center justify-between font-semibold">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-[#D6A23A] shrink-0" />
            <span>Calculated Multi-Source Discrepancy:</span>
          </div>
          <Badge variant="danger" size="md">
            {conflict.discrepancy_percentage?.toFixed(2)}% Discrepancy
          </Badge>
        </div>

        {/* Resolution Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <Select
            label="Resolution Action"
            value={action}
            onChange={(e) => setAction(e.target.value)}
            options={[
              { value: 'ACCEPT_DOC_A', label: `Accept Document A Value (${conflict.document_a_value} ${conflict.document_a_unit})` },
              { value: 'ACCEPT_DOC_B', label: `Accept Document B Value (${conflict.document_b_value} ${conflict.document_b_unit})` },
              { value: 'OVERRIDE', label: 'Manual Authoritative Override Value' },
              { value: 'FLAG_UNRESOLVED', label: 'Flag for On-Site Mine Audit' },
            ]}
          />

          {action === 'OVERRIDE' && (
            <Input
              label="Custom Authoritative Metric Value"
              type="number"
              step="0.01"
              placeholder="Enter authoritative metric value"
              value={overrideValue}
              onChange={(e) => setOverrideValue(e.target.value)}
              required
            />
          )}

          <div className="space-y-1">
            <label className="text-xs font-semibold text-[#E8ECEB]">Resolution Audit Justification Notes</label>
            <textarea
              rows={3}
              placeholder="Provide technical justification or audit rationale for conflict resolution..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full rounded-lg bg-[#151A1D] border border-[#30383D] p-3 text-xs text-[#E8ECEB] placeholder:text-[#9BA5A8]/70 focus:outline-none focus:border-[#C58B3A] font-sans shadow-sm"
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#30383D]">
            <Button variant="ghost" size="md" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="md"
              isLoading={isLoading}
              leftIcon={<CheckCircle2 className="h-4 w-4" />}
            >
              Resolve & Record in Audit Ledger
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};

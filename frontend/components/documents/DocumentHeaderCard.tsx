'use client';

import React from 'react';
import {
  FileText,
  FileSpreadsheet,
  FileCode,
  File,
  CheckCircle2,
  Clock,
  AlertCircle,
  Database,
  Hash,
  Sparkles,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DocumentItem } from '@/types/document';

interface DocumentHeaderCardProps {
  document: DocumentItem;
}

const getFileTypeIcon = (fileType: string) => {
  switch (fileType?.toUpperCase()) {
    case 'PDF':
      return <FileText className="h-6 w-6 text-[#C94B45]" />;
    case 'DOCX':
      return <FileText className="h-6 w-6 text-[#54788A]" />;
    case 'XLSX':
      return <FileSpreadsheet className="h-6 w-6 text-[#4F8A62]" />;
    case 'CSV':
      return <FileCode className="h-6 w-6 text-[#C58B3A]" />;
    default:
      return <File className="h-6 w-6 text-[#9BA5A8]" />;
  }
};

const formatFileSize = (bytes: number): string => {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

export const DocumentHeaderCard: React.FC<DocumentHeaderCardProps> = ({ document }) => {
  // Determine status steps based on document status
  const isParsed = document.status === 'PARSED' || document.status === 'INDEXED';
  const isIndexed = document.status === 'INDEXED' || document.status === 'PARSED';
  const isPending = document.status === 'PENDING';
  const isProcessing = document.status === 'PROCESSING';
  const isFailed = document.status === 'FAILED';

  const pipelineSteps = [
    { label: 'Ingestion', completed: !isPending && !isFailed, active: isPending },
    { label: 'Parsing', completed: isParsed, active: isProcessing },
    { label: 'Chunking', completed: isParsed, active: false },
    { label: 'Metric Normalization', completed: isParsed, active: false },
    { label: 'Vector Indexing', completed: isIndexed, active: false },
  ];

  return (
    <Card className="space-y-6 bg-[#1C2226] border-[#30383D]">
      {/* Primary Document Metadata Row */}
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-lg bg-[#242C30] border border-[#30383D] shrink-0">
            {getFileTypeIcon(document.file_type)}
          </div>

          <div className="space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-extrabold text-[#E8ECEB] tracking-tight font-sans">
                {document.filename}
              </h2>
              <Badge variant={isFailed ? 'danger' : isPending || isProcessing ? 'warning' : 'success'}>
                {document.status}
              </Badge>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-[#9BA5A8] pt-0.5">
              <span className="flex items-center gap-1 text-[#E8ECEB] font-semibold">
                <Database className="h-3.5 w-3.5 text-[#C58B3A]" />
                {document.subsidiary || 'CIL HQ'}
              </span>
              <span>•</span>
              <span className="text-[#C58B3A] font-semibold">{document.fiscal_year || '2023-24'}</span>
              <span>•</span>
              <span>{document.total_pages || 1} Pages</span>
              <span>•</span>
              <span>{formatFileSize(document.file_size_bytes)}</span>
            </div>
          </div>
        </div>

        {/* File Hash Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#242C30] border border-[#30383D] text-xs font-mono text-[#9BA5A8] shrink-0">
          <Hash className="h-3.5 w-3.5 text-[#9BA5A8]" />
          <span>SHA-256:</span>
          <span className="text-[#E8ECEB] select-all" title={document.file_hash}>
            {document.file_hash ? document.file_hash.substring(0, 18) : 'N/A'}...
          </span>
        </div>
      </div>

      {/* Document Processing Pipeline Stepper */}
      <div className="pt-4 border-t border-[#30383D] space-y-2">
        <p className="text-[10px] font-mono uppercase tracking-widest text-[#9BA5A8] font-semibold flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-[#C58B3A]" />
          <span>Document Processing Pipeline Traceability</span>
        </p>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1">
          {pipelineSteps.map((step, idx) => {
            return (
              <div
                key={idx}
                className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition-colors ${
                  step.completed
                    ? 'bg-[#4F8A62]/10 border-[#4F8A62]/30 text-[#4F8A62]'
                    : step.active
                    ? 'bg-[#C58B3A]/10 border-[#C58B3A]/30 text-[#C58B3A] animate-pulse'
                    : isFailed
                    ? 'bg-[#C94B45]/10 border-[#C94B45]/20 text-[#9BA5A8]'
                    : 'bg-[#151A1D] border-[#30383D] text-[#9BA5A8]'
                }`}
              >
                <span className="font-medium text-[11px] truncate">{step.label}</span>
                {step.completed ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-[#4F8A62] shrink-0" />
                ) : step.active ? (
                  <Clock className="h-3.5 w-3.5 text-[#C58B3A] shrink-0 animate-spin" />
                ) : (
                  <div className="h-2 w-2 rounded-full bg-[#30383D] shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Failure Alert Banner */}
      {isFailed && (
        <div className="p-3.5 rounded-lg bg-[#C94B45]/10 border border-[#C94B45]/30 text-xs text-[#C94B45] flex items-start gap-2.5">
          <AlertCircle className="h-4 w-4 text-[#C94B45] shrink-0 mt-0.5" />
          <div className="space-y-1">
            <span className="font-semibold text-[#C94B45]">Processing Interrupted:</span>
            <p className="text-[#9BA5A8]">{document.error_message || 'The document processing pipeline encountered an error. Please try re-uploading the file.'}</p>
          </div>
        </div>
      )}
    </Card>
  );
};

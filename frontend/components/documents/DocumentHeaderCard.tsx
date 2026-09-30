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
  Download,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DocumentItem } from '@/types/document';
import { buildOfficialSourceUrl } from '@/lib/officialSourceLink';
import { getDocumentSourceActions } from '@/lib/documentSourceAccess';
import { documentApi } from '@/lib/api/documentApi';
import { useLanguage } from '@/context/LanguageContext';

interface DocumentHeaderCardProps {
  document: DocumentItem;
  sourcePage?: number | null;
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

export const DocumentHeaderCard: React.FC<DocumentHeaderCardProps> = ({ document, sourcePage = null }) => {
  const { t } = useLanguage();
  const [sourceDownloadError, setSourceDownloadError] = React.useState<string | null>(null);
  // Determine status steps based on document status
  const isParsed = document.status === 'PARSED' || document.status === 'INDEXED';
  const isIndexed = document.status === 'INDEXED' || document.status === 'PARSED';
  const isPending = document.status === 'PENDING';
  const isProcessing = document.status === 'PROCESSING';
  const isFailed = document.status === 'FAILED';
  const officialSourceUrl = buildOfficialSourceUrl(document, sourcePage);
  const sourceActions = getDocumentSourceActions(document, sourcePage);

  const handleSourceDownload = async () => {
    setSourceDownloadError(null);
    try {
      const blob = await documentApi.downloadDocumentSource(document.id);
      const objectUrl = window.URL.createObjectURL(blob);
      const anchor = window.document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = document.filename;
      anchor.click();
      window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
    } catch (err: any) {
      setSourceDownloadError(err?.response?.data?.detail || err?.message || 'Source file unavailable.');
    }
  };

  const pipelineSteps = [
    { label: t('workspace.ingestion'), completed: !isPending && !isFailed, active: isPending },
    { label: t('workspace.parsing'), completed: isParsed, active: isProcessing },
    { label: t('workspace.chunking'), completed: isParsed, active: false },
    { label: t('workspace.metricNormalization'), completed: isParsed, active: false },
    { label: t('workspace.vectorIndexing'), completed: isIndexed, active: false },
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
              {officialSourceUrl ? (
                <a
                  href={officialSourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xl font-extrabold text-[#E8ECEB] tracking-tight font-sans hover:text-[#C58B3A] hover:underline"
                  title={t('workspace.openOfficialSource')}
                >
                  {document.filename}
                </a>
              ) : (
                <h2 className="text-xl font-extrabold text-[#E8ECEB] tracking-tight font-sans" title={sourceActions.storedArtifactAvailable ? 'Stored source file' : 'Source file unavailable'}>
                  {document.filename}
                </h2>
              )}
              <Badge variant={isFailed ? 'danger' : isPending || isProcessing ? 'warning' : 'success'}>
                {document.status}
              </Badge>
            </div>

            <div className="text-[10px] font-mono flex flex-wrap items-center gap-2">
              {officialSourceUrl && (
                <a
                  href={officialSourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 rounded-md border border-[#C58B3A]/40 px-2.5 py-1.5 text-[#C58B3A] hover:bg-[#C58B3A]/10"
                  title="Open the authoritative government source in a new tab."
                >
                  {t('workspace.openOfficialSource')}
                </a>
              )}
              {sourceActions.storedArtifactAvailable ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleSourceDownload}
                  leftIcon={<Download className="h-3.5 w-3.5" />}
                  title="Download the exact source artifact ingested by COALINTEL."
                >
                  Download File
                </Button>
              ) : (
                <span className="text-[#9BA5A8]">Source File Unavailable</span>
              )}
              {sourceDownloadError && <span className="text-[#C94B45]">{sourceDownloadError}</span>}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs font-mono text-[#9BA5A8] pt-0.5">
              <span className="flex items-center gap-1 text-[#E8ECEB] font-semibold">
                <Database className="h-3.5 w-3.5 text-[#C58B3A]" />
                {document.subsidiary || 'CIL HQ'}
              </span>
              <span>•</span>
              <span className="text-[#C58B3A] font-semibold">{document.fiscal_year || '2023-24'}</span>
              <span>•</span>
              <span>{document.total_pages || 1} {t('workspace.pages')}</span>
              <span>•</span>
              <span>{formatFileSize(document.file_size_bytes)}</span>
            </div>
          </div>
        </div>

        {/* File Hash Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#242C30] border border-[#30383D] text-xs font-mono text-[#9BA5A8] shrink-0">
          <Hash className="h-3.5 w-3.5 text-[#9BA5A8]" />
          <span>{t('workspace.sha256')}</span>
          <span className="text-[#E8ECEB] select-all" title={document.file_hash}>
            {document.file_hash ? document.file_hash.substring(0, 18) : 'N/A'}...
          </span>
        </div>
      </div>

      {/* Document Processing Pipeline Stepper */}
      <div className="pt-4 border-t border-[#30383D] space-y-2">
        <p className="text-[10px] font-mono uppercase tracking-widest text-[#9BA5A8] font-semibold flex items-center gap-1.5">
          <Sparkles className="h-3.5 w-3.5 text-[#C58B3A]" />
          <span>{t('workspace.pipeline')}</span>
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
            <span className="font-semibold text-[#C94B45]">{t('workspace.processingInterrupted')}</span>
            <p className="text-[#9BA5A8]">{document.error_message || t('workspace.processingError')}</p>
          </div>
        </div>
      )}
    </Card>
  );
};

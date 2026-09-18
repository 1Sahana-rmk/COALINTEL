'use client';

import React, { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import {
  FileText,
  FileSpreadsheet,
  FileCode,
  File,
  Search,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  Trash2,
  AlertTriangle,
  X,
} from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { CIL_SUBSIDIARIES } from '@/lib/constants';
import { documentApi } from '@/lib/api/documentApi';
import { DocumentItem, DocumentStatus } from '@/types/document';

interface DocumentTableProps {
  documents: DocumentItem[];
  loading?: boolean;
  onRefresh?: () => void;
  selectedStatus: string;
  onStatusChange: (status: string) => void;
  selectedSubsidiary: string;
  onSubsidiaryChange: (subsidiary: string) => void;
}

const getFileTypeIcon = (fileType: string) => {
  switch (fileType?.toUpperCase()) {
    case 'PDF':
      return <FileText className="h-5 w-5 text-[#C94B45]" />;
    case 'DOCX':
      return <FileText className="h-5 w-5 text-[#54788A]" />;
    case 'XLSX':
      return <FileSpreadsheet className="h-5 w-5 text-[#4F8A62]" />;
    case 'CSV':
      return <FileCode className="h-5 w-5 text-[#C58B3A]" />;
    default:
      return <File className="h-5 w-5 text-[#9BA5A8]" />;
  }
};

const getStatusBadge = (status: DocumentStatus) => {
  switch (status) {
    case 'PARSED':
    case 'INDEXED':
      return <Badge variant="success">{status}</Badge>;
    case 'PROCESSING':
    case 'PENDING':
      return <Badge variant="warning">{status}</Badge>;
    case 'FAILED':
      return <Badge variant="danger">{status}</Badge>;
    default:
      return <Badge variant="default">{status}</Badge>;
  }
};

const formatFileSize = (bytes: number): string => {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
};

export const DocumentTable: React.FC<DocumentTableProps> = ({
  documents,
  loading = false,
  onRefresh,
  selectedStatus,
  onStatusChange,
  selectedSubsidiary,
  onSubsidiaryChange,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [isAdmin, setIsAdmin] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<DocumentItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const pageSize = 10;

  // Detect Admin role on mount from localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem('coalintel_user');
      if (stored) {
        try {
          const user = JSON.parse(stored);
          setIsAdmin(user?.role === 'Admin');
        } catch (e) {
          setIsAdmin(false);
        }
      }
    }
  }, []);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && documentToDelete && !isDeleting) {
        setDocumentToDelete(null);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [documentToDelete, isDeleting]);

  const statusTabs = [
    { value: 'ALL', label: 'All Documents' },
    { value: 'PARSED', label: 'Parsed' },
    { value: 'INDEXED', label: 'Indexed' },
    { value: 'PROCESSING', label: 'Processing' },
    { value: 'FAILED', label: 'Failed' },
  ];

  // Client-side search filtering
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      const matchSearch =
        !searchTerm.trim() ||
        doc.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
        doc.file_hash.toLowerCase().includes(searchTerm.toLowerCase());
      return matchSearch;
    });
  }, [documents, searchTerm]);

  // Pagination calculation
  const totalPages = Math.max(1, Math.ceil(filteredDocuments.length / pageSize));
  const paginatedDocs = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredDocuments.slice(start, start + pageSize);
  }, [filteredDocuments, currentPage]);

  const handleDeleteConfirm = async () => {
    if (!documentToDelete) return;
    setIsDeleting(true);
    setDeleteError(null);

    try {
      await documentApi.deleteDocument(documentToDelete.id);
      setDocumentToDelete(null);
      if (onRefresh) {
        onRefresh();
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to delete document.';
      setDeleteError(msg);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Search & Filter Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4 p-4 rounded-lg bg-[#1C2226] border border-[#30383D] shadow-sm">
        {/* Search Input */}
        <div className="flex-1 max-w-md">
          <Input
            placeholder="Search by filename or SHA-256 hash..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            leftIcon={<Search className="h-4 w-4 text-[#9BA5A8]" />}
            className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] text-xs py-2"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <Select
            value={selectedSubsidiary}
            onChange={(e) => {
              onSubsidiaryChange(e.target.value);
              setCurrentPage(1);
            }}
            options={CIL_SUBSIDIARIES}
            className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] text-xs font-medium py-2 w-48"
          />

          {onRefresh && (
            <Button
              variant="secondary"
              size="sm"
              onClick={onRefresh}
              isLoading={loading}
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
            >
              Refresh
            </Button>
          )}
        </div>
      </div>

      {/* Status Filter Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none border-b border-[#30383D]">
        {statusTabs.map((tab) => (
          <button
            key={tab.value}
            onClick={() => {
              onStatusChange(tab.value);
              setCurrentPage(1);
            }}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors whitespace-nowrap select-none ${
              selectedStatus === tab.value
                ? 'bg-[#C58B3A]/15 text-[#C58B3A] border border-[#C58B3A]/40 font-semibold'
                : 'text-[#9BA5A8] hover:text-[#E8ECEB] hover:bg-[#242C30]'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Document Data Table */}
      <div className="rounded-lg border border-[#30383D] bg-[#1C2226] overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-[#30383D] bg-[#151A1D] text-[11px] font-mono text-[#9BA5A8] uppercase tracking-wider">
                <th className="py-3 px-4">Document / File Type</th>
                <th className="py-3 px-4">Subsidiary / FY</th>
                <th className="py-3 px-4">Pages / Size</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Ingested Date</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-[#30383D] text-xs">
              {loading ? (
                Array.from({ length: 5 }).map((_, idx) => (
                  <tr key={idx} className="animate-pulse">
                    <td className="py-4 px-4">
                      <div className="h-4 w-48 bg-[#242C30] rounded" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 w-24 bg-[#242C30] rounded" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 w-20 bg-[#242C30] rounded" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 w-16 bg-[#242C30] rounded" />
                    </td>
                    <td className="py-4 px-4">
                      <div className="h-4 w-24 bg-[#242C30] rounded" />
                    </td>
                    <td className="py-4 px-4 text-right">
                      <div className="h-6 w-20 bg-[#242C30] rounded ml-auto" />
                    </td>
                  </tr>
                ))
              ) : paginatedDocs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8">
                    <EmptyState
                      title="No Documents Found"
                      description="No mining documents match your current filter parameters."
                    />
                  </td>
                </tr>
              ) : (
                paginatedDocs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-[#242C30]/50 transition-colors group">
                    {/* Filename & Type */}
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-[#242C30] border border-[#30383D] group-hover:border-[#C58B3A]/40 shrink-0">
                          {getFileTypeIcon(doc.file_type)}
                        </div>
                        <div className="min-w-0">
                          <Link
                            href={`/documents/${doc.id}`}
                            className="font-semibold text-[#E8ECEB] hover:text-[#C58B3A] transition-colors truncate block max-w-xs sm:max-w-sm"
                            title={doc.filename}
                          >
                            {doc.filename}
                          </Link>
                          <span className="text-[10px] font-mono text-[#9BA5A8] truncate block max-w-xs">
                            SHA-256: {doc.file_hash ? doc.file_hash.substring(0, 16) : 'N/A'}...
                          </span>
                        </div>
                      </div>
                    </td>

                    {/* Subsidiary & FY */}
                    <td className="py-3.5 px-4 font-mono text-[#9BA5A8]">
                      <span className="font-semibold block text-[#E8ECEB]">{doc.subsidiary || 'CIL HQ'}</span>
                      <span className="text-[11px] text-[#C58B3A] font-semibold">{doc.fiscal_year || '2023-24'}</span>
                    </td>

                    {/* Pages & Size */}
                    <td className="py-3.5 px-4 font-mono text-[#9BA5A8]">
                      <span className="block text-[#E8ECEB]">{doc.total_pages || 1} Pages</span>
                      <span className="text-[11px] text-[#9BA5A8]">{formatFileSize(doc.file_size_bytes)}</span>
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4">{getStatusBadge(doc.status)}</td>

                    {/* Date */}
                    <td className="py-3.5 px-4 text-[#9BA5A8] font-mono text-[11px]">
                      {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'Recent'}
                    </td>

                    {/* Actions */}
                    <td className="py-3.5 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Link href={`/documents/${doc.id}`}>
                          <Button
                            variant="outline"
                            size="sm"
                            leftIcon={<Eye className="h-3.5 w-3.5" />}
                          >
                            View Intelligence
                          </Button>
                        </Link>
                        {isAdmin && (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setDeleteError(null);
                              setDocumentToDelete(doc);
                            }}
                            className="text-[#C94B45] hover:text-[#C94B45] hover:bg-[#C94B45]/10 border border-transparent hover:border-[#C94B45]/30"
                            leftIcon={<Trash2 className="h-3.5 w-3.5" />}
                          >
                            Delete
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="py-3 px-4 border-t border-[#30383D] bg-[#151A1D] flex items-center justify-between text-xs font-mono text-[#9BA5A8]">
          <span>
            Showing {filteredDocuments.length === 0 ? 0 : (currentPage - 1) * pageSize + 1} to{' '}
            {Math.min(currentPage * pageSize, filteredDocuments.length)} of {filteredDocuments.length} documents
          </span>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1 || loading}
              className="p-1.5 rounded-lg bg-[#242C30] border border-[#30383D] text-[#E8ECEB] hover:bg-[#30383D] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>

            <span>
              Page {currentPage} of {totalPages}
            </span>

            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages || loading}
              className="p-1.5 rounded-lg bg-[#242C30] border border-[#30383D] text-[#E8ECEB] hover:bg-[#30383D] disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Admin Document Deletion Confirmation Modal */}
      {documentToDelete && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0E1113]/80 backdrop-blur-sm animate-fade-in"
          onClick={() => !isDeleting && setDocumentToDelete(null)}
          role="dialog"
          aria-modal="true"
          aria-label="Delete document confirmation"
        >
          <div
            className="relative w-full max-w-lg p-6 rounded-lg bg-[#1C2226] border border-[#C94B45]/40 shadow-2xl space-y-6 animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-[#30383D] pb-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-[#C94B45]/10 text-[#C94B45] border border-[#C94B45]/30">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-[#E8ECEB]">Delete this document?</h3>
                  <p className="text-xs text-[#9BA5A8] font-mono">Document #{documentToDelete.id}</p>
                </div>
              </div>

              <button
                onClick={() => setDocumentToDelete(null)}
                disabled={isDeleting}
                className="p-1.5 rounded-lg text-[#9BA5A8] hover:text-[#E8ECEB] hover:bg-[#242C30] transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Error Banner */}
            {deleteError && (
              <div className="p-3.5 rounded-lg bg-[#C94B45]/10 border border-[#C94B45]/40 text-[#C94B45] text-xs flex items-start gap-2.5">
                <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5 text-[#C94B45]" />
                <span>{deleteError}</span>
              </div>
            )}

            {/* Modal Body */}
            <div className="space-y-3 text-xs text-[#9BA5A8]">
              <p>
                Are you sure you want to permanently delete{' '}
                <strong className="text-[#E8ECEB] font-semibold">{documentToDelete.filename}</strong>?
              </p>
              <div className="p-3.5 rounded-lg bg-[#151A1D] border border-[#30383D] space-y-1.5 font-mono text-[11px] text-[#9BA5A8]">
                <p className="text-[#D6A23A] font-sans font-semibold text-xs">This operation will permanently remove:</p>
                <ul className="list-disc list-inside space-y-1 text-[#E8ECEB]">
                  <li>Stored source document file from storage</li>
                  <li>All extracted metrics and unit normalizations</li>
                  <li>Document text chunks and token metadata</li>
                  <li>Semantic vector embeddings in ChromaDB</li>
                </ul>
                <p className="text-[#C94B45] pt-1 font-sans text-[11px] font-semibold">
                  This action cannot be undone.
                </p>
              </div>
            </div>

            {/* Modal Footer Actions */}
            <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#30383D]">
              <Button
                variant="ghost"
                size="md"
                onClick={() => setDocumentToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                size="md"
                onClick={handleDeleteConfirm}
                isLoading={isDeleting}
                leftIcon={<Trash2 className="h-4 w-4" />}
              >
                Delete Permanently
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

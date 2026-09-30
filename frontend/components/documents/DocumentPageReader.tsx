'use client';

import React, { useState, useMemo } from 'react';
import {
  ChevronLeft,
  ChevronRight,
  Search,
  BookOpen,
  Bookmark,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { DocumentPageItem } from '@/types/document';
import { DocumentTableItem } from '@/types/document';
import { buildPageContentSummary, reliableTables } from '@/lib/documentEvidencePresentation';
import { useLanguage } from '@/context/LanguageContext';

interface DocumentPageReaderProps {
  filename: string;
  totalPages: number;
  pages: DocumentPageItem[];
  activePageNumber?: number;
  onPageChange?: (pageNum: number) => void;
  highlightTerm?: string;
  pageTables?: DocumentTableItem[];
  loading?: boolean;
}

export const DocumentPageReader: React.FC<DocumentPageReaderProps> = ({
  filename,
  totalPages,
  pages,
  activePageNumber = 1,
  onPageChange,
  highlightTerm = '',
  pageTables = [],
  loading = false,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(activePageNumber);
  const [searchTerm, setSearchTerm] = useState<string>(highlightTerm);
  const [fontSize, setFontSize] = useState<'sm' | 'base' | 'lg'>('base');
  const { t } = useLanguage();

  // Keep internal currentPage in sync when activePageNumber changes externally (e.g. from lineage drawer)
  React.useEffect(() => {
    if (activePageNumber) {
      setCurrentPage(activePageNumber);
    }
  }, [activePageNumber]);

  const handlePageChange = (newPage: number) => {
    const validPage = Math.max(1, Math.min(totalPages || 1, newPage));
    setCurrentPage(validPage);
    if (onPageChange) onPageChange(validPage);
  };

  // Find active page content item
  const activePageItem = useMemo(() => {
    return pages.find((p) => p.page_number === currentPage) || pages[0] || null;
  }, [pages, currentPage]);
  const structuredPageTables = useMemo(() => reliableTables(pageTables), [pageTables]);
  const pageSummary = useMemo(() => buildPageContentSummary(structuredPageTables), [structuredPageTables]);

  // Render text with search term highlighting
  const renderHighlightedText = (text: string) => {
    const activeSearch = searchTerm || highlightTerm;
    if (!activeSearch.trim()) {
      return <span className="whitespace-pre-wrap">{text}</span>;
    }

    const regex = new RegExp(`(${activeSearch.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(regex);

    return (
      <span className="whitespace-pre-wrap">
        {parts.map((part, i) =>
          regex.test(part) ? (
            <mark key={i} className="bg-[#C58B3A]/20 text-[#C58B3A] px-1 py-0.5 rounded font-semibold border border-[#C58B3A]/40">
              {part}
            </mark>
          ) : (
            part
          )
        )}
      </span>
    );
  };

  const fontClasses = {
    sm: 'text-xs leading-relaxed',
    base: 'text-sm leading-relaxed',
    lg: 'text-base leading-loose',
  };

  return (
    <Card className="h-full flex flex-col min-h-[600px] border-[#30383D] bg-[#1C2226] shadow-sm">
      {/* Header Toolbar */}
      <CardHeader className="py-3 px-4 bg-[#151A1D] border-b border-[#30383D]">
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
          {/* Left Title & Provenance Badge */}
          <div className="flex items-center gap-2.5">
            <BookOpen className="h-4 w-4 text-[#C58B3A] shrink-0" />
            <CardTitle className="text-sm font-semibold truncate max-w-xs text-[#E8ECEB]">{filename}</CardTitle>
            <Badge variant="amber" size="sm" className="hidden md:inline-flex">
              {t('workspace.page')} {currentPage} / {totalPages || 1}
            </Badge>
          </div>

          {/* Center Search within Page */}
          <div className="w-full sm:w-64">
            <Input
              placeholder={t('workspace.searchText')}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              leftIcon={<Search className="h-3.5 w-3.5 text-[#9BA5A8]" />}
              className="bg-[#151A1D] border-[#30383D] text-[#E8ECEB] text-xs py-1.5"
            />
          </div>

          {/* Right Controls: Font size & Navigation */}
          <div className="flex items-center justify-between sm:justify-end gap-2">
            <div className="flex items-center gap-1 bg-[#151A1D] rounded-lg p-1 border border-[#30383D]">
              <button
                onClick={() => setFontSize('sm')}
                className={`px-1.5 py-0.5 text-[10px] font-mono rounded ${fontSize === 'sm' ? 'bg-[#C58B3A] text-[#0E1113] font-bold' : 'text-[#9BA5A8] hover:text-[#E8ECEB]'}`}
                title="Small Font"
              >
                A-
              </button>
              <button
                onClick={() => setFontSize('base')}
                className={`px-1.5 py-0.5 text-[10px] font-mono rounded ${fontSize === 'base' ? 'bg-[#C58B3A] text-[#0E1113] font-bold' : 'text-[#9BA5A8] hover:text-[#E8ECEB]'}`}
                title="Normal Font"
              >
                A
              </button>
              <button
                onClick={() => setFontSize('lg')}
                className={`px-1.5 py-0.5 text-[10px] font-mono rounded ${fontSize === 'lg' ? 'bg-[#C58B3A] text-[#0E1113] font-bold' : 'text-[#9BA5A8] hover:text-[#E8ECEB]'}`}
                title="Large Font"
              >
                A+
              </button>
            </div>

            {/* Page Navigation Controls */}
            <div className="flex items-center gap-1.5 font-mono text-xs">
              <button
                onClick={() => handlePageChange(currentPage - 1)}
                disabled={currentPage <= 1 || loading}
                className="p-1.5 rounded-lg bg-[#242C30] border border-[#30383D] text-[#E8ECEB] hover:bg-[#30383D] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title={t('workspace.previous')}
              >
                <ChevronLeft className="h-4 w-4" />
              </button>

              <div className="flex items-center gap-1">
                <input
                  type="number"
                  min={1}
                  max={totalPages || 1}
                  value={currentPage}
                  onChange={(e) => handlePageChange(parseInt(e.target.value) || 1)}
                  className="w-10 text-center bg-[#151A1D] border border-[#30383D] rounded text-xs py-1 text-[#E8ECEB] font-bold focus:outline-none focus:border-[#C58B3A]"
                />
                <span className="text-[#9BA5A8]">/ {totalPages || 1}</span>
              </div>

              <button
                onClick={() => handlePageChange(currentPage + 1)}
                disabled={currentPage >= (totalPages || 1) || loading}
                className="p-1.5 rounded-lg bg-[#242C30] border border-[#30383D] text-[#E8ECEB] hover:bg-[#30383D] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                title={t('workspace.next')}
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </CardHeader>

      {/* Main Scrollable Reading Area */}
      <CardContent className="flex-1 p-6 overflow-y-auto max-h-[650px] bg-[#0E1113] text-[#E8ECEB] scrollbar-thin">
        {loading ? (
          <div className="space-y-4 animate-pulse p-4">
            <div className="h-4 bg-[#242C30] rounded w-3/4" />
            <div className="h-4 bg-[#242C30] rounded w-full" />
            <div className="h-4 bg-[#242C30] rounded w-5/6" />
            <div className="h-4 bg-[#242C30] rounded w-2/3" />
          </div>
        ) : activePageItem ? (
          <div className="space-y-4">
            {/* Document Provenance Header inside Canvas */}
            <div className="flex items-center justify-between pb-3 border-b border-[#30383D] text-[11px] font-mono text-[#9BA5A8]">
              <span className="flex items-center gap-1.5 text-[#E8ECEB] font-semibold">
                <Bookmark className="h-3.5 w-3.5 text-[#C58B3A]" />
                {t('workspace.pageTextCanvas')}
              </span>
              <span className="text-[#C58B3A] font-semibold">Page {activePageItem.page_number}</span>
            </div>

            {pageSummary ? (
              <>
                <section className="rounded-lg border border-[#C58B3A]/30 bg-[#C58B3A]/10 p-4 space-y-2">
                  <h3 className="text-sm font-semibold text-[#E8ECEB]">{t('workspace.pageSummary')}</h3>
                  <p className="text-sm leading-relaxed text-[#E8ECEB]">{pageSummary}</p>
                  <p className="text-[10px] text-[#9BA5A8]">{t('workspace.summaryNote')}</p>
                </section>

                <details className="rounded-lg border border-[#30383D] bg-[#151A1D]">
                  <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-[#C58B3A]">{t('workspace.rawText')}</summary>
                  <div className={`border-t border-[#30383D] p-4 font-sans tracking-wide text-[#E8ECEB] selection:bg-[#C58B3A]/30 ${fontClasses[fontSize]}`}>
                    {renderHighlightedText(activePageItem.text_snippet || t('workspace.noTextForPage'))}
                  </div>
                </details>
              </>
            ) : (
              <div className={`font-sans tracking-wide text-[#E8ECEB] selection:bg-[#C58B3A]/30 ${fontClasses[fontSize]}`}>
                {renderHighlightedText(activePageItem.text_snippet || t('workspace.noTextForPage'))}
              </div>
            )}
          </div>
        ) : (
          <div className="p-8 text-center text-[#9BA5A8] text-xs font-mono">
            {t('workspace.noPageData')} {currentPage}.
          </div>
        )}
      </CardContent>
    </Card>
  );
};

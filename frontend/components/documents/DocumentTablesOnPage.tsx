'use client';

import React from 'react';
import { AlertTriangle, Table2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DocumentTableItem } from '@/types/document';
import { displayPersistedTableValue, persistedTableMerges, structuredRows, tableColumnCount, tablesForPage, PersistedTableMerge } from '@/lib/documentEvidencePresentation';
import { useLanguage } from '@/context/LanguageContext';

interface DocumentTablesOnPageProps {
  tables: DocumentTableItem[];
  pageNumber: number;
  loading?: boolean;
}

function mergeStartingAt(merges: PersistedTableMerge[], row: number, column: number): PersistedTableMerge | undefined {
  return merges.find((merge) => merge.startRow === row && merge.startColumn === column);
}

function isCoveredByMerge(merges: PersistedTableMerge[], row: number, column: number): boolean {
  return merges.some((merge) =>
    row >= merge.startRow && row <= merge.endRow &&
    column >= merge.startColumn && column <= merge.endColumn &&
    !(merge.startRow === row && merge.startColumn === column),
  );
}

function PersistedTable({ table }: { table: DocumentTableItem }) {
  const { t } = useLanguage();
  const headers = Array.isArray(table.headers) ? table.headers : [];
  const rows = structuredRows(table);
  const columnCount = tableColumnCount(table);
  const hasStructuredRows = rows.length > 0 && columnCount > 0;
  const cellRecords = Array.isArray(table.cells) ? table.cells : [];
  const merges = persistedTableMerges(table);
  const cellGeometryCount = cellRecords.filter((cell) => {
    if (!cell || typeof cell !== 'object') return false;
    const record = cell as Record<string, unknown>;
    return Boolean(record.bounding_box || record.bbox);
  }).length;

  return (
    <div className="rounded-lg border border-[#30383D] bg-[#151A1D] overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#30383D] px-3 py-2">
        <div className="flex items-center gap-2 min-w-0">
          <Table2 className="h-4 w-4 text-[#C58B3A] shrink-0" />
          <span className="text-xs font-semibold text-[#E8ECEB] truncate">{table.title || `Table ${table.table_number}`}</span>
          {table.sheet_name && <span className="text-[10px] text-[#9BA5A8]">Sheet: {table.sheet_name}</span>}
        </div>
        <div className="flex items-center gap-2 text-[10px] text-[#9BA5A8] font-mono">
          {table.extraction_method && <span>{table.extraction_method}</span>}
          {table.extraction_confidence != null && <Badge variant="amber" size="sm">{Math.round(table.extraction_confidence * 100)}%</Badge>}
        </div>
      </div>

      {hasStructuredRows ? (
        <div className="overflow-x-auto">
          <table className="min-w-[1100px] w-full text-left text-xs border-collapse">
            {headers.length > 0 && (
              <thead className="bg-[#242C30] text-[#E8ECEB]"><tr>
                {Array.from({ length: columnCount }, (_, index) => index + 1).filter((column) => !isCoveredByMerge(merges, 1, column)).map((column) => {
                  const merge = mergeStartingAt(merges, 1, column);
                  const value = headers[column - 1];
                  return <th key={column} colSpan={merge ? merge.endColumn - merge.startColumn + 1 : 1} rowSpan={merge ? merge.endRow - merge.startRow + 1 : 1} className="border-b border-[#30383D] px-3 py-2 font-semibold whitespace-nowrap">
                    {displayPersistedTableValue(value)}
                  </th>;
                })}
              </tr></thead>
            )}
            <tbody className="divide-y divide-[#30383D] text-[#E8ECEB]">
              {rows.map((row, rowIndex) => <tr key={rowIndex} className="hover:bg-[#242C30]/50">
                {Array.from({ length: columnCount }, (_, columnIndex) => columnIndex + 1).filter((column) => !isCoveredByMerge(merges, rowIndex + (headers.length > 0 ? 2 : 1), column)).map((column) => {
                  const sourceRow = rowIndex + (headers.length > 0 ? 2 : 1);
                  const merge = mergeStartingAt(merges, sourceRow, column);
                  const value = row[column - 1];
                  return <td key={column} colSpan={merge ? merge.endColumn - merge.startColumn + 1 : 1} rowSpan={merge ? merge.endRow - merge.startRow + 1 : 1} className="border-r border-[#30383D]/70 px-3 py-2 align-top whitespace-pre-wrap">
                    {displayPersistedTableValue(value)}
                  </td>;
                })}
              </tr>)}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="px-3 py-4 text-xs text-[#D6A23A]">{t('workspace.tableStructureUnavailable')}</div>
      )}

      <div className="border-t border-[#30383D] px-3 py-2 text-[10px] text-[#9BA5A8] space-y-1">
        <div>{t('workspace.persistedProvenance')}: {cellRecords.length} {t('workspace.cellRecords')}{cellGeometryCount > 0 ? ` · ${cellGeometryCount} ${t('workspace.withGeometry')}` : ` · ${t('workspace.exactCellGeometryUnavailable')}`}{Array.isArray(table.merged_cells) && table.merged_cells.length > 0 ? ` · ${t('workspace.merged')}: ${table.merged_cells.join(', ')}` : ''}</div>
        {Array.isArray(table.warnings) && table.warnings.length > 0 && <div className="flex items-start gap-1.5 text-[#D6A23A]"><AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" /><span>{table.warnings.join(' · ')}</span></div>}
      </div>
    </div>
  );
}

export const DocumentTablesOnPage: React.FC<DocumentTablesOnPageProps> = ({ tables, pageNumber, loading = false }) => {
  const { t } = useLanguage();
  const pageTables = tablesForPage(tables, pageNumber);
  return <Card className="border-[#30383D] bg-[#1C2226]">
    <CardHeader className="py-3 px-4 bg-[#151A1D] border-b border-[#30383D]"><CardTitle className="text-sm font-semibold text-[#E8ECEB]">{t('workspace.tablesOnPage')} {pageNumber}</CardTitle></CardHeader>
    <CardContent className="p-4 space-y-3">
      {loading ? <div className="h-16 rounded-lg bg-[#242C30] animate-pulse" /> : pageTables.length === 0 ? <p className="text-xs text-[#9BA5A8]">{t('workspace.noTableArtifact')}</p> : <>
        <p className="text-[10px] text-[#9BA5A8]">{t('workspace.renderedFromArtifacts')}</p>
        {pageTables.map((table) => <PersistedTable key={table.id} table={table} />)}
      </>}
    </CardContent>
  </Card>;
};

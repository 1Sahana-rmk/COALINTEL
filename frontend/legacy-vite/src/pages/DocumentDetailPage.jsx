import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, CheckCircle2, Hash, Calendar, Building2, Layers, BookOpen } from 'lucide-react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Table } from '../components/common/Table';
import { documentApi } from '../api/documentApi';

const baselineExtractedMetrics = [
  { id: 101, mine: 'Rajmahal OC', metric: 'Coal Production', rawVal: '425.00', rawUnit: 'Lakh Tonnes', normVal: '42.50', normUnit: 'MT', year: '2023-24', status: 'VALIDATED' },
  { id: 102, mine: 'Rajmahal OC', metric: 'Overburden Removal', rawVal: '120.40', rawUnit: 'M.Cu.M', normVal: '120.40', normUnit: 'M.Cu.M', year: '2023-24', status: 'VALIDATED' },
  { id: 103, mine: 'Sonalpur OC', metric: 'Despatch', rawVal: '382.00', rawUnit: 'Lakh Tonnes', normVal: '38.20', normUnit: 'MT', year: '2023-24', status: 'WARNING_ARITHMETIC' },
];

export const DocumentDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [documentInfo, setDocumentInfo] = useState({
    id: id || '1',
    filename: 'ECL_Annual_Report_2023-24.pdf',
    subsidiary: 'Eastern Coalfields (ECL)',
    fiscal_year: '2023-24',
    total_pages: 84,
    file_size_bytes: 14889728,
    file_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    status: 'PARSED'
  });

  const [pages, setPages] = useState([]);
  const [activePage, setActivePage] = useState(1);
  const [extractedMetrics, setExtractedMetrics] = useState(baselineExtractedMetrics);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchDocData = async () => {
      if (!id) return;
      setLoading(true);
      try {
        const [docData, pagesData, lineageData] = await Promise.allSettled([
          documentApi.getDocumentById(id),
          documentApi.getDocumentPages(id),
          documentApi.getDocumentLineage(id)
        ]);

        if (docData.status === 'fulfilled' && docData.value) {
          const d = docData.value;
          setDocumentInfo({
            id: d.id,
            filename: d.filename,
            subsidiary: d.subsidiary || 'ECL',
            fiscal_year: d.fiscal_year || '2023-24',
            total_pages: d.total_pages || 84,
            file_size_bytes: d.file_size_bytes || 14889728,
            file_hash: d.file_hash || 'hash_' + d.id,
            status: d.status || 'PARSED'
          });
        }

        if (pagesData.status === 'fulfilled' && pagesData.value?.pages) {
          setPages(pagesData.value.pages);
        }

        if (lineageData.status === 'fulfilled' && Array.isArray(lineageData.value?.metrics) && lineageData.value.metrics.length > 0) {
          setExtractedMetrics(lineageData.value.metrics.map(m => ({
            id: m.id,
            mine: m.mine_name,
            metric: m.metric_name,
            rawVal: typeof m.numeric_value === 'number' ? m.numeric_value.toFixed(2) : m.numeric_value,
            rawUnit: m.unit,
            normVal: typeof m.standard_value === 'number' ? m.standard_value.toFixed(2) : m.standard_value,
            normUnit: m.standard_unit,
            year: m.fiscal_year,
            status: m.validation_status
          })));
        }
      } catch (err) {
        // Baseline fallback
      } finally {
        setLoading(false);
      }
    };

    fetchDocData();
  }, [id]);

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="flex items-center space-x-3">
          <Button variant="ghost" size="sm" icon={ArrowLeft} onClick={() => navigate('/documents')}>
            Back to Library
          </Button>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              Document Lineage Inspector
            </h1>
            <p className="text-xs text-slate-400">Document ID #{documentInfo.id} • Ingestion Traceability</p>
          </div>
        </div>
        <Badge status={documentInfo.status} />
      </div>

      {/* Document Overview Metadata */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <div className="text-xs text-slate-400 font-medium">Filename</div>
          <div className="text-sm font-semibold text-white mt-1 truncate" title={documentInfo.filename}>{documentInfo.filename}</div>
        </Card>
        <Card>
          <div className="text-xs text-slate-400 font-medium">Subsidiary / Fiscal Year</div>
          <div className="text-sm font-semibold text-white mt-1">{documentInfo.subsidiary} • {documentInfo.fiscal_year}</div>
        </Card>
        <Card>
          <div className="text-xs text-slate-400 font-medium">Page Count / Size</div>
          <div className="text-sm font-semibold text-white mt-1">
            {documentInfo.total_pages} Pages • {((documentInfo.file_size_bytes || 1048576) / (1024 * 1024)).toFixed(1)} MB
          </div>
        </Card>
        <Card>
          <div className="text-xs text-slate-400 font-medium">SHA-256 Digest</div>
          <div className="text-[10px] font-mono text-amber-400 mt-1 truncate" title={documentInfo.file_hash}>
            {documentInfo.file_hash}
          </div>
        </Card>
      </div>

      {/* Extracted Metrics Table */}
      <Card title="Extracted Mining Metrics & Unit Normalization Lineage">
        <Table headers={['Mine Entity', 'Metric Name', 'Raw Extracted Value', 'Normalized Value (MT)', 'Fiscal Year', 'Validation Status']}>
          {extractedMetrics.map((m) => (
            <tr key={m.id} className="hover:bg-slate-800/40">
              <td className="px-4 py-3 text-xs font-semibold text-white">{m.mine}</td>
              <td className="px-4 py-3 text-xs text-slate-300">{m.metric}</td>
              <td className="px-4 py-3 text-xs text-slate-400 font-mono">{m.rawVal} {m.rawUnit}</td>
              <td className="px-4 py-3 text-xs font-bold text-amber-400 font-mono">{m.normVal} {m.normUnit}</td>
              <td className="px-4 py-3 text-xs text-slate-300">{m.year}</td>
              <td className="px-4 py-3">
                <Badge status={m.status} size="xs" />
              </td>
            </tr>
          ))}
        </Table>
      </Card>

      {/* Page Text Snippet Viewer */}
      {pages.length > 0 && (
        <Card title="Page Text & Chunk Snippet Inspector">
          <div className="space-y-3">
            <div className="flex items-center gap-2 overflow-x-auto pb-2 text-xs">
              <span className="text-slate-400 shrink-0">Select Page:</span>
              {pages.map((p) => (
                <button
                  key={p.page_number}
                  onClick={() => setActivePage(p.page_number)}
                  className={`px-2.5 py-1 rounded border text-xs font-mono transition-colors ${
                    activePage === p.page_number
                      ? 'bg-amber-500/20 text-amber-400 border-amber-500/40 font-bold'
                      : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-white'
                  }`}
                >
                  Page {p.page_number}
                </button>
              ))}
            </div>

            <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl text-xs font-mono text-slate-300 whitespace-pre-line leading-relaxed max-h-80 overflow-y-auto">
              {pages.find(p => p.page_number === activePage)?.text_snippet || 'No extracted text snippet for this page.'}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};

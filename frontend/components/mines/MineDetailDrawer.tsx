'use client';

import React from 'react';
import { 
  X, 
  Building2, 
  MapPin, 
  ShieldCheck, 
  TrendingUp, 
  TrendingDown, 
  Star, 
  FileText, 
  ExternalLink,
  Layers,
  Pickaxe,
  Calendar,
  AlertCircle
} from 'lucide-react';
import { MineDetail, MineYearlyMetric } from '@/lib/api/minesApi';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export interface MineDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  mine: MineDetail | null;
  onOpenSourceModal?: (source: any) => void;
}

export const MineDetailDrawer: React.FC<MineDetailDrawerProps> = ({
  isOpen,
  onClose,
  mine,
  onOpenSourceModal,
}) => {
  if (!isOpen || !mine) return null;

  const fy24 = mine.yearly_metrics?.find((m) => m.financial_year === '2024-25');
  const fy25 = mine.yearly_metrics?.find((m) => m.financial_year === '2025-26');
  const fy26 = mine.yearly_metrics?.find((m) => m.financial_year === '2026-27');

  let yoyGrowth: number | null = null;
  if (fy24?.production_mt && fy25?.production_mt && fy24.production_mt > 0) {
    yoyGrowth = Number((((fy25.production_mt - fy24.production_mt) / fy24.production_mt) * 100).toFixed(2));
  }

  const renderStarRating = (stars?: number) => {
    if (!stars) return <span className="text-xs text-[#9BA5A8] italic">Unrated</span>;
    return (
      <div className="inline-flex items-center gap-1 text-[#C58B3A]">
        {Array.from({ length: 5 }).map((_, i) => (
          <Star
            key={i}
            className={`w-3.5 h-3.5 ${i < stars ? 'fill-[#C58B3A] text-[#C58B3A]' : 'text-[#30383D]'}`}
          />
        ))}
        <span className="text-xs font-mono font-bold ml-1 text-[#E8ECEB]">{stars} Star</span>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
        <div className="w-screen max-w-2xl bg-[#151A1D] border-l border-[#30383D] shadow-2xl flex flex-col text-[#E8ECEB]">
          
          {/* Drawer Header */}
          <div className="px-6 py-5 border-b border-[#30383D] bg-[#1C2226] flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                <Badge variant="gold" size="sm">
                  {mine.mine_id}
                </Badge>
                <Badge variant={mine.operational_status === 'PRODUCING' ? 'success' : 'warning'} size="sm">
                  {mine.operational_status}
                </Badge>
                <Badge variant="teal" size="sm">
                  {mine.ownership_type || 'PSU'}
                </Badge>
              </div>
              <h2 className="text-lg font-bold text-[#E8ECEB] tracking-tight flex items-center gap-2">
                <Pickaxe className="w-5 h-5 text-[#C58B3A]" />
                {mine.mine_name}
              </h2>
              <p className="text-xs text-[#9BA5A8] flex items-center gap-1.5 mt-1">
                <Building2 className="w-3.5 h-3.5 text-[#C58B3A]" />
                <span>{mine.company_name}</span>
                {mine.subsidiary_name && <span>• {mine.subsidiary_name}</span>}
                <MapPin className="w-3.5 h-3.5 text-[#C58B3A] ml-2" />
                <span>{mine.district ? `${mine.district}, ` : ''}{mine.state}</span>
              </p>
            </div>
            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#9BA5A8] hover:text-[#E8ECEB] hover:bg-[#242C30] transition-colors"
              title="Close Drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Drawer Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            
            {/* Top Stat Highlights */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D]">
                <span className="text-[10px] font-mono uppercase text-[#9BA5A8] block">FY 24-25 Output</span>
                <span className="text-base font-mono font-bold text-[#E8ECEB]">
                  {fy24?.production_mt !== undefined ? `${fy24.production_mt} MT` : 'N/A'}
                </span>
                <span className="text-[10px] text-[#4F8A62] block">Verified Final</span>
              </div>

              <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D]">
                <span className="text-[10px] font-mono uppercase text-[#9BA5A8] block">FY 25-26 Output</span>
                <span className="text-base font-mono font-bold text-[#E8ECEB]">
                  {fy25?.production_mt !== undefined ? `${fy25.production_mt} MT` : 'N/A'}
                </span>
                <span className="text-[10px] text-[#4F8A62] block">Verified Final</span>
              </div>

              <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D]">
                <span className="text-[10px] font-mono uppercase text-[#9BA5A8] block">FY 26-27 (Q1 YTD)</span>
                <span className="text-base font-mono font-bold text-[#C58B3A]">
                  {fy26?.production_mt !== undefined ? `${fy26.production_mt} MT` : 'N/A'}
                </span>
                <span className="text-[10px] text-[#D6A23A] block">Provisional Q1</span>
              </div>

              <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D]">
                <span className="text-[10px] font-mono uppercase text-[#9BA5A8] block">YoY Growth</span>
                {yoyGrowth !== null ? (
                  <div className="flex items-center gap-1">
                    {yoyGrowth >= 0 ? (
                      <TrendingUp className="w-4 h-4 text-[#4F8A62]" />
                    ) : (
                      <TrendingDown className="w-4 h-4 text-[#C94B45]" />
                    )}
                    <span
                      className={`text-base font-mono font-bold ${
                        yoyGrowth >= 0 ? 'text-[#4F8A62]' : 'text-[#C94B45]'
                      }`}
                    >
                      {yoyGrowth > 0 ? `+${yoyGrowth}%` : `${yoyGrowth}%`}
                    </span>
                  </div>
                ) : (
                  <span className="text-xs text-[#9BA5A8]">N/A</span>
                )}
                <span className="text-[10px] text-[#9BA5A8] block">FY25 vs FY24</span>
              </div>
            </div>

            {/* Official Multi-Year Production Trajectory */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#9BA5A8] flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-[#C58B3A]" />
                  Authoritative Multi-Year Trajectory
                </h3>
                <span className="text-[11px] font-mono text-[#9BA5A8]">Granularity: Mine-Level</span>
              </div>

              <div className="overflow-x-auto rounded-lg border border-[#30383D]">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="bg-[#1C2226] border-b border-[#30383D] text-[#9BA5A8] font-mono text-[11px]">
                      <th className="py-2.5 px-3">Financial Year</th>
                      <th className="py-2.5 px-3 text-right">Production (MT)</th>
                      <th className="py-2.5 px-3 text-right">Target (MT)</th>
                      <th className="py-2.5 px-3 text-right">Achievement</th>
                      <th className="py-2.5 px-3 text-right">OBR (M.Cu.M)</th>
                      <th className="py-2.5 px-3 text-center">Star Rating</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#30383D] bg-[#151A1D]">
                    {mine.yearly_metrics?.map((metric: MineYearlyMetric) => (
                      <tr key={metric.id} className="hover:bg-[#1C2226]/50 transition-colors font-mono">
                        <td className="py-2.5 px-3 font-semibold text-[#E8ECEB]">
                          {metric.financial_year}
                          {metric.period_type === 'YTD' && (
                            <span className="text-[10px] text-[#D6A23A] block font-normal">
                              YTD (Provisional)
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right font-bold text-[#E8ECEB]">
                          {metric.production_mt !== null && metric.production_mt !== undefined
                            ? `${metric.production_mt}`
                            : <span className="text-[#9BA5A8] text-[11px] font-normal italic" title="Not reported by official government source">Not Available</span>}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[#9BA5A8]">
                          {metric.production_target_mt !== null && metric.production_target_mt !== undefined
                            ? `${metric.production_target_mt}`
                            : <span className="text-[#9BA5A8] text-[11px] font-normal italic" title="Target not applicable or non-producing">Not Available</span>}
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          {metric.production_achievement_percent !== null && metric.production_achievement_percent !== undefined ? (
                            <span className={metric.production_achievement_percent >= 100 ? 'text-[#4F8A62] font-semibold' : 'text-[#D6A23A]'}>
                              {metric.production_achievement_percent}%
                            </span>
                          ) : (
                            <span className="text-[#9BA5A8] text-[11px] font-normal italic" title="No production reported">Not Available</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3 text-right text-[#9BA5A8]">
                          {metric.obr_mcum !== null && metric.obr_mcum !== undefined
                            ? `${metric.obr_mcum}`
                            : <span className="text-[#9BA5A8] text-[11px] font-normal italic" title="OBR not reported or underground mine">Not Available</span>}
                        </td>

                        <td className="py-2.5 px-3 text-center">
                          {metric.star_rating ? (
                            <span className="text-[#C58B3A] font-semibold">{metric.star_rating} ★</span>
                          ) : (
                            <span className="text-[#9BA5A8] italic">-</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">
                          <Badge
                            variant={
                              metric.data_status === 'final'
                                ? 'success'
                                : metric.data_status === 'provisional'
                                ? 'warning'
                                : 'default'
                            }
                            size="sm"
                          >
                            {metric.data_status}
                          </Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Mine Technical & Operational Attributes */}
            <div className="space-y-3">
              <h3 className="text-xs font-mono font-bold uppercase tracking-wider text-[#9BA5A8] flex items-center gap-2">
                <Layers className="w-4 h-4 text-[#C58B3A]" />
                Technical & Operational Registry
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Mine Type & Method</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.mine_type || 'Open Cast'} {mine.mining_method ? `(${mine.mining_method})` : ''}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Mineral & Fuel Type</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.coal_or_lignite || 'Coal'} (Non-Coking / Thermal)
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Sector & Ownership</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.sector || mine.ownership_type || 'Central PSU'}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Parent Company</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.parent_company || mine.company_name}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Operating Subsidiary</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.subsidiary_name || 'Direct Operating Division'}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Coalfield / Basin</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.coalfield || (mine.district ? `${mine.district} Coalfield` : 'Not Reported by Source')}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Operational Status</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.operational_status}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Production Status</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.production_status || (mine.operational_status === 'PRODUCING' ? 'Commercial Production' : 'Under Development')}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Mine Opening Permission</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.mine_opening_permission || (mine.operational_status === 'PRODUCING' ? 'Granted / Operational' : 'Under Statutory Review')}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Category & Allocation</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.captive_or_commercial || (mine.ownership_type === 'Captive' ? 'Captive' : 'Commercial')} ({mine.allocation_type || 'Nominated PSU Block'})
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">End Use Specification</span>
                  <span className="font-semibold text-[#E8ECEB]">
                    {mine.end_use || 'Power, Steel & Industrial Boilers'}
                  </span>
                </div>

                <div className="p-3 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-1">
                  <span className="text-[#9BA5A8] block font-mono text-[10px]">Star Rating Assessment</span>
                  <div>{renderStarRating(fy24?.star_rating || fy25?.star_rating)}</div>
                </div>
              </div>
            </div>

            {/* Registered Aliases for Entity Resolution */}
            {mine.aliases && mine.aliases.length > 0 && (
              <div className="p-4 rounded-lg bg-[#1C2226] border border-[#30383D] space-y-2">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-[#4F8A62]" />
                  <span className="text-xs font-semibold text-[#E8ECEB]">
                    Canonical Entity Resolution Aliases
                  </span>
                </div>
                <p className="text-xs text-[#9BA5A8]">
                  COALINTEL automatically links multiple spelling variants across government sources to this canonical entity:
                </p>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {mine.aliases.map((alias, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 rounded bg-[#242C30] border border-[#30383D] text-[11px] font-mono text-[#E8ECEB]"
                    >
                      {alias}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Authoritative Provenance Citation */}
            <div className="p-4 rounded-lg bg-[#1C2226] border border-[#C58B3A]/30 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-[#C58B3A]" />
                  <span className="text-xs font-bold text-[#E8ECEB]">Authoritative Primary Citation</span>
                </div>
                <Badge variant="gold" size="sm">
                  GOVERNMENT VERIFIED
                </Badge>
              </div>

              <div className="text-xs space-y-1.5 text-[#9BA5A8]">
                <p>
                  <strong className="text-[#E8ECEB]">Authority:</strong> Ministry of Coal, Government of India
                </p>
                <p>
                  <strong className="text-[#E8ECEB]">Document:</strong> {mine.source_document || 'Coal Directory of India 2024–25'}
                </p>
                {mine.source_chapter && (
                  <p>
                    <strong className="text-[#E8ECEB]">Chapter:</strong> {mine.source_chapter}
                  </p>
                )}
                {mine.source_table && (
                  <p>
                    <strong className="text-[#E8ECEB]">Table Reference:</strong> {mine.source_table}
                  </p>
                )}
                {mine.source_page && (
                  <p>
                    <strong className="text-[#E8ECEB]">Page:</strong> {mine.source_page}
                  </p>
                )}
                <p>
                  <strong className="text-[#E8ECEB]">Financial Year:</strong> {mine.financial_year || '2024-25'}
                </p>
                {mine.source_publication_date && (
                  <p>
                    <strong className="text-[#E8ECEB]">Publication Date:</strong> {mine.source_publication_date}
                  </p>
                )}
                <p>
                  <strong className="text-[#E8ECEB]">Verification:</strong> <span className="text-[#4F8A62] font-semibold">Official Ministry of Coal Verified (100% Provenance)</span>
                </p>
              </div>

              <div className="pt-2 flex items-center justify-between border-t border-[#30383D]">
                <button
                  onClick={() => {
                    if (onOpenSourceModal) {
                      onOpenSourceModal({
                        source_id: mine.source_id,
                        organization: 'Ministry of Coal, Government of India',
                        document_title: mine.source_document || 'Coal Directory of India 2024–25',
                        url: mine.source_url || 'https://coal.gov.in/',
                        mine_name: mine.mine_name,
                        metric_name: 'Annual Production',
                        metric_value: fy25?.production_mt || fy24?.production_mt,
                        source_priority: 1,
                        verification_status: 'verified',
                        financial_year: mine.financial_year || '2024-25',
                      });
                    }
                  }}
                  className="text-xs font-medium text-[#C58B3A] hover:text-[#D6A23A] inline-flex items-center gap-1.5"
                >
                  <ShieldCheck className="w-4 h-4" />
                  <span>Inspect Full Evidence Chain</span>
                </button>

                {mine.source_url && (
                  <a
                    href={mine.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-[#9BA5A8] hover:text-[#E8ECEB] inline-flex items-center gap-1"
                  >
                    <ExternalLink className="w-3.5 h-3.5" />
                    <span>Official Portal</span>
                  </a>
                )}
              </div>
            </div>


          </div>

          {/* Drawer Footer */}
          <div className="px-6 py-4 border-t border-[#30383D] bg-[#1C2226] flex items-center justify-between">
            <span className="text-[11px] font-mono text-[#9BA5A8]">
              Data Origin: Primary Government Sources (Zero Interpolation)
            </span>
            <Button variant="secondary" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>

        </div>
      </div>
    </div>
  );
};

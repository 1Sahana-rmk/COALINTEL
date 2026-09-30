'use client';

import React, { useMemo } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { Card } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { MineSummary } from '@/lib/api/minesApi';
import { BarChart3, PieChart as PieIcon, MapPin, Building2, Layers, Award, Pickaxe } from 'lucide-react';

interface MinesVisualAnalyticsProps {
  mines: MineSummary[];
}

const PALETTE = [
  '#C58B3A', // Primary Gold/Amber
  '#4F8A62', // Success Green
  '#54788A', // Info Blue-Grey
  '#D6A23A', // Warning Amber
  '#8C52FF', // Purple
  '#00C49F', // Teal
  '#C94B45', // Error Red
  '#E8ECEB', // Bone White
  '#9BA5A8'  // Muted Grey
];

export const MinesVisualAnalytics: React.FC<MinesVisualAnalyticsProps> = ({ mines }) => {
  // 1. Mines by State
  const stateData = useMemo(() => {
    const map: Record<string, number> = {};
    mines.forEach((m) => {
      if (m.state) map[m.state] = (map[m.state] || 0) + 1;
    });
    return Object.entries(map)
      .map(([state, count]) => ({ state, count }))
      .sort((a, b) => b.count - a.count);
  }, [mines]);

  // 2. Mines by Subsidiary (Top 10)
  const subsidiaryData = useMemo(() => {
    const map: Record<string, number> = {};
    mines.forEach((m) => {
      const sub = m.subsidiary_name || m.company_name || 'Other';
      map[sub] = (map[sub] || 0) + 1;
    });
    return Object.entries(map)
      .map(([subsidiary, count]) => ({ subsidiary, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  }, [mines]);

  // 3. Mine Type Breakdown (OC, UG, Mixed)
  const typeData = useMemo(() => {
    const map: Record<string, number> = { 'Open Cast (OC)': 0, 'Underground (UG)': 0, 'Mixed': 0 };
    mines.forEach((m) => {
      if (m.mine_type === 'OC') map['Open Cast (OC)']++;
      else if (m.mine_type === 'UG') map['Underground (UG)']++;
      else if (m.mine_type === 'Mixed') map['Mixed']++;
    });
    return Object.entries(map)
      .filter(([_, count]) => count > 0)
      .map(([name, value]) => ({ name, value }));
  }, [mines]);

  // 4. Coal vs Lignite Breakdown
  const fuelData = useMemo(() => {
    let coal = 0;
    let lignite = 0;
    mines.forEach((m) => {
      if ((m.coal_or_lignite || '').toLowerCase() === 'lignite') lignite++;
      else coal++;
    });
    return [
      { name: 'Coal', value: coal },
      { name: 'Lignite', value: lignite }
    ].filter((d) => d.value > 0);
  }, [mines]);

  // 5. Sector Breakdown
  const sectorData = useMemo(() => {
    const map: Record<string, number> = {};
    mines.forEach((m) => {
      const sec = m.ownership_type || 'Other';
      map[sec] = (map[sec] || 0) + 1;
    });
    return Object.entries(map)
      .map(([sector, count]) => ({ sector, count }))
      .sort((a, b) => b.count - a.count);
  }, [mines]);

  // 6. Mine Operational Status
  const statusData = useMemo(() => {
    const map: Record<string, number> = {};
    mines.forEach((m) => {
      const st = (m.operational_status || 'PRODUCING').replace(/_/g, ' ');
      map[st] = (map[st] || 0) + 1;
    });
    return Object.entries(map)
      .map(([status, count]) => ({ status, count }))
      .sort((a, b) => b.count - a.count);
  }, [mines]);

  // 7. Top Producing Mines (FY 2025-26 or latest authentic output)
  const topProducersData = useMemo(() => {
    return mines
      .filter((m) => m.production_fy25_26 !== null && m.production_fy25_26 !== undefined && m.production_fy25_26 > 0)
      .map((m) => ({
        mine: m.mine_name.replace(' OpenCast', '').replace(' OCP', ''),
        production: m.production_fy25_26 as number,
        subsidiary: m.subsidiary_name || m.company_name
      }))
      .sort((a, b) => b.production - a.production)
      .slice(0, 10);
  }, [mines]);

  const CustomChartTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || !payload.length) return null;
    return (
      <div className="p-2.5 rounded-lg bg-[#151A1D] border border-[#30383D] shadow-xl text-xs space-y-1">
        <span className="font-bold text-[#E8ECEB] block font-mono">{label || payload[0].name}</span>
        <div className="flex items-center gap-2">
          <span className="text-[#9BA5A8]">Value:</span>
          <span className="font-mono font-bold text-[#C58B3A]">
            {payload[0].value} {payload[0].unit || (payload[0].dataKey === 'production' ? 'MT' : 'Mines')}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Visual Analytics Header */}
      <div className="p-4 rounded-xl bg-[#151A1D] border border-[#30383D] flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-[#E8ECEB] flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-[#C58B3A]" />
            Mines Visual Analytics & Distribution
            <Badge variant="gold" size="sm">SYNCHRONIZED WITH FILTERS</Badge>
          </h3>
          <p className="text-xs text-[#9BA5A8] mt-0.5">
            Real-time visual distribution calculated across {mines.length} canonical mines in active scope.
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-[#9BA5A8]">
          <span>Charts update automatically on filter changes</span>
        </div>
      </div>

      {/* Charts Grid Row 1: State Distribution & Top Producing Mines */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        
        {/* Chart 1: State Distribution */}
        <Card variant="bordered" className="p-4 bg-[#151A1D] border-[#30383D]">
          <div className="flex items-center justify-between mb-3 border-b border-[#30383D] pb-2">
            <h4 className="text-xs font-bold text-[#E8ECEB] uppercase font-mono tracking-wider flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-[#C58B3A]" />
              1. Mines by State ({stateData.length} States)
            </h4>
            <Badge variant="secondary" size="sm">{mines.length} Mines</Badge>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stateData} margin={{ top: 10, right: 10, left: -20, bottom: 35 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30383D" vertical={false} />
                <XAxis 
                  dataKey="state" 
                  stroke="#9BA5A8" 
                  fontSize={10} 
                  angle={-35} 
                  textAnchor="end" 
                  interval={0} 
                />
                <YAxis stroke="#9BA5A8" fontSize={10} allowDecimals={false} />
                <Tooltip content={<CustomChartTooltip />} />
                <Bar dataKey="count" fill="#C58B3A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Chart 7: Top Producing Mines Output */}
        <Card variant="bordered" className="p-4 bg-[#151A1D] border-[#30383D]">
          <div className="flex items-center justify-between mb-3 border-b border-[#30383D] pb-2">
            <h4 className="text-xs font-bold text-[#E8ECEB] uppercase font-mono tracking-wider flex items-center gap-2">
              <Award className="w-3.5 h-3.5 text-[#4F8A62]" />
              7. Top Producing Mines Output (FY 25-26 MT)
            </h4>
            <Badge variant="gold" size="sm">Top 10 Mega-Mines</Badge>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={topProducersData} layout="vertical" margin={{ top: 5, right: 20, left: 40, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30383D" horizontal={false} />
                <XAxis type="number" stroke="#9BA5A8" fontSize={10} unit=" MT" />
                <YAxis dataKey="mine" type="category" stroke="#9BA5A8" fontSize={10} width={90} />
                <Tooltip content={<CustomChartTooltip />} />
                <Bar dataKey="production" fill="#4F8A62" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

      </div>

      {/* Charts Grid Row 2: Subsidiary & Sector Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        
        {/* Chart 2: Subsidiary Distribution */}
        <Card variant="bordered" className="p-4 bg-[#151A1D] border-[#30383D]">
          <div className="flex items-center justify-between mb-3 border-b border-[#30383D] pb-2">
            <h4 className="text-xs font-bold text-[#E8ECEB] uppercase font-mono tracking-wider flex items-center gap-2">
              <Building2 className="w-3.5 h-3.5 text-[#54788A]" />
              2. Mines by Subsidiary / Entity
            </h4>
            <Badge variant="info" size="sm">Top Operating Entities</Badge>
          </div>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={subsidiaryData} margin={{ top: 10, right: 10, left: -20, bottom: 25 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30383D" vertical={false} />
                <XAxis dataKey="subsidiary" stroke="#9BA5A8" fontSize={10} angle={-30} textAnchor="end" interval={0} />
                <YAxis stroke="#9BA5A8" fontSize={10} allowDecimals={false} />
                <Tooltip content={<CustomChartTooltip />} />
                <Bar dataKey="count" fill="#54788A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Chart 5: Sector Breakdown */}
        <Card variant="bordered" className="p-4 bg-[#151A1D] border-[#30383D]">
          <div className="flex items-center justify-between mb-3 border-b border-[#30383D] pb-2">
            <h4 className="text-xs font-bold text-[#E8ECEB] uppercase font-mono tracking-wider flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-[#D6A23A]" />
              5. Mines by Sector & Ownership
            </h4>
            <Badge variant="warning" size="sm">Public vs Private vs Captive</Badge>
          </div>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={sectorData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30383D" vertical={false} />
                <XAxis dataKey="sector" stroke="#9BA5A8" fontSize={10} interval={0} />
                <YAxis stroke="#9BA5A8" fontSize={10} allowDecimals={false} />
                <Tooltip content={<CustomChartTooltip />} />
                <Bar dataKey="count" fill="#D6A23A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

      </div>

      {/* Charts Grid Row 3: Mine Types, Coal/Lignite & Mine Operational Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        
        {/* Chart 3: Mine Type Breakdown */}
        <Card variant="bordered" className="p-4 bg-[#151A1D] border-[#30383D]">
          <div className="flex items-center justify-between mb-3 border-b border-[#30383D] pb-2">
            <h4 className="text-xs font-bold text-[#E8ECEB] uppercase font-mono tracking-wider flex items-center gap-2">
              <Pickaxe className="w-3.5 h-3.5 text-[#C58B3A]" />
              3. Mine Type
            </h4>
            <span className="text-[10px] text-[#9BA5A8]">OC, UG, Mixed</span>
          </div>
          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={typeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={35}
                  outerRadius={65}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {typeData.map((_, index) => (
                    <Cell key={`cell-type-${index}`} fill={PALETTE[index % PALETTE.length]} stroke="#151A1D" strokeWidth={2} />
                  ))}
                </Pie>
                <Tooltip content={<CustomChartTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Chart 4: Coal vs Lignite Breakdown */}
        <Card variant="bordered" className="p-4 bg-[#151A1D] border-[#30383D]">
          <div className="flex items-center justify-between mb-3 border-b border-[#30383D] pb-2">
            <h4 className="text-xs font-bold text-[#E8ECEB] uppercase font-mono tracking-wider flex items-center gap-2">
              <PieIcon className="w-3.5 h-3.5 text-[#4F8A62]" />
              4. Coal vs Lignite
            </h4>
            <span className="text-[10px] text-[#9BA5A8]">Primary Fuel</span>
          </div>
          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={fuelData}
                  cx="50%"
                  cy="50%"
                  innerRadius={35}
                  outerRadius={65}
                  paddingAngle={4}
                  dataKey="value"
                >
                  <Cell fill="#C58B3A" stroke="#151A1D" strokeWidth={2} />
                  <Cell fill="#4F8A62" stroke="#151A1D" strokeWidth={2} />
                </Pie>
                <Tooltip content={<CustomChartTooltip />} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Chart 6: Operational Status */}
        <Card variant="bordered" className="p-4 bg-[#151A1D] border-[#30383D]">
          <div className="flex items-center justify-between mb-3 border-b border-[#30383D] pb-2">
            <h4 className="text-xs font-bold text-[#E8ECEB] uppercase font-mono tracking-wider flex items-center gap-2">
              <Layers className="w-3.5 h-3.5 text-[#D6A23A]" />
              6. Mine Status
            </h4>
            <span className="text-[10px] text-[#9BA5A8]">Operational Life</span>
          </div>
          <div className="h-52 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusData} layout="vertical" margin={{ top: 5, right: 15, left: 10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#30383D" horizontal={false} />
                <XAxis type="number" stroke="#9BA5A8" fontSize={10} allowDecimals={false} />
                <YAxis dataKey="status" type="category" stroke="#9BA5A8" fontSize={9} width={90} />
                <Tooltip content={<CustomChartTooltip />} />
                <Bar dataKey="count" fill="#C58B3A" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

      </div>
    </div>
  );
};

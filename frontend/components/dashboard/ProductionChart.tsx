'use client';

import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/Card';
import { BarChart3 } from 'lucide-react';
import { ProductionSeriesItem } from '@/types/dashboard';

interface ProductionChartProps {
  data?: ProductionSeriesItem[];
  loading?: boolean;
  isApiConnected?: boolean;
}

interface CustomTooltipProps {
  active?: boolean;
  payload?: any[];
  label?: string;
}

const CustomTooltip: React.FC<CustomTooltipProps> = ({
  active,
  payload,
  label,
}) => {
  if (!active || !payload || payload.length === 0) return null;

  const actualItem = payload.find((p) => p.dataKey === 'actual');
  const targetItem = payload.find((p) => p.dataKey === 'target');

  const actualVal =
    actualItem?.value !== undefined ? Number(actualItem.value) : null;

  const targetVal =
    targetItem?.value !== undefined ? Number(targetItem.value) : null;

  const hasActual = actualVal !== null && !Number.isNaN(actualVal);
  const hasTarget = targetVal !== null && !Number.isNaN(targetVal);

  const variance =
    hasActual && hasTarget ? actualVal! - targetVal! : null;

  const variancePercent =
    variance !== null && targetVal! > 0
      ? (variance / targetVal!) * 100
      : null;

  const isSurplus = variance !== null && variance >= 0;

  return (
    <div className="bg-[#151A1D] border border-[#30383D] rounded-lg p-3 shadow-dropdown text-xs space-y-2 min-w-[200px]">
      <div className="flex items-center justify-between border-b border-[#30383D] pb-1.5">
        <span className="font-bold text-[#E8ECEB] font-mono">
          {label} Subsidiary
        </span>

        {variancePercent !== null && (
          <span
            className={`font-mono font-semibold text-[10px] px-1.5 py-0.5 rounded ${
              isSurplus
                ? 'text-[#4F8A62] bg-[#4F8A62]/15 border border-[#4F8A62]/30'
                : 'text-[#D6A23A] bg-[#D6A23A]/15 border border-[#D6A23A]/30'
            }`}
          >
            {isSurplus ? '+' : ''}
            {variancePercent.toFixed(1)}% vs Target
          </span>
        )}
      </div>

      <div className="space-y-1 font-mono text-[11px]">
        <div className="flex items-center justify-between">
          <span className="text-[#9BA5A8] flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm bg-[#C58B3A]" />
            Actual Production:
          </span>

          <span className="font-bold text-[#E8ECEB]">
            {hasActual ? `${actualVal!.toFixed(1)} MT` : 'Unavailable'}
          </span>
        </div>

        <div className="flex items-center justify-between">
          <span className="text-[#9BA5A8] flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-sm bg-[#54788A]" />
            Annual Target:
          </span>

          <span className="font-bold text-[#E8ECEB]">
            {hasTarget ? `${targetVal!.toFixed(1)} MT` : 'Unavailable'}
          </span>
        </div>

        {variance !== null && (
          <div className="flex items-center justify-between pt-1 border-t border-[#30383D]/60 text-[10px]">
            <span className="text-[#9BA5A8]">Net Delta:</span>

            <span
              className={`font-semibold ${
                isSurplus
                  ? 'text-[#4F8A62]'
                  : 'text-[#D6A23A]'
              }`}
            >
              {isSurplus ? '+' : ''}
              {variance.toFixed(1)} MT
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

export const ProductionChart: React.FC<ProductionChartProps> = ({
  data = [],
  loading = false,
  isApiConnected = false,
}) => {
  const chartSeries = data;

  return (
    <Card className="col-span-1 lg:col-span-2 bg-[#1C2226] border-[#30383D]">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>
            <BarChart3 className="h-5 w-5 text-[#C58B3A]" />
            <span>Subsidiary Coal Production vs Target (MT)</span>
          </CardTitle>

          <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-[#242C30] text-[#9BA5A8] border border-[#30383D]">
            {isApiConnected ? 'Live API Data' : 'API Not Connected'}
          </span>
        </div>

        <CardDescription>
          Deterministic comparison of extracted actual coal production
          figures against operational target plans across CIL subsidiaries.
        </CardDescription>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="h-72 w-full animate-pulse rounded-lg bg-[#242C30]" />
        ) : chartSeries.length === 0 ? (
          <div className="h-72 w-full flex flex-col items-center justify-center p-6 text-center text-xs font-mono text-[#9BA5A8] border border-dashed border-[#30383D] rounded-lg bg-[#151A1D]">
            <BarChart3 className="h-8 w-8 text-[#9BA5A8]/50 mb-2" />

            <span className="text-[#E8ECEB] font-semibold">
              No Verified Production Data Available
            </span>

            <span className="text-[11px] mt-1 max-w-sm">
              No verified production metrics were found for the selected
              subsidiary scope and fiscal year. Ingest documents to view
              live analytics.
            </span>
          </div>
        ) : (
          <div className="h-72 w-full pt-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartSeries}
                margin={{
                  top: 10,
                  right: 10,
                  left: -20,
                  bottom: 0,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#30383D"
                  opacity={0.6}
                  vertical={false}
                />

                <XAxis
                  dataKey="subsidiary"
                  stroke="#9BA5A8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#30383D' }}
                  dy={4}
                />

                <YAxis
                  stroke="#9BA5A8"
                  fontSize={11}
                  tickLine={false}
                  axisLine={{ stroke: '#30383D' }}
                />

                <Tooltip
                  content={<CustomTooltip />}
                  cursor={{ fill: 'rgba(197, 139, 58, 0.08)' }}
                />

                <Legend
                  wrapperStyle={{
                    fontSize: '11px',
                    paddingTop: '12px',
                    color: '#9BA5A8',
                  }}
                  iconSize={10}
                  iconType="rect"
                />

                <Bar
                  dataKey="actual"
                  name="Actual Production (MT)"
                  fill="#C58B3A"
                  radius={[3, 3, 0, 0]}
                  animationDuration={700}
                  animationEasing="ease-out"
                />

                <Bar
                  dataKey="target"
                  name="Target Plan (MT)"
                  fill="#54788A"
                  radius={[3, 3, 0, 0]}
                  animationDuration={700}
                  animationEasing="ease-out"
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
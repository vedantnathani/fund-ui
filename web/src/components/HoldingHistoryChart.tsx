'use client';

import { useState } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts';
import { HistoryDataPoint } from '@/types';

interface HoldingHistoryChartProps {
  data: HistoryDataPoint[];
  holdings: string[];
}

const PALETTE = [
  '#34D399', // Emerald
  '#818CF8', // Indigo
  '#FBBF24', // Amber
  '#F472B6', // Pink
  '#60A5FA', // Blue
  '#A78BFA', // Purple
  '#2DD4BF', // Teal
  '#FB923C', // Orange
  '#38BDF8', // Sky
  '#FB7185', // Rose
];

export default function HoldingHistoryChart({ data, holdings }: HoldingHistoryChartProps) {
  // Track visible lines (default: top 5 enabled, remaining toggleable)
  const [visibleHoldings, setVisibleHoldings] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    holdings.forEach((h, idx) => {
      initial[h] = idx < 6; // Show top 6 by default for uncluttered chart
    });
    return initial;
  });

  const toggleHolding = (name: string) => {
    setVisibleHoldings((prev) => ({
      ...prev,
      [name]: !prev[name],
    }));
  };

  if (!data || data.length === 0 || holdings.length === 0) {
    return (
      <div className="py-12 text-center text-xs text-gray-500">
        Insufficient historical data points to generate trend chart.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-white">Top Holdings Weight Trajectory (% of AUM)</h3>
        <span className="text-[11px] text-gray-400">Click stock pills to toggle lines</span>
      </div>

      {/* Interactive Stock Filter Pills */}
      <div className="flex flex-wrap gap-2">
        {holdings.map((name, idx) => {
          const isVisible = visibleHoldings[name];
          const color = PALETTE[idx % PALETTE.length];

          return (
            <button
              key={name}
              type="button"
              onClick={() => toggleHolding(name)}
              className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-all ${
                isVisible
                  ? 'bg-white/10 text-white border border-white/20 shadow-sm'
                  : 'bg-white/[0.02] text-gray-500 border border-white/5 opacity-50 hover:opacity-80'
              }`}
            >
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: isVisible ? color : '#6B7280' }}
              />
              <span className="truncate max-w-[120px]">{name}</span>
            </button>
          );
        })}
      </div>

      {/* Recharts Multi-line Chart Container */}
      <div className="w-full h-[360px] pt-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" vertical={false} />
            <XAxis
              dataKey="month"
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
            />
            <YAxis
              stroke="#6B7280"
              fontSize={12}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              content={({ active, payload, label }) => {
                if (!active || !payload || payload.length === 0) return null;
                return (
                  <div className="glass-panel p-3 rounded-xl border border-white/10 shadow-2xl space-y-2 text-xs">
                    <div className="font-semibold text-gray-200 border-b border-white/10 pb-1">
                      Report: {label}
                    </div>
                    <div className="space-y-1">
                      {payload
                        .filter((p) => p.value !== undefined && Number(p.value) > 0)
                        .sort((a, b) => Number(b.value) - Number(a.value))
                        .map((entry) => (
                          <div key={entry.name} className="flex items-center justify-between gap-4">
                            <span className="flex items-center gap-1.5 text-gray-300">
                              <span
                                className="w-2 h-2 rounded-full"
                                style={{ backgroundColor: entry.color }}
                              />
                              <span className="truncate max-w-[160px]">{entry.name}:</span>
                            </span>
                            <span className="font-mono font-semibold text-white">
                              {Number(entry.value).toFixed(2)}%
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                );
              }}
            />
            {holdings.map((name, idx) => {
              if (!visibleHoldings[name]) return null;
              const color = PALETTE[idx % PALETTE.length];

              return (
                <Line
                  key={name}
                  type="monotone"
                  dataKey={name}
                  name={name}
                  stroke={color}
                  strokeWidth={2.5}
                  dot={{ r: 4, fill: color, strokeWidth: 1, stroke: '#0B0F17' }}
                  activeDot={{ r: 6, fill: color }}
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

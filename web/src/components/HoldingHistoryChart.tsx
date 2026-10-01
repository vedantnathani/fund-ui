'use client';

import { useState, useMemo } from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { HistoryDataPoint } from '@/types';
import { ChevronLeft, ChevronRight } from 'lucide-react';

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

const WINDOW_SIZE = 6; // months visible at once

export default function HoldingHistoryChart({ data, holdings }: HoldingHistoryChartProps) {
  // Track visible lines (default: top 5 enabled, remaining toggleable)
  const [visibleHoldings, setVisibleHoldings] = useState<Record<string, boolean>>(() => {
    const initial: Record<string, boolean> = {};
    holdings.forEach((h, idx) => {
      initial[h] = idx < 5;
    });
    return initial;
  });

  // Window offset — 0 means showing the most recent WINDOW_SIZE months
  const totalMonths = data.length;
  const maxOffset = Math.max(0, totalMonths - WINDOW_SIZE);

  // offset = 0 → show last WINDOW_SIZE months; offset = maxOffset → show first WINDOW_SIZE months
  // We store offset from the END (0 = newest, maxOffset = oldest)
  const [windowEnd, setWindowEnd] = useState(0); // 0 means newest end

  const windowedData = useMemo(() => {
    if (totalMonths <= WINDOW_SIZE) return data;
    const endIdx = totalMonths - windowEnd;
    const startIdx = Math.max(0, endIdx - WINDOW_SIZE);
    return data.slice(startIdx, endIdx);
  }, [data, windowEnd, totalMonths]);

  const canGoNewer = windowEnd > 0;
  const canGoOlder = windowEnd < maxOffset;

  const goNewer = () => setWindowEnd((prev) => Math.max(0, prev - 1));
  const goOlder = () => setWindowEnd((prev) => Math.min(maxOffset, prev + 1));

  const toggleHolding = (name: string) => {
    setVisibleHoldings((prev) => ({
      ...prev,
      [name]: !prev[name],
    }));
  };

  const currentWindowLabel = useMemo(() => {
    if (windowedData.length === 0) return '';
    const first = windowedData[0]?.month as string;
    const last = windowedData[windowedData.length - 1]?.month as string;
    if (first === last) return first;
    return `${first} → ${last}`;
  }, [windowedData]);

  if (!data || data.length === 0 || holdings.length === 0) {
    return (
      <div className="py-12 text-center text-xs text-gray-500">
        Insufficient historical data points to generate trend chart.
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-white">Top Holdings Weight Trajectory (% of AUM)</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">Click stock pills to toggle · use arrows to navigate time</p>
        </div>

        {/* Window Navigator — only shown when data > window size */}
        {totalMonths > WINDOW_SIZE && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-gray-400 bg-white/[0.04] border border-white/10 px-2.5 py-1 rounded-lg">
              {currentWindowLabel}
            </span>
            <button
              type="button"
              onClick={goOlder}
              disabled={!canGoOlder}
              title="Show older months"
              className="p-1.5 rounded-lg bg-white/[0.04] border border-white/10 text-gray-400 hover:text-white hover:bg-white/[0.09] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={goNewer}
              disabled={!canGoNewer}
              title="Show newer months"
              className="p-1.5 rounded-lg bg-white/[0.04] border border-white/10 text-gray-400 hover:text-white hover:bg-white/[0.09] transition-all disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
            {/* Dot indicator */}
            <div className="flex items-center gap-1 pl-1">
              {Array.from({ length: Math.ceil(totalMonths / WINDOW_SIZE) }).map((_, i) => {
                const pageStart = maxOffset - i * WINDOW_SIZE;
                const isActive = windowEnd >= pageStart && windowEnd < pageStart + WINDOW_SIZE;
                return (
                  <span
                    key={i}
                    className={`w-1.5 h-1.5 rounded-full transition-all ${isActive ? 'bg-indigo-400' : 'bg-white/20'}`}
                  />
                );
              })}
            </div>
          </div>
        )}
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

      {/* Range slider for fine-grained month scrubbing (visible when > window size) */}
      {totalMonths > WINDOW_SIZE && (
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-gray-500 shrink-0">Oldest</span>
          <input
            type="range"
            min={0}
            max={maxOffset}
            value={maxOffset - windowEnd}  // invert so right = newer
            onChange={(e) => setWindowEnd(maxOffset - Number(e.target.value))}
            className="flex-1 h-1 accent-indigo-500 cursor-pointer"
            aria-label="Scroll through months"
          />
          <span className="text-[11px] text-gray-500 shrink-0">Latest</span>
        </div>
      )}

      {/* Recharts Multi-line Chart Container */}
      <div className="w-full h-[340px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={windowedData} margin={{ top: 10, right: 15, left: -15, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255, 255, 255, 0.05)" vertical={false} />
            <XAxis
              dataKey="month"
              stroke="#6B7280"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255, 255, 255, 0.1)' }}
              interval={0}
              tick={{ fill: '#9CA3AF' }}
            />
            <YAxis
              stroke="#6B7280"
              fontSize={11}
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
                  connectNulls
                />
              );
            })}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Month count indicator */}
      {totalMonths > WINDOW_SIZE && (
        <p className="text-center text-[11px] text-gray-500">
          Showing {windowedData.length} of {totalMonths} months · Use the slider or arrows to navigate
        </p>
      )}
    </div>
  );
}

'use client';

import { useState, useMemo, useEffect } from 'react';
import {
  Calendar,
  CloudDownload,
  Loader2,
  X,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Info,
} from 'lucide-react';
import { triggerBackfill } from '@/lib/github';

interface SchemeOption {
  id: string;
  name: string;
  amc?: string;
}

interface BackfillModalProps {
  isOpen: boolean;
  onClose: () => void;
  funds: SchemeOption[];
  initialFundId?: string;
  onSuccess?: (message: string, runUrl?: string) => void;
  onError?: (error: string) => void;
}

const MONTH_NAMES = [
  { value: '01', label: 'January' },
  { value: '02', label: 'February' },
  { value: '03', label: 'March' },
  { value: '04', label: 'April' },
  { value: '05', label: 'May' },
  { value: '06', label: 'June' },
  { value: '07', label: 'July' },
  { value: '08', label: 'August' },
  { value: '09', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' },
];

function getMonthOffset(monthsAgo: number): { year: string; month: string } {
  const d = new Date();
  d.setMonth(d.getMonth() - monthsAgo);
  const year = String(d.getFullYear());
  const month = String(d.getMonth() + 1).padStart(2, '0');
  return { year, month };
}

export default function BackfillModal({
  isOpen,
  onClose,
  funds,
  initialFundId = 'all',
  onSuccess,
  onError,
}: BackfillModalProps) {
  const currentYearNum = new Date().getFullYear();
  const currentMonthNum = String(new Date().getMonth() + 1).padStart(2, '0');

  // Available years from 2013 (PPFAS inception) to current year
  const years = useMemo(() => {
    const list: string[] = [];
    for (let y = currentYearNum; y >= 2013; y--) {
      list.push(String(y));
    }
    return list;
  }, [currentYearNum]);

  // Default start = 12 months ago, end = current month
  const defaultStart = useMemo(() => getMonthOffset(12), []);
  const defaultEnd = useMemo(() => getMonthOffset(0), []);

  const [selectedFundId, setSelectedFundId] = useState(initialFundId);
  const [startYear, setStartYear] = useState(defaultStart.year);
  const [startMonth, setStartMonth] = useState(defaultStart.month);
  const [endYear, setEndYear] = useState(defaultEnd.year);
  const [endMonth, setEndMonth] = useState(defaultEnd.month);
  const [dryRun, setDryRun] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Sync initialFundId when opened
  useEffect(() => {
    if (isOpen) {
      setSelectedFundId(initialFundId);
      setValidationError(null);
    }
  }, [isOpen, initialFundId]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  const startFormatted = `${startYear}-${startMonth}`;
  const endFormatted = `${endYear}-${endMonth}`;

  // Calculate span count in months
  const monthsCount = useMemo(() => {
    const yDiff = Number(endYear) - Number(startYear);
    const mDiff = Number(endMonth) - Number(startMonth);
    const total = yDiff * 12 + mDiff + 1;
    return total;
  }, [startYear, startMonth, endYear, endMonth]);

  // Preset handlers
  const handleApplyPreset = (months: number | 'ytd') => {
    const end = getMonthOffset(0);
    setEndYear(end.year);
    setEndMonth(end.month);

    if (months === 'ytd') {
      setStartYear(String(currentYearNum));
      setStartMonth('01');
    } else {
      const start = getMonthOffset(months);
      setStartYear(start.year);
      setStartMonth(start.month);
    }
    setValidationError(null);
  };

  const handleSubmit = async () => {
    setValidationError(null);

    if (startFormatted > endFormatted) {
      setValidationError(`Start period (${startFormatted}) cannot be after end period (${endFormatted}).`);
      return;
    }

    setSubmitting(true);
    const result = await triggerBackfill({
      fundId: selectedFundId,
      startMonth: startFormatted,
      endMonth: endFormatted,
      dryRun,
    });
    setSubmitting(false);

    if (result.success) {
      const targetName =
        selectedFundId === 'all'
          ? 'all tracked schemes'
          : funds.find((f) => f.id === selectedFundId)?.name || selectedFundId;

      onClose();
      if (onSuccess) {
        onSuccess(
          `Backfill queued for ${targetName} (${startFormatted} → ${endFormatted}). GitHub Actions is processing the downloads in the background (~1-2 mins). Refresh the page once the action finishes to view new data.`,
          result.runUrl
        );
      }
    } else {
      const err = result.error || 'Failed to dispatch backfill request.';
      setValidationError(err);
      if (onError) onError(err);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm transition-opacity animate-in fade-in duration-200"
        onClick={onClose}
      />

      {/* Modal Dialog */}
      <div className="relative w-full max-w-xl glass-panel rounded-2xl border border-white/10 shadow-2xl overflow-hidden z-10 animate-in zoom-in-95 duration-200">
        {/* Subtle decorative top border glow */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-teal-400 to-emerald-400" />

        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-white/5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
              <CloudDownload className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white leading-tight">
                Historical Data Backfill
              </h2>
              <p className="text-xs text-gray-400">
                Fetch and extract past monthly portfolio disclosures
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-6 max-h-[75vh] overflow-y-auto">
          {/* Scheme Selection */}
          <div className="space-y-2">
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider">
              Target Scheme
            </label>
            <div className="relative">
              <select
                value={selectedFundId}
                onChange={(e) => setSelectedFundId(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 appearance-none"
              >
                <option value="all" className="bg-[#0E131F] text-white">
                  ⚡ All Tracked Schemes (Bulk Ingestion)
                </option>
                {funds.map((f) => (
                  <option key={f.id} value={f.id} className="bg-[#0E131F] text-white">
                    {f.name} ({f.amc || 'Mutual Fund'})
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute right-3.5 top-1/2 -translate-y-1/2 text-gray-400 text-xs">
                ▼
              </div>
            </div>
          </div>

          {/* Quick Presets */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">
                Quick Range Presets
              </span>
              <span className="text-[11px] text-gray-500">Auto-sets start and end</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                type="button"
                onClick={() => handleApplyPreset(6)}
                className="px-3 py-2 rounded-xl text-xs font-medium bg-white/[0.03] hover:bg-white/[0.08] text-gray-300 hover:text-white border border-white/5 transition-all text-center"
              >
                Last 6 Months
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(12)}
                className="px-3 py-2 rounded-xl text-xs font-medium bg-white/[0.03] hover:bg-white/[0.08] text-gray-300 hover:text-white border border-white/5 transition-all text-center"
              >
                Last 12 Months
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset(36)}
                className="px-3 py-2 rounded-xl text-xs font-medium bg-white/[0.03] hover:bg-white/[0.08] text-gray-300 hover:text-white border border-white/5 transition-all text-center"
              >
                Last 3 Years
              </button>
              <button
                type="button"
                onClick={() => handleApplyPreset('ytd')}
                className="px-3 py-2 rounded-xl text-xs font-medium bg-white/[0.03] hover:bg-white/[0.08] text-gray-300 hover:text-white border border-white/5 transition-all text-center"
              >
                Year-to-Date
              </button>
            </div>
          </div>

          {/* Date Pickers (Start & End) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Start Period */}
            <div className="p-4 rounded-xl bg-black/25 border border-white/5 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-indigo-400">
                <Calendar className="w-3.5 h-3.5" />
                Start Period (From)
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-gray-400 uppercase">Month</label>
                  <select
                    value={startMonth}
                    onChange={(e) => setStartMonth(e.target.value)}
                    className="w-full mt-1 px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {MONTH_NAMES.map((m) => (
                      <option key={m.value} value={m.value} className="bg-[#0E131F]">
                        {m.label} ({m.value})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-gray-400 uppercase">Year</label>
                  <select
                    value={startYear}
                    onChange={(e) => setStartYear(e.target.value)}
                    className="w-full mt-1 px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {years.map((y) => (
                      <option key={y} value={y} className="bg-[#0E131F]">
                        {y}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* End Period */}
            <div className="p-4 rounded-xl bg-black/25 border border-white/5 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-400">
                <Calendar className="w-3.5 h-3.5" />
                End Period (To)
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-gray-400 uppercase">Month</label>
                  <select
                    value={endMonth}
                    onChange={(e) => setEndMonth(e.target.value)}
                    className="w-full mt-1 px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {MONTH_NAMES.map((m) => (
                      <option key={m.value} value={m.value} className="bg-[#0E131F]">
                        {m.label} ({m.value})
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-gray-400 uppercase">Year</label>
                  <select
                    value={endYear}
                    onChange={(e) => setEndYear(e.target.value)}
                    className="w-full mt-1 px-2.5 py-1.5 rounded-lg bg-black/40 border border-white/10 text-xs text-white focus:outline-none focus:border-indigo-500"
                  >
                    {years.map((y) => (
                      <option key={y} value={y} className="bg-[#0E131F]">
                        {y}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          </div>

          {/* Range Summary & Idempotency Badge */}
          <div className="p-4 rounded-xl bg-indigo-950/20 border border-indigo-500/20 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-300 font-medium">Selected Period Range:</span>
              <span className="font-bold text-white font-mono">
                {startFormatted} → {endFormatted}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs text-indigo-300">
              <span>Span:</span>
              <span className="font-semibold">
                {monthsCount > 0 ? `${monthsCount} monthly disclosures` : 'Invalid Range'}
              </span>
            </div>
            <div className="pt-2 border-t border-indigo-500/10 flex items-start gap-2 text-[11px] text-indigo-400/90">
              <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />
              <span>
                Existing monthly disclosures are preserved. The pipeline skips already-processed
                months to run in seconds.
              </span>
            </div>
          </div>

          {/* Dry Run Toggle */}
          <label className="flex items-center gap-3 p-3 rounded-xl bg-white/[0.02] border border-white/5 cursor-pointer hover:bg-white/[0.04] transition-colors">
            <input
              type="checkbox"
              checked={dryRun}
              onChange={(e) => setDryRun(e.target.checked)}
              className="w-4 h-4 rounded border-gray-600 text-indigo-600 focus:ring-indigo-500 bg-black/40"
            />
            <div className="text-xs">
              <span className="font-medium text-gray-200">Dry Run Simulation</span>
              <p className="text-gray-500 text-[11px]">
                Test extraction without saving snapshots or committing data
              </p>
            </div>
          </label>

          {/* Validation Error Message */}
          {validationError && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-start gap-2 text-xs text-rose-300">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5 text-rose-400" />
              <span>{validationError}</span>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-white/5 bg-black/20 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-white hover:bg-white/5 border border-white/10 transition-all"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={submitting || monthsCount <= 0}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Dispatching Backfill...
              </>
            ) : (
              <>
                <CloudDownload className="w-3.5 h-3.5" />
                Fetch Portfolio History
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

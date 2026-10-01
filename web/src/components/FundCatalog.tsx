'use client';

import { useState, useMemo } from 'react';
import Link from 'next/link';
import { FundSummary } from '@/types';
import {
  Search,
  ArrowRight,
  TrendingUp,
  PieChart,
  Calendar,
  Building2,
  CheckCircle2,
  ArrowUpRight,
  Activity,
  CloudDownload,
} from 'lucide-react';
import BackfillModal from './BackfillModal';
import Toast, { ToastVariant } from './Toast';

interface FundCatalogProps {
  funds: FundSummary[];
  lastUpdated: string;
}

export default function FundCatalog({ funds, lastUpdated }: FundCatalogProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedAmc, setSelectedAmc] = useState<string>('All');
  const [backfillModalOpen, setBackfillModalOpen] = useState(false);
  const [backfillFundId, setBackfillFundId] = useState('all');
  const [toast, setToast] = useState<{
    message: string;
    variant: ToastVariant;
    action?: { label: string; href: string };
  } | null>(null);

  const schemeOptions = useMemo(() => {
    return funds.map((f) => ({ id: f.id, name: f.name, amc: f.amc }));
  }, [funds]);

  const handleOpenBackfill = (id = 'all') => {
    setBackfillFundId(id);
    setBackfillModalOpen(true);
  };

  const handleBackfillSuccess = (msg: string, runUrl?: string) => {
    setToast({
      message: msg,
      variant: 'success',
      action: runUrl ? { label: 'Track in GitHub Actions ↗', href: runUrl } : undefined,
    });
  };

  const handleBackfillError = (err: string) => {
    setToast({
      message: err,
      variant: 'error',
    });
  };

  const amcs = useMemo(() => {
    const list = Array.from(new Set(funds.map((f) => f.amc)));
    return ['All', ...list];
  }, [funds]);

  const filteredFunds = useMemo(() => {
    return funds.filter((fund) => {
      const matchesSearch =
        fund.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        fund.amc.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (fund.top_holding?.name.toLowerCase() || '').includes(searchTerm.toLowerCase());

      const matchesAmc = selectedAmc === 'All' || fund.amc === selectedAmc;

      return matchesSearch && matchesAmc;
    });
  }, [funds, searchTerm, selectedAmc]);

  const latestMonth = funds[0]?.latest_month || 'N/A';
  const totalTracked = funds.length;
  const topExposure = funds[0]?.top10_total_pct || 0;

  return (
    <div className="space-y-8">
      {/* Hero / Overview Metrics Banner */}
      <div className="relative overflow-hidden rounded-2xl p-6 sm:p-8 glass-panel border border-white/10 shadow-2xl">
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-400">
            <Activity className="w-3.5 h-3.5" />
            Active Portfolio Surveillance
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
            Institutional Equity Insights, <br />
            <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-indigo-400 bg-clip-text text-transparent">
              Zero-Latency Diff Tracking
            </span>
          </h1>
          <p className="text-sm sm:text-base text-gray-300 max-w-2xl leading-relaxed">
            Automated monthly surveillance of mutual fund factsheets and portfolio disclosures.
            Detect top-10 equity entries, exits, weight expansions, and sector allocations.
          </p>
        </div>

        {/* Highlight Stats Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-8 pt-6 border-t border-white/5">
          <div className="space-y-1">
            <span className="text-xs font-medium text-gray-400">Tracked Funds</span>
            <div className="text-2xl font-bold text-white">{totalTracked} Scheme</div>
          </div>
          <div className="space-y-1">
            <span className="text-xs font-medium text-gray-400">Latest Processed</span>
            <div className="text-2xl font-bold text-emerald-400">{latestMonth}</div>
          </div>
          <div className="space-y-1">
            <span className="text-xs font-medium text-gray-400">Top-10 Weight</span>
            <div className="text-2xl font-bold text-indigo-300">{topExposure}%</div>
          </div>
          <div className="space-y-1">
            <span className="text-xs font-medium text-gray-400">Pipeline Cadence</span>
            <div className="text-2xl font-bold text-teal-300">2x Daily Cron</div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
        <div className="flex flex-col sm:flex-row items-center gap-3 flex-1">
          <div className="relative w-full sm:w-80">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search by fund, AMC, or stock..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
            />
          </div>

          {/* AMC Filter Pills */}
          <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
            {amcs.map((amc) => (
              <button
                key={amc}
                onClick={() => setSelectedAmc(amc)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-all ${
                  selectedAmc === amc
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                    : 'bg-white/[0.03] text-gray-400 hover:text-white hover:bg-white/[0.06] border border-white/5'
                }`}
              >
                {amc}
              </button>
            ))}
          </div>
        </div>

        {/* Global Backfill Action */}
        <button
          type="button"
          onClick={() => handleOpenBackfill('all')}
          className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold bg-white/[0.05] hover:bg-white/[0.09] text-white border border-white/10 hover:border-indigo-500/30 transition-all shadow-sm shrink-0"
        >
          <CloudDownload className="w-4 h-4 text-indigo-400" />
          Fetch Historical Data
        </button>
      </div>

      {/* Fund Cards Grid */}
      {filteredFunds.length === 0 ? (
        <div className="text-center py-16 glass-panel rounded-2xl border border-white/5">
          <p className="text-gray-400 text-sm">No funds found matching your search criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredFunds.map((fund) => {
            const hasEnteredExited = fund.latest_changes_count > 0;
            const diffSummary = fund.latest_diff_summary;

            return (
              <div
                key={fund.id}
                className="glass-card rounded-2xl p-6 flex flex-col justify-between group relative overflow-hidden"
              >
                {/* Subtle top card glow */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500/40 via-emerald-400/40 to-transparent" />

                <div className="space-y-4">
                  {/* AMC and Category header */}
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.05] text-gray-300 font-medium border border-white/5">
                      <Building2 className="w-3 h-3 text-indigo-400" />
                      {fund.amc}
                    </span>
                    <span className="text-gray-400 font-mono text-[11px]">
                      {fund.latest_month}
                    </span>
                  </div>

                  {/* Fund Name */}
                  <div>
                    <h2 className="text-xl font-bold text-white group-hover:text-indigo-300 transition-colors">
                      {fund.name}
                    </h2>
                    <p className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                      <Calendar className="w-3 h-3" />
                      As of {fund.latest_as_of}
                    </p>
                  </div>

                  {/* Metrics preview */}
                  <div className="p-3.5 rounded-xl bg-black/25 border border-white/5 space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-gray-400">Top-10 Concentration:</span>
                      <span className="font-semibold text-white">{fund.top10_total_pct}%</span>
                    </div>

                    {fund.top_holding && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-gray-400">Top Position:</span>
                        <span className="font-medium text-emerald-400 truncate max-w-[170px]" title={fund.top_holding.name}>
                          {fund.top_holding.name} ({fund.top_holding.weight_pct}%)
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Latest Movement Highlight */}
                  <div className="text-xs">
                    {hasEnteredExited ? (
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-400 font-medium">
                        <Activity className="w-3 h-3" />
                        {fund.latest_changes_count} Changes in Top 10
                      </div>
                    ) : diffSummary ? (
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium">
                        <CheckCircle2 className="w-3 h-3" />
                        Stable Top 10 ({diffSummary.num_increased} up, {diffSummary.num_decreased} down)
                      </div>
                    ) : (
                      <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/5 text-gray-400">
                        {fund.months_available.length} months history available
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Action footer */}
                <div className="pt-5 mt-6 border-t border-white/5 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => handleOpenBackfill(fund.id)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/5 hover:border-indigo-500/30 transition-all"
                    title={`Fetch past portfolio disclosures for ${fund.name}`}
                  >
                    <CloudDownload className="w-3.5 h-3.5 text-indigo-400" />
                    Fetch Data
                  </button>
                  <Link
                    href={`/fund/${fund.id}`}
                    className="inline-flex items-center gap-1 text-xs font-semibold text-indigo-400 hover:text-indigo-300 group-hover:translate-x-0.5 transition-all"
                  >
                    View Holdings
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Backfill Modal */}
      <BackfillModal
        isOpen={backfillModalOpen}
        onClose={() => setBackfillModalOpen(false)}
        funds={schemeOptions}
        initialFundId={backfillFundId}
        onSuccess={handleBackfillSuccess}
        onError={handleBackfillError}
      />

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 animate-in slide-in-from-bottom-5 duration-200">
          <Toast
            message={toast.message}
            variant={toast.variant}
            onClose={() => setToast(null)}
          />
          {toast.action && (
            <div className="mt-2 text-right">
              <a
                href={toast.action.href}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-indigo-400 hover:text-indigo-300 underline"
              >
                {toast.action.label}
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

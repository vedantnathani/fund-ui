'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  Plus, Settings2, CheckCircle2, XCircle, Building2,
  ExternalLink, ToggleLeft, ToggleRight, Loader2,
  Lock, Unlock, Eye
} from 'lucide-react';
import { FundConfig } from '@/types';
import { addFund, disableFund, enableFund, verifyAdminPasscode } from '@/lib/github';
import Toast, { ToastVariant } from './Toast';

interface FundManagerProps {
  initialFunds: FundConfig[];
}

type ParserOption = 'excel' | 'pdf_text' | 'ocr';
type FundType = 'equity' | 'debt' | 'hybrid' | 'liquid';

const PARSER_LABELS: Record<ParserOption, string> = {
  excel: 'Excel (XLS/XLSX)',
  pdf_text: 'PDF Text',
  ocr: 'OCR (scanned PDFs)',
};

const DEFAULT_FORM: Omit<FundConfig, 'enabled'> = {
  id: '',
  name: '',
  amc: '',
  type: 'equity',
  category: '',
  source_page: '',
  excel_sheet: '',
  pdf_section_keyword: '',
  parser_preference: ['excel'],
  significant_change_pp: 0.5,
};

// ---- Validation helpers ----
function validateForm(f: typeof DEFAULT_FORM): Record<string, string> {
  const errs: Record<string, string> = {};
  if (!f.id) errs.id = 'Required';
  else if (!/^[a-z0-9-]+$/.test(f.id)) errs.id = 'Lowercase kebab-case only (e.g. mirae-flexicap)';
  if (!f.name.trim()) errs.name = 'Required';
  if (!f.amc.trim()) errs.amc = 'Required';
  if (!f.source_page.startsWith('https://')) errs.source_page = 'Must be a valid HTTPS URL';
  if (f.parser_preference.length === 0) errs.parser_preference = 'Select at least one parser';
  if (f.significant_change_pp < 0.1 || f.significant_change_pp > 5.0)
    errs.significant_change_pp = 'Must be between 0.1 and 5.0';
  return errs;
}

// ---- Admin Lock Prompt ----
function AdminLockPrompt({ onUnlock }: { onUnlock: (passcode: string) => void }) {
  const [passcode, setPasscode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!passcode.trim()) return;
    setLoading(true);
    setError(null);
    const valid = await verifyAdminPasscode(passcode.trim());
    setLoading(false);
    if (valid) {
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('admin_passcode', passcode.trim());
      }
      onUnlock(passcode.trim());
    } else {
      setError('Incorrect administrator passcode');
    }
  };

  return (
    <div className="max-w-md mx-auto my-12 glass-panel rounded-2xl p-8 border border-white/10 shadow-2xl text-center space-y-6">
      <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
        <Lock className="w-6 h-6" />
      </div>
      <div>
        <h2 className="text-xl font-bold text-white">Administrator Access</h2>
        <p className="text-xs text-gray-400 mt-1">
          Enter administrator passcode to configure scheme tracking and pipeline settings.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 text-left">
        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1.5">
            Admin Passcode
          </label>
          <input
            type="password"
            value={passcode}
            onChange={(e) => setPasscode(e.target.value)}
            placeholder="••••••••••••"
            className="w-full px-3.5 py-2.5 rounded-xl bg-black/40 border border-white/10 text-sm text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
            autoFocus
          />
          {error && <p className="text-xs text-rose-400 mt-1.5">{error}</p>}
        </div>

        <button
          type="submit"
          disabled={loading || !passcode}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Unlock className="w-4 h-4" />}
          {loading ? 'Verifying...' : 'Unlock Management'}
        </button>
      </form>
    </div>
  );
}

// ---- Fund Row ----
function FundRow({
  fund,
  onToggle,
  toggling,
}: {
  fund: FundConfig;
  onToggle: (id: string, enable: boolean) => void;
  toggling: string | null;
}) {
  const isToggling = toggling === fund.id;
  return (
    <div className={`glass-card rounded-2xl p-5 flex flex-col sm:flex-row sm:items-center gap-4 transition-opacity ${!fund.enabled ? 'opacity-60' : ''}`}>
      <div className="flex-1 min-w-0 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-white truncate">{fund.name}</h3>
          <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full ${
            fund.enabled
              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/25'
              : 'bg-gray-700/40 text-gray-400 border border-gray-600/30'
          }`}>
            {fund.enabled
              ? <><CheckCircle2 className="w-2.5 h-2.5" /> Active</>
              : <><XCircle className="w-2.5 h-2.5" /> Disabled</>
            }
          </span>
          <span className="inline-flex items-center text-[10px] font-medium px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            {fund.type}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-gray-400 flex-wrap">
          <Building2 className="w-3 h-3" />
          <span>{fund.amc}</span>
          {fund.category && <><span>·</span><span>{fund.category}</span></>}
          <span>·</span>
          <span className="font-mono text-gray-500">{fund.id}</span>
        </div>
        <div className="flex items-center gap-2 text-[11px] text-gray-500 flex-wrap">
          <span>Parsers: {fund.parser_preference.join(', ')}</span>
          <span>·</span>
          <span>Δ threshold: {fund.significant_change_pp}pp</span>
          <a href={fund.source_page} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300">
            Source <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
      <button
        onClick={() => onToggle(fund.id, !fund.enabled)}
        disabled={isToggling}
        className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all border ${
          fund.enabled
            ? 'border-rose-500/30 bg-rose-500/10 text-rose-400 hover:bg-rose-500/20'
            : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20'
        } disabled:opacity-50`}
      >
        {isToggling ? (
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
        ) : fund.enabled ? (
          <ToggleLeft className="w-4 h-4" />
        ) : (
          <ToggleRight className="w-4 h-4" />
        )}
        {fund.enabled ? 'Disable' : 'Enable'}
      </button>
    </div>
  );
}

// ---- Add Fund Modal ----
function AddFundModal({
  onClose,
  onSuccess,
  existingIds,
}: {
  onClose: () => void;
  onSuccess: (fund: FundConfig) => void;
  existingIds: string[];
}) {
  const [form, setForm] = useState<typeof DEFAULT_FORM>({ ...DEFAULT_FORM });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  const set = (key: keyof typeof DEFAULT_FORM, val: unknown) =>
    setForm((prev) => ({ ...prev, [key]: val }));

  const touch = (key: string) => setTouched((prev) => ({ ...prev, [key]: true }));

  const currentErrors = validateForm(form);
  const hasErrors = Object.keys(currentErrors).length > 0;

  const fieldError = (key: string) => (touched[key] ? currentErrors[key] : undefined);

  const toggleParser = (p: ParserOption) => {
    const cur = form.parser_preference as ParserOption[];
    set('parser_preference', cur.includes(p) ? cur.filter((x) => x !== p) : [...cur, p]);
  };

  const handleSubmit = async () => {
    // Touch all fields
    const allTouched = Object.keys(DEFAULT_FORM).reduce((a, k) => ({ ...a, [k]: true }), {});
    setTouched(allTouched);
    if (hasErrors) return;
    if (existingIds.includes(form.id)) {
      setErrors({ id: `Fund ID '${form.id}' already exists` });
      return;
    }
    setSubmitting(true);
    setSubmitError(null);
    const result = await addFund({ ...form, enabled: true });
    setSubmitting(false);
    if (result.success) {
      onSuccess({ ...form, enabled: true });
    } else {
      setSubmitError(result.error || 'Unknown error');
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4" onClick={onClose}>
      <div
        className="glass-panel rounded-2xl border border-white/10 w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 glass-panel border-b border-white/5 px-6 py-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-white">Add New Fund</h2>
            <p className="text-xs text-gray-400 mt-0.5">This will commit to <code className="bg-black/40 px-1 rounded">config/funds.json</code> and trigger a 12-month backfill.</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-colors">✕</button>
        </div>

        <div className="p-6 space-y-5">
          {submitError && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-950/50 border border-rose-500/30 text-rose-300 text-xs">
              <XCircle className="w-4 h-4 shrink-0" />
              {submitError}
            </div>
          )}

          {/* Row 1: Fund ID + Name */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Fund ID <span className="text-rose-400">*</span></label>
              <input
                value={form.id}
                onChange={(e) => set('id', e.target.value.toLowerCase())}
                onBlur={() => touch('id')}
                placeholder="mirae-emerging-bluechip"
                className={`w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 transition-all font-mono ${fieldError('id') ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : 'border-white/10 focus:border-indigo-500/50 focus:ring-indigo-500/30'}`}
              />
              {fieldError('id') && <p className="text-rose-400 text-[11px] mt-1">{fieldError('id')}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Fund Name <span className="text-rose-400">*</span></label>
              <input
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                onBlur={() => touch('name')}
                placeholder="Mirae Asset Emerging Bluechip Fund"
                className={`w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 transition-all ${fieldError('name') ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : 'border-white/10 focus:border-indigo-500/50 focus:ring-indigo-500/30'}`}
              />
              {fieldError('name') && <p className="text-rose-400 text-[11px] mt-1">{fieldError('name')}</p>}
            </div>
          </div>

          {/* Row 2: AMC + Type + Category */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">AMC <span className="text-rose-400">*</span></label>
              <input
                value={form.amc}
                onChange={(e) => set('amc', e.target.value)}
                onBlur={() => touch('amc')}
                placeholder="Mirae Asset"
                className={`w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 transition-all ${fieldError('amc') ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : 'border-white/10 focus:border-indigo-500/50 focus:ring-indigo-500/30'}`}
              />
              {fieldError('amc') && <p className="text-rose-400 text-[11px] mt-1">{fieldError('amc')}</p>}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Fund Type <span className="text-rose-400">*</span></label>
              <select
                value={form.type}
                onChange={(e) => set('type', e.target.value as FundType)}
                className="w-full px-3 py-2.5 rounded-xl bg-[#0E131F] border border-white/10 text-sm text-white focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all"
              >
                {(['equity', 'debt', 'hybrid', 'liquid'] as FundType[]).map((t) => (
                  <option key={t} value={t}>{t.charAt(0).toUpperCase() + t.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Category <span className="text-gray-500">(optional)</span></label>
              <input
                value={form.category}
                onChange={(e) => set('category', e.target.value)}
                placeholder="Flexi Cap"
                className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all"
              />
            </div>
          </div>

          {/* Row 3: Source Page */}
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">Source Page URL <span className="text-rose-400">*</span></label>
            <input
              value={form.source_page}
              onChange={(e) => set('source_page', e.target.value)}
              onBlur={() => touch('source_page')}
              placeholder="https://www.miraeassetmf.co.in/downloads/factsheets"
              className={`w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-1 transition-all ${fieldError('source_page') ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : 'border-white/10 focus:border-indigo-500/50 focus:ring-indigo-500/30'}`}
            />
            {fieldError('source_page') && <p className="text-rose-400 text-[11px] mt-1">{fieldError('source_page')}</p>}
          </div>

          {/* Row 4: Parser preferences */}
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">Parser Preference <span className="text-rose-400">*</span> <span className="text-gray-500">(select all that apply, in priority order)</span></label>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(PARSER_LABELS) as ParserOption[]).map((p) => {
                const active = (form.parser_preference as ParserOption[]).includes(p);
                return (
                  <button
                    key={p}
                    type="button"
                    onClick={() => toggleParser(p)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                      active
                        ? 'bg-indigo-600/30 border-indigo-500/50 text-indigo-300'
                        : 'bg-white/[0.03] border-white/10 text-gray-400 hover:text-white hover:bg-white/[0.06]'
                    }`}
                  >
                    {PARSER_LABELS[p]}
                  </button>
                );
              })}
            </div>
            {fieldError('parser_preference') && <p className="text-rose-400 text-[11px] mt-1">{fieldError('parser_preference')}</p>}
          </div>

          {/* Row 5: Optional parser hints + threshold */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Excel Sheet Name <span className="text-gray-500">(optional)</span></label>
              <input
                value={form.excel_sheet}
                onChange={(e) => set('excel_sheet', e.target.value)}
                placeholder="PPFCF"
                className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">PDF Section Keyword <span className="text-gray-500">(optional)</span></label>
              <input
                value={form.pdf_section_keyword}
                onChange={(e) => set('pdf_section_keyword', e.target.value)}
                placeholder="Emerging Bluechip"
                className="w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/30 transition-all"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5">Significant Change (pp)</label>
              <input
                type="number"
                min={0.1}
                max={5.0}
                step={0.1}
                value={form.significant_change_pp}
                onChange={(e) => set('significant_change_pp', parseFloat(e.target.value))}
                onBlur={() => touch('significant_change_pp')}
                className={`w-full px-3 py-2.5 rounded-xl bg-white/[0.04] border text-sm text-white focus:outline-none focus:ring-1 transition-all ${fieldError('significant_change_pp') ? 'border-rose-500/60 focus:border-rose-500 focus:ring-rose-500/30' : 'border-white/10 focus:border-indigo-500/50 focus:ring-indigo-500/30'}`}
              />
              {fieldError('significant_change_pp') && <p className="text-rose-400 text-[11px] mt-1">{fieldError('significant_change_pp')}</p>}
            </div>
          </div>

          {/* Live Preview */}
          {(form.id || form.name || form.amc) && (
            <div>
              <button
                type="button"
                onClick={() => setShowPreview(!showPreview)}
                className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                <Eye className="w-3.5 h-3.5" />
                {showPreview ? 'Hide' : 'Show'} card preview
              </button>
              {showPreview && (
                <div className="mt-3 glass-card rounded-2xl p-5 relative overflow-hidden border border-indigo-500/20">
                  <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500/40 via-emerald-400/40 to-transparent" />
                  <div className="flex items-center justify-between text-xs mb-3">
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-white/[0.05] text-gray-300 font-medium border border-white/5">
                      <Building2 className="w-3 h-3 text-indigo-400" />
                      {form.amc || 'AMC Name'}
                    </span>
                    <span className="text-gray-400 font-mono text-[11px]">No data yet</span>
                  </div>
                  <h3 className="text-lg font-bold text-white">{form.name || 'Fund Name'}</h3>
                  <p className="text-xs text-gray-400 mt-1">{form.type} · {form.category || 'Category'}</p>
                  <p className="text-xs text-gray-500 mt-2 font-mono">{form.id || 'fund-id'}</p>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="sticky bottom-0 glass-panel border-t border-white/5 px-6 py-4 flex items-center justify-between gap-3">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-sm text-gray-400 hover:text-white hover:bg-white/5 border border-white/10 transition-all">
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="flex items-center gap-2 px-5 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
            {submitting ? 'Adding...' : 'Add Fund'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---- Main FundManager component ----
export default function FundManager({ initialFunds }: FundManagerProps) {
  const [funds, setFunds] = useState<FundConfig[]>(initialFunds);
  const [showAddModal, setShowAddModal] = useState(false);
  const [toggling, setToggling] = useState<string | null>(null);
  const [toast, setToast] = useState<{ message: string; variant: ToastVariant } | null>(null);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

  useEffect(() => {
    const saved = typeof window !== 'undefined' ? sessionStorage.getItem('admin_passcode') : null;
    if (saved) {
      setIsUnlocked(true);
    }
    setCheckingAuth(false);
  }, []);

  const handleLock = () => {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('admin_passcode');
    }
    setIsUnlocked(false);
  };

  const showToast = useCallback((message: string, variant: ToastVariant) => {
    setToast({ message, variant });
  }, []);

  const handleToggle = async (id: string, enable: boolean) => {
    setToggling(id);
    const result = enable ? await enableFund(id) : await disableFund(id);
    setToggling(null);
    if (result.success) {
      setFunds((prev) => prev.map((f) => (f.id === id ? { ...f, enabled: enable } : f)));
      showToast(`Fund ${enable ? 'enabled' : 'disabled'} successfully`, 'success');
    } else {
      showToast(result.error || 'Action failed', 'error');
    }
  };

  const handleAddSuccess = (newFund: FundConfig) => {
    setFunds((prev) => [...prev, newFund]);
    setShowAddModal(false);
    showToast(`Fund '${newFund.name}' added! Backfill will run automatically.`, 'success');
  };

  const activeFunds = funds.filter((f) => f.enabled);
  const disabledFunds = funds.filter((f) => !f.enabled);

  if (checkingAuth) {
    return (
      <div className="flex items-center justify-center py-20 text-gray-500">
        <Loader2 className="w-6 h-6 animate-spin" />
      </div>
    );
  }

  if (!isUnlocked) {
    return <AdminLockPrompt onUnlock={() => setIsUnlocked(true)} />;
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-xs font-semibold text-indigo-400 mb-3">
            <Settings2 className="w-3.5 h-3.5" />
            Fund Registry Manager
          </div>
          <h1 className="text-3xl font-extrabold text-white">Manage Funds</h1>
          <p className="text-sm text-gray-400 mt-1">
            Add, enable, or disable funds tracked by the automated pipeline.{' '}
            <span className="text-gray-500">{funds.length} total · {activeFunds.length} active</span>
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleLock}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium text-gray-400 hover:text-white hover:bg-white/5 border border-white/10 transition-all"
            title="Lock admin session"
          >
            <Lock className="w-3.5 h-3.5" />
            Lock
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/30 transition-all shrink-0"
          >
            <Plus className="w-4 h-4" />
            Add New Fund
          </button>
        </div>
      </div>

      {/* Active Funds */}
      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
          Active Funds ({activeFunds.length})
        </h2>
        {activeFunds.length === 0 ? (
          <div className="text-center py-12 glass-panel rounded-2xl border border-white/5">
            <p className="text-gray-400 text-sm">No active funds. Add one to get started.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {activeFunds.map((fund) => (
              <FundRow key={fund.id} fund={fund} onToggle={handleToggle} toggling={toggling} />
            ))}
          </div>
        )}
      </section>

      {/* Disabled Funds */}
      {disabledFunds.length > 0 && (
        <section className="space-y-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-500">
            Disabled Funds ({disabledFunds.length})
          </h2>
          <div className="space-y-3">
            {disabledFunds.map((fund) => (
              <FundRow key={fund.id} fund={fund} onToggle={handleToggle} toggling={toggling} />
            ))}
          </div>
        </section>
      )}

      {/* Add Fund Modal */}
      {showAddModal && (
        <AddFundModal
          onClose={() => setShowAddModal(false)}
          onSuccess={handleAddSuccess}
          existingIds={funds.map((f) => f.id)}
        />
      )}

      {/* Toast */}
      {toast && (
        <Toast
          message={toast.message}
          variant={toast.variant}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}

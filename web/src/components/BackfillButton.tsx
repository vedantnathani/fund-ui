'use client';

import { useState } from 'react';
import { CloudDownload, Calendar, ExternalLink } from 'lucide-react';
import BackfillModal from './BackfillModal';
import Toast, { ToastVariant } from './Toast';

interface BackfillButtonProps {
  fundId?: string;
  fundName?: string;
  funds?: Array<{ id: string; name: string; amc?: string }>;
  variant?: 'primary' | 'secondary' | 'compact' | 'card';
  label?: string;
}

export default function BackfillButton({
  fundId = 'all',
  fundName,
  funds = [],
  variant = 'secondary',
  label = 'Fetch Historical Data',
}: BackfillButtonProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    variant: ToastVariant;
    action?: { label: string; href: string };
  } | null>(null);

  // If funds list is not passed, build fallback list with fundId/fundName
  const schemeOptions = funds.length > 0
    ? funds
    : fundId !== 'all'
    ? [{ id: fundId, name: fundName || fundId }]
    : [];

  const handleSuccess = (msg: string, runUrl?: string) => {
    setToast({
      message: msg,
      variant: 'success',
      action: runUrl ? { label: 'Track in GitHub Actions ↗', href: runUrl } : undefined,
    });
  };

  const handleError = (err: string) => {
    setToast({
      message: err,
      variant: 'error',
    });
  };

  return (
    <>
      {variant === 'card' ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-indigo-400 hover:text-white bg-indigo-500/10 hover:bg-indigo-600/20 border border-indigo-500/20 transition-all"
        >
          <CloudDownload className="w-3.5 h-3.5" />
          Fetch Data
        </button>
      ) : variant === 'compact' ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold text-gray-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 transition-all shadow-sm"
        >
          <Calendar className="w-3.5 h-3.5 text-indigo-400" />
          {label}
        </button>
      ) : variant === 'primary' ? (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 text-white shadow-lg shadow-indigo-600/25 border border-indigo-400/30 transition-all"
        >
          <CloudDownload className="w-4 h-4" />
          {label}
        </button>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-medium text-gray-300 hover:text-white bg-white/[0.04] hover:bg-white/[0.08] border border-white/10 transition-all"
        >
          <CloudDownload className="w-3.5 h-3.5 text-indigo-400" />
          {label}
        </button>
      )}

      {/* Backfill Modal */}
      <BackfillModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        funds={schemeOptions}
        initialFundId={fundId}
        onSuccess={handleSuccess}
        onError={handleError}
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
    </>
  );
}

'use client';

import { useEffect } from 'react';
import { CheckCircle2, XCircle, Info, X } from 'lucide-react';

export type ToastVariant = 'success' | 'error' | 'info';

interface ToastProps {
  message: string;
  variant: ToastVariant;
  onClose: () => void;
}

const VARIANT_STYLES: Record<ToastVariant, { bg: string; border: string; icon: React.ReactNode }> = {
  success: {
    bg: 'bg-emerald-950/90',
    border: 'border-emerald-500/40',
    icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />,
  },
  error: {
    bg: 'bg-rose-950/90',
    border: 'border-rose-500/40',
    icon: <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />,
  },
  info: {
    bg: 'bg-indigo-950/90',
    border: 'border-indigo-500/40',
    icon: <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />,
  },
};

export default function Toast({ message, variant, onClose }: ToastProps) {
  const styles = VARIANT_STYLES[variant];

  useEffect(() => {
    const timer = setTimeout(onClose, 4000);
    return () => clearTimeout(timer);
  }, [onClose]);

  return (
    <div
      className={`
        fixed top-5 right-5 z-[100] max-w-sm w-full
        flex items-start gap-3 px-4 py-3 rounded-xl
        ${styles.bg} ${styles.border} border
        backdrop-blur-md shadow-2xl
        animate-in slide-in-from-top-2 fade-in duration-200
      `}
      role="alert"
    >
      {styles.icon}
      <p className="text-sm text-gray-100 flex-1 leading-relaxed">{message}</p>
      <button
        onClick={onClose}
        className="text-gray-400 hover:text-white transition-colors shrink-0"
        aria-label="Close notification"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

'use client';

import Link from 'next/link';
import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface MonthSelectorProps {
  fundId: string;
  currentMonth: string;
  availableMonths: string[];
}

const INITIAL_VISIBLE = 6; // always show the N most-recent months before collapsing

export default function MonthSelector({ fundId, currentMonth, availableMonths }: MonthSelectorProps) {
  const [expanded, setExpanded] = useState(false);

  const needsCollapse = availableMonths.length > INITIAL_VISIBLE;
  const visibleMonths = expanded || !needsCollapse
    ? availableMonths
    : availableMonths.slice(0, INITIAL_VISIBLE);

  const hiddenCount = availableMonths.length - INITIAL_VISIBLE;

  return (
    <div className="space-y-2">
      {/* Pills row — wraps so many months display cleanly */}
      <div className="flex flex-wrap items-center gap-2">
        {visibleMonths.map((m) => {
          const isActive = m === currentMonth;
          return (
            <Link
              key={m}
              href={`/fund/${fundId}?month=${m}`}
              className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-lg shadow-indigo-500/25 border border-indigo-400/30'
                  : 'bg-white/[0.04] text-gray-400 hover:text-white hover:bg-white/[0.08] border border-white/5'
              }`}
            >
              {m}
            </Link>
          );
        })}

        {/* Expand / Collapse toggle */}
        {needsCollapse && (
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 px-3 py-1.5 rounded-xl text-xs font-medium text-gray-400 hover:text-white bg-white/[0.03] hover:bg-white/[0.07] border border-white/5 transition-all"
          >
            {expanded ? (
              <>
                <ChevronUp className="w-3 h-3" />
                Show less
              </>
            ) : (
              <>
                <ChevronDown className="w-3 h-3" />
                +{hiddenCount} more
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
}

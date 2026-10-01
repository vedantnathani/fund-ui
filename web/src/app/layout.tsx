import type { Metadata, Viewport } from 'next';
import './globals.css';
import Link from 'next/link';
import { Activity, ShieldCheck, Layers } from 'lucide-react';

export const viewport: Viewport = {
  themeColor: '#0B0F17',
  colorScheme: 'dark',
  width: 'device-width',
  initialScale: 1,
};

export const metadata: Metadata = {
  metadataBase: new URL('https://fund-ui.vercel.app'),
  title: {
    default: 'FundLens — Mutual Fund Top-10 Holdings Tracker',
    template: '%s | FundLens',
  },
  description:
    'Automated monthly surveillance of Indian mutual fund factsheets & portfolio disclosures. Track top-10 equity holdings, detect month-over-month weight shifts, and inspect verified AI commentary.',
  keywords: [
    'mutual funds',
    'portfolio tracker',
    'top 10 holdings',
    'PPFAS',
    'equity disclosures',
    'factsheet parser',
    'financial analytics',
    'Indian mutual funds',
  ],
  authors: [{ name: 'Vedant Nathani' }],
  creator: 'Vedant Nathani',
  openGraph: {
    title: 'FundLens — Mutual Fund Top-10 Holdings Tracker',
    description:
      'Automated surveillance of Indian mutual fund factsheets & portfolio disclosures. Track top-10 holdings and MoM shifts.',
    url: 'https://fund-ui.vercel.app',
    siteName: 'FundLens',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'FundLens — Mutual Fund Top-10 Holdings Tracker',
    description:
      'Automated surveillance of Indian mutual fund factsheets & portfolio disclosures.',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0B0F17] text-gray-100 min-h-screen flex flex-col selection:bg-indigo-500/30 selection:text-indigo-200">
        {/* Subtle background ambient gradients */}
        <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
          <div className="absolute top-[-10%] left-[-10%] w-[45vw] h-[45vw] rounded-full bg-indigo-600/10 blur-[130px]" />
          <div className="absolute top-[20%] right-[-10%] w-[40vw] h-[40vw] rounded-full bg-emerald-600/8 blur-[140px]" />
          <div className="absolute bottom-[-10%] left-[20%] w-[35vw] h-[35vw] rounded-full bg-blue-600/8 blur-[120px]" />
        </div>

        {/* Global Navigation Header */}
        <header className="sticky top-0 z-50 glass-panel border-b border-white/5">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <Link href="/" className="flex items-center gap-3 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-emerald-400 p-[1px] shadow-lg shadow-indigo-500/20 group-hover:shadow-indigo-500/35 transition-all">
                <div className="w-full h-full bg-[#0E131F] rounded-[11px] flex items-center justify-center">
                  <Layers className="w-4 h-4 text-emerald-400" />
                </div>
              </div>
              <div>
                <span className="font-semibold tracking-tight text-white group-hover:text-indigo-300 transition-colors">
                  FundLens
                </span>
                <span className="hidden sm:inline-block ml-2 text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                  Top-10 Tracker
                </span>
              </div>
            </Link>

            <div className="flex items-center gap-3 sm:gap-4">
              <div className="hidden sm:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs font-medium text-emerald-400">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Automated Pipeline Active
              </div>

              <a
                href="https://www.linkedin.com/in/vedant-nathani"
                target="_blank"
                rel="noreferrer"
                className="p-2 text-gray-400 hover:text-[#0A66C2] hover:bg-white/5 rounded-lg transition-colors"
                title="Connect on LinkedIn"
              >
                <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
                  <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" />
                </svg>
              </a>
            </div>
          </div>
        </header>

        {/* Main Page Body */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>

        {/* Regulatory Footer & Disclaimer */}
        <footer className="glass-panel border-t border-white/5 mt-auto">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-gray-400 border-b border-white/5 pb-6">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-indigo-400 shrink-0" />
                <span className="font-medium text-gray-300">Regulatory Disclaimer:</span>
                <span>
                  Informational only. Not investment advice. Data derived from official AMC monthly factsheets & portfolio disclosures; verify directly against the AMC source before investing.
                </span>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-2 pt-4 text-xs text-gray-500">
              <p>© {new Date().getFullYear()} FundLens — 100% Free Mutual Fund Analytics Stack</p>
              <div className="flex items-center gap-4">
                <span>Free Next.js + GitHub Actions Architecture</span>
                <span>•</span>
                <Link href="/manage" className="hover:text-gray-400 transition-colors">
                  Admin
                </Link>
              </div>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

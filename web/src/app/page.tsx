import { getFundIndex } from '@/lib/data';
import FundCatalog from '@/components/FundCatalog';

export default async function HomePage() {
  const index = await getFundIndex();

  if (!index || !index.funds || index.funds.length === 0) {
    return (
      <div className="py-20 text-center space-y-4">
        <h1 className="text-2xl font-bold text-white">No Fund Data Found</h1>
        <p className="text-gray-400 max-w-md mx-auto text-sm">
          Run the pipeline or backfill script to populate initial mutual fund snapshots.
        </p>
        <code className="inline-block p-3 rounded-xl bg-black/40 border border-white/10 text-xs font-mono text-emerald-400">
          python3 pipeline/backfill.py --fixtures-only
        </code>
      </div>
    );
  }

  return <FundCatalog funds={index.funds} lastUpdated={index.last_updated} />;
}

import fs from 'fs';
import path from 'path';
import { Diff, FundConfig, FundIndex, HistoryDataPoint, Snapshot } from '@/types';

// Statically scope data directory to public/data (mirrored by prebuild) or ../data
function getDataDir(): string {
  const publicData = path.join(process.cwd(), 'public', 'data');
  if (fs.existsSync(publicData)) {
    return publicData;
  }
  const rootData = path.join(process.cwd(), '..', 'data');
  if (fs.existsSync(rootData)) {
    return rootData;
  }
  return publicData;
}

export async function getFundIndex(): Promise<FundIndex | null> {
  const dataDir = getDataDir();
  const indexPath = path.join(dataDir, 'index.json');

  if (!fs.existsSync(indexPath)) {
    return null;
  }

  try {
    const raw = fs.readFileSync(indexPath, 'utf-8');
    return JSON.parse(raw) as FundIndex;
  } catch (error) {
    console.error('Error reading index.json:', error);
    return null;
  }
}

export async function getFundSnapshot(fundId: string, month: string): Promise<Snapshot | null> {
  const dataDir = getDataDir();
  const snapPath = path.join(dataDir, fundId, `${month}.json`);

  if (!fs.existsSync(snapPath)) {
    return null;
  }

  try {
    const raw = fs.readFileSync(snapPath, 'utf-8');
    return JSON.parse(raw) as Snapshot;
  } catch (error) {
    console.error(`Error reading snapshot for ${fundId} (${month}):`, error);
    return null;
  }
}

export async function getFundDiff(fundId: string, month: string): Promise<Diff | null> {
  const dataDir = getDataDir();
  const diffPath = path.join(dataDir, fundId, `${month}.diff.json`);

  if (!fs.existsSync(diffPath)) {
    return null;
  }

  try {
    const raw = fs.readFileSync(diffPath, 'utf-8');
    return JSON.parse(raw) as Diff;
  } catch (error) {
    console.error(`Error reading diff for ${fundId} (${month}):`, error);
    return null;
  }
}

export async function getFundHistory(fundId: string): Promise<{ data: HistoryDataPoint[]; holdings: string[] }> {
  const dataDir = getDataDir();
  const fundDir = path.join(dataDir, fundId);

  if (!fs.existsSync(fundDir)) {
    return { data: [], holdings: [] };
  }

  try {
    const files = fs
      .readdirSync(fundDir)
      .filter((f) => f.endsWith('.json') && !f.endsWith('.diff.json') && f !== 'index.json')
      .sort(); // Chronological: 2026-06, 2026-07, 2026-08

    const historyPoints: HistoryDataPoint[] = [];
    const allHoldingsSet = new Set<string>();

    for (const file of files) {
      const filePath = path.join(fundDir, file);
      const raw = fs.readFileSync(filePath, 'utf-8');
      const snap: Snapshot = JSON.parse(raw);
      const month = file.replace('.json', '');

      const point: HistoryDataPoint = {
        month,
        as_of: snap.as_of,
      };

      for (const h of snap.holdings) {
        point[h.name] = h.weight_pct;
        allHoldingsSet.add(h.name);
      }

      historyPoints.push(point);
    }

    // Sort holdings by latest month weight descending
    const latestPoint = historyPoints[historyPoints.length - 1] || {};
    const sortedHoldings = Array.from(allHoldingsSet).sort((a, b) => {
      const wa = Number(latestPoint[a]) || 0;
      const wb = Number(latestPoint[b]) || 0;
      return wb - wa;
    });

    return {
      data: historyPoints,
      holdings: sortedHoldings.slice(0, 10), // Top 10 latest
    };
  } catch (error) {
    console.error(`Error reading history for ${fundId}:`, error);
    return { data: [], holdings: [] };
  }
}

export async function getFundsConfig(): Promise<FundConfig[]> {
  // Try repo root config (works in dev and local build)
  const rootConfig = path.join(process.cwd(), '..', 'config', 'funds.json');
  // Fallback to public/funds.json (Vercel — copied by prebuild)
  const publicConfig = path.join(process.cwd(), 'public', 'funds.json');

  const configPath = fs.existsSync(rootConfig)
    ? rootConfig
    : fs.existsSync(publicConfig)
      ? publicConfig
      : null;

  if (!configPath) {
    console.warn('funds.json not found at root or public/funds.json');
    return [];
  }

  try {
    const raw = fs.readFileSync(configPath, 'utf-8');
    return JSON.parse(raw) as FundConfig[];
  } catch (error) {
    console.error('Error reading funds config:', error);
    return [];
  }
}

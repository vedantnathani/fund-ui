import type { Metadata } from 'next';
import { getFundsConfig } from '@/lib/data';
import FundManager from '@/components/FundManager';

export const metadata: Metadata = {
  title: 'Manage Funds — FundLens',
  description: 'Add, enable, or disable mutual funds tracked by the automated FundLens pipeline.',
};

export default async function ManagePage() {
  const funds = await getFundsConfig();

  return <FundManager initialFunds={funds} />;
}

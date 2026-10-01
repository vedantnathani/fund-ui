export interface FundConfig {
  id: string;
  name: string;
  amc: string;
  type: 'equity' | 'debt' | 'hybrid' | 'liquid';
  category?: string;
  source_page: string;
  excel_sheet?: string;
  pdf_section_keyword?: string;
  parser_preference: string[];
  significant_change_pp: number;
  enabled: boolean;
}

export interface Holding {
  rank: number;
  key: string;
  name: string;
  isin?: string | null;
  sector: string;
  weight_pct: number;
}

export interface Snapshot {
  fund_id: string;
  as_of: string;
  source_url?: string;
  source_type?: string;
  file_sha256?: string;
  top10_total_pct: number;
  amc_commentary?: string | null;
  holdings: Holding[];
}

export interface DiffHolding {
  key: string;
  name: string;
  isin?: string | null;
  sector: string;
  rank: number;
  prev_rank?: number;
  rank_change?: number;
  weight_pct: number;
  prev_weight_pct?: number;
  weight_delta_pp?: number;
  direction?: 'increased' | 'decreased' | 'unchanged';
  significant?: boolean;
}

export interface MoverInfo {
  name: string;
  weight_delta_pp: number;
}

export interface DiffSummary {
  num_entered: number;
  num_exited: number;
  num_increased: number;
  num_decreased: number;
  num_unchanged: number;
  num_significant: number;
  biggest_increase?: MoverInfo | null;
  biggest_decrease?: MoverInfo | null;
}

export interface AISummary {
  text: string;
  provider: string;
  verified: boolean;
  generated_at: string;
}

export interface Diff {
  fund_id: string;
  current_month: string;
  previous_month: string;
  as_of: string;
  prev_as_of: string;
  top10_total_pct: number;
  prev_top10_total_pct: number;
  top10_total_delta_pp: number;
  entered_top10: DiffHolding[];
  exited_top10: DiffHolding[];
  retained: DiffHolding[];
  summary: DiffSummary;
  amc_commentary?: string | null;
  ai_summary?: AISummary | null;
}

export interface FundSummary {
  id: string;
  name: string;
  amc: string;
  category: string;
  type: string;
  latest_month: string;
  latest_as_of: string;
  top10_total_pct: number;
  top_holding?: {
    name: string;
    weight_pct: number;
  } | null;
  months_available: string[];
  latest_changes_count: number;
  latest_diff_summary?: DiffSummary | null;
}

export interface FundIndex {
  last_updated: string;
  total_funds: number;
  funds: FundSummary[];
}

export interface HistoryDataPoint {
  month: string;
  as_of: string;
  [companyName: string]: string | number;
}

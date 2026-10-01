# STATE: Mutual Fund Top-10 Holdings Tracker

## Current State
Milestone v1.1 (Fund Manager UI & Production Deployment) — **PHASE 13 PLANNED** 🏗️

## Next Action
Run `/gsd-execute-phase 13` to execute Phase 13 (Vercel Production Deployment & Documentation).

## Active Milestone: v1.1
| Phase | Name | Status |
|-------|------|--------|
| 9 | Backfill CLI Enhancements | ✅ Completed (commit 51fd906) |
| 10 | GitHub Actions: Backfill & Register-Fund Workflows | ✅ Completed (commit d4abdeb) |
| 11 | Fund Manager UI (Add / Edit / Remove Funds) | ✅ Completed (commit 79fb307) |
| 12 | Backfill Period Picker UI | ✅ Completed (commit 58d5725) |
| 13 | Vercel Production Deployment | 🟡 Planned (ready to execute) |

## Decisions Log
| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | Excel parser is primary for PPFAS | Portfolio Disclosure XLS has structured data with ISIN, more reliable than PDF table extraction | 2026-10-02 |
| 2 | No JavaScript/Playwright needed for PPFAS | Page is server-rendered HTML, all links available via plain HTTP | 2026-10-02 |
| 3 | OpenRouter as default LLM provider | User preference; pluggable via env var | 2026-10-02 |
| 4 | Dark mode + glassmorphism dashboard | User preference for visual direction | 2026-10-02 |
| 5 | Twice-daily cron (6 AM + 6 PM IST) | User preference for schedule frequency | 2026-10-02 |
| 6 | Single combined factsheet per month at PPFAS | All funds in one PDF; parser must filter by section_keyword | 2026-10-02 |
| 7 | PPFAS Excel uses OpenXML container | Despite `.xls` extension, openpyxl engine works; implement auto-fallback to xlrd | 2026-10-02 |
| 8 | Multi-section equity extraction | Foreign equities (Alphabet, Microsoft, etc.) reside in a separate sub-table; parser must aggregate domestic + foreign | 2026-10-02 |
| 9 | Dynamic PDF page discovery | Factsheet page positions vary across months; scan scheme + table headers dynamically | 2026-10-02 |
| 10 | Deterministic canonical key diffing | Match holdings by ISIN/canonical slug to prevent renames from creating spurious enter/exit churn | 2026-10-02 |
| 11 | Neutral portfolio wording | Use "weight increased/decreased" and "entered/exited top 10" rather than speculative trading terms | 2026-10-02 |
| 12 | Dedicated pipeline runner script | `pipeline/run.py` isolates automation logic from GitHub Actions YAML, enabling local testability | 2026-10-02 |
| 13 | Targeted publication window cron | `30 0,12 3-20 * *` (days 3–20, 6 AM & 6 PM IST) aligns with Indian AMC monthly release cycles | 2026-10-02 |
| 14 | Pre-computed JSON data loader | `web/src/lib/data.ts` loads static JSON from filesystem; prebuild script mirrors `data/` for Vercel Hobby zero-config deployment | 2026-10-02 |
| 15 | Strict number verification post-check | Extract every numeric token from LLM text and verify existence in diff JSON within ±0.05pp tolerance | 2026-10-02 |
| 16 | Deterministic template fallback | Pure Python fallback guarantee ensuring pipeline never crashes on API failure or quota exhaustion | 2026-10-02 |
| 17 | GitHub API for fund config updates | UI commits to funds.json via GitHub Contents API; requires GH_PAT stored in Vercel env vars only | 2026-10-02 |
| 18 | workflow_dispatch for on-demand backfill | UI triggers backfill via GitHub Actions API; avoids needing a server-side compute layer on Vercel | 2026-10-02 |

## Open Questions
_None currently._

## Blockers
_None currently._

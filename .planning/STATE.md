# STATE: Mutual Fund Top-10 Holdings Tracker

## Current Phase
Phase 2 (Scraper + Parser + Validator) — **COMPLETED**

## Next Action
Begin Phase 3: Diff Engine + Snapshots + Backfill

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
| 9 | Dynamic PDF page discovery | Factsheet page positions vary across months (p3 in June/Aug 2026, p7 in July 2026); scan scheme + table headers dynamically | 2026-10-02 |

## Open Questions
_None currently._

## Blockers
_None currently._


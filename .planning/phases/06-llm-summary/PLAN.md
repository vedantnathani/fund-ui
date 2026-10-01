# Phase 6: LLM Summary — Plan

## Goal
Implement a pluggable AI summarization module in `pipeline/summarize.py` that generates natural-language portfolio commentary from month-over-month diffs. Enforces a strict number verification post-check to eliminate hallucinations and guarantees graceful fallback to deterministic templates so the pipeline never breaks even with zero API keys or external outages.

---

## Requirements Addressed
- **FR-7.1**: Pluggable provider via env var (`LLM_PROVIDER`). Default: OpenRouter free models, with support for Google Gemini and Groq.
- **FR-7.2**: Pure diff input: Only the diff JSON and factsheet commentary are passed to the model.
- **FR-7.3**: Constrained system prompt prohibiting outside facts, predictions, or unsolicited investment advice.
- **FR-7.4**: Plain-language output of 3–5 sentences summarizing key moves and concentration changes.
- **FR-7.5**: Post-check number verification: extracts every number from the LLM output and validates it exists in the diff JSON; rejects output if any unverified number appears.
- **FR-7.6**: Deterministic template fallback when API keys are absent, network calls fail, or number verification rejects output.
- **FR-7.7**: Graceful degradation: The pipeline must NEVER fail just because an LLM did.
- **UAT Criteria 5**: Summary contains only verified numbers from diff JSON.
- **UAT Criteria 6**: Fallback template summary generated when LLM fails or is unconfigured.

---

## Architecture & Technical Decisions

1. **Pluggable Architecture**:
   - Provider abstraction (`LLMClient`):
     - `OpenRouterProvider` (uses standard OpenAI-compatible completions API with `https://openrouter.ai/api/v1`)
     - `GeminiProvider` (uses Google Generative AI REST endpoint)
     - `GroqProvider` (uses Groq OpenAI-compatible endpoint)
     - `TemplateFallbackProvider` (pure Python rule-based generator)
   - Auto-detection: selects provider based on `LLM_PROVIDER` and available environment keys (`OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`). If none found, automatically defaults to `template_fallback`.
2. **Strict Hallucination Verification**:
   - Regular expression extracts all numerical tokens from the summary text.
   - Filters out legitimate calendar terms (years `2026`, months `08`, days `31`) and ranks (`1` to `10`).
   - For all financial amounts and deltas (e.g. `50.96`, `7.63`, `0.33`, `0.48`), confirms the value matches a number in `diff` within a $\pm 0.05$ rounding tolerance.
   - If an extraneous number appears (e.g., "portfolio gained 15%"), the verification rejects the LLM response and falls back to the deterministic template.
3. **Diff Schema Enrichment**:
   - Diff JSON stores the summary inside an `ai_summary` object:
     ```json
     "ai_summary": {
       "text": "...",
       "provider": "openrouter" | "template_fallback",
       "verified": true,
       "generated_at": "2026-10-02T01:00:00Z"
     }
     ```
4. **Dashboard Presentation**:
   - Rendered prominently in `web/src/app/fund/[id]/page.tsx` with a glowing badge ("AI Summary" or "Automated Summary"), provider label, and safety disclaimer.

---

## Detailed Task Breakdown

### Task 1: Summarizer Module (`pipeline/summarize.py`)
- Implement `Summarizer` class:
  - System prompt enforcing strict factuality: "You are a financial portfolio analyst. Summarize this mutual fund top-10 holdings diff. Use only the exact numbers provided. Do not invent numbers, cite outside news, or give advice."
  - Providers: OpenRouter (`google/gemini-2.0-flash-exp:free`), Gemini, Groq, and Template.
  - Method `generate_summary(diff_data) -> Dict[str, Any]`.
  - Method `verify_numbers(summary_text, diff_data) -> bool`.
  - Method `generate_template_summary(diff_data) -> str`.
- CLI interface:
  - `python3 pipeline/summarize.py --diff data/ppfas-flexicap/2026-08.diff.json`

### Task 2: Pipeline Integration
- Integrate `Summarizer` into `pipeline/diff.py` and `pipeline/run.py` so that whenever a diff is calculated, `ai_summary` is computed and embedded.
- Re-run backfill on fixtures to populate `ai_summary` in `data/ppfas-flexicap/*.diff.json`.

### Task 3: Dashboard Display Enhancement
- Update `web/src/types/index.ts` to type `ai_summary`.
- Update `web/src/app/fund/[id]/page.tsx` to display the AI summary card with provider attribution and verified badge.
- Re-run `npm --prefix web run build` to verify clean static compilation.

### Task 4: Unit & Integration Tests (`pipeline/tests/test_summarize.py`)
- Test 1: Template generator produces accurate 3–4 sentence summary matching diff metrics.
- Test 2: Number verifier accepts valid LLM text containing only diff numbers (UAT 5).
- Test 3: Number verifier rejects LLM text with fabricated percentages or numbers (UAT 5).
- Test 4: Summarizer falls back to template when API call fails or keys are missing (UAT 6).

---

## Verification & Acceptance Checklist
- [ ] `pytest pipeline/tests/test_summarize.py` passes with 100% green tests.
- [ ] Number verifier rejects text with hallucinated metrics (UAT Criteria #5).
- [ ] Fallback template generates valid summary in offline/keyless environments (UAT Criteria #6).
- [ ] Generated `data/ppfas-flexicap/*.diff.json` contain `ai_summary` object.
- [ ] Dashboard displays AI summary card with "Verified" badge.
- [ ] Full `pytest pipeline/tests/` and Next.js `npm run build` pass without errors.

# Phase 8: README & Documentation — Plan

## Goal
Author comprehensive, high-quality documentation in `README.md` that serves both end-users and developers. Explains the zero-cost architecture, installation, local pipeline execution, how to add new funds via configuration, GitHub Actions workflow secrets setup, Vercel deployment, and test suite verification.

---

## Requirements Addressed
- **FR-10.1**: Comprehensive `README.md` detailing system architecture, prerequisites, local setup, and deployment.
- **FR-10.2**: Step-by-step "Add a Fund" guide demonstrating how any equity scheme can be added via `config/funds.json` without modifying Python or TypeScript code.
- **FR-10.3**: Secrets and environment configuration guide covering optional LLM providers (OpenRouter, Gemini, Groq) and GitHub Actions automated commit permissions.
- **FR-10.4**: Testing and local development instructions covering the 37-test Python test suite and Next.js static build workflow.

---

## Architecture & Technical Decisions

1. **Structured Technical Documentation**:
   - Clear visual hierarchy with badges, architecture flow diagrams, feature highlights, and copy-pasteable terminal commands.
2. **Pragmatic Quickstart**:
   - Provide exact steps for cloning, setting up Python 3.9–3.11 virtualenv, installing dependencies, and running local verification in under 60 seconds.
3. **Walkthrough of Config-Driven Extensibility**:
   - Concrete example of expanding from `ppfas-flexicap` to other AMCs and schemes, detailing `excel_sheet`, `pdf_section_keyword`, and alias normalization rules.
4. **Vercel Hobby Zero-Config Guide**:
   - Document how the `prebuild` sync hook guarantees zero runtime compute overhead while enabling sub-second static page serving.

---

## Detailed Task Breakdown

### Task 1: Comprehensive README.md Creation
- **Header & Badges**: Python, Next.js, Vercel, License, Test Suite status.
- **System Architecture**: High-level ASCII diagram illustrating the scheduled pipeline (GitHub Actions -> Scrape -> Parse -> Validate -> Diff -> Hallucination-Verified AI Summary -> Data Commit -> Vercel Static Deploy).
- **Core Features**:
  - 100% Free Stack (zero paid APIs, zero databases, zero cloud bills).
  - Multi-tier Parser Engine (Excel with OpenXML/xlrd fallback, PDF with dynamic page discovery).
  - Validation-First Invariants (monotonic rank/weights, exact top-10 check).
  - Diff Engine & Neutral Phrasing (entered/exited top 10, weight deltas).
  - Zero-Hallucination AI Summarizer (strict number validation post-check with deterministic template fallback).
  - Dark-Mode Glassmorphic Next.js Dashboard.
- **Local Setup & Development**:
  - Python pipeline setup (`pip install -r requirements.txt`).
  - Running test suite (`pytest pipeline/tests/ -v`).
  - Running pipeline locally (`python3 pipeline/run.py --dry-run`).
  - Running Next.js dashboard (`npm --prefix web install && npm --prefix web run dev`).
  - Building production bundle (`npm --prefix web run build`).
- **Guide: Adding a New Fund**:
  - Explaining each field in `config/funds.json`.
  - Adding company name mappings to `config/aliases.json`.
  - Running backfill or runner to populate new fund data.
- **GitHub Actions & Deployment Guide**:
  - Setting up scheduled workflow cron.
  - Configuring optional LLM secrets (`OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`).
  - Configuring GitHub repo `Workflow permissions` (Read and write permissions for `GITHUB_TOKEN`).
  - Deploying to Vercel Hobby.

### Task 2: Verification of All Commands & Instructions
- Validate that all commands cited in the README execute cleanly:
  - `python3 -m pytest pipeline/tests/ -v`
  - `python3 pipeline/run.py --dry-run`
  - `npm --prefix web run build`

### Task 3: Roadmap & Milestone 2 Completion
- Update `.planning/ROADMAP.md` and `.planning/STATE.md` marking Phase 8 and Milestone 2 as complete.
- Record final git commit and phase summary.

---

## Verification & Acceptance Checklist
- [ ] `README.md` exists and contains all required sections (setup, architecture, add-a-fund guide, secrets, local run, testing).
- [ ] Code snippets and CLI commands documented in `README.md` are tested and verified.
- [ ] Full test suite passes 37/37 tests.
- [ ] Next.js static build succeeds with 6/6 pages.

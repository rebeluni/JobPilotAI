# JobPilot AI 🚀

JobPilot AI is a local-first, privacy-respecting, intelligent job discovery, matching, immigration-awareness, application preparation, browser-assisted form filling, and application tracking platform built for **Ankita Yadav** (B.Tech in Artificial Intelligence & Data Science, Mumbai, ~1 yr experience).

Built with truthful AI principles:
- **Zero Fabrication**: Never invents or assumes user skills, degrees, experience, companies, or authorization.
- **Unresolved Data Safety**: Incomplete details stay marked as `NEEDS_USER_INPUT`.
- **Human in the Loop**: Crucial actions (submissions, legal authorizations) require explicit user approval (typing `SUBMIT`).
- **Modular Isolation**: Modules communicate exclusively through shared schemas in `jobpilot.core.schemas`.
- **Cloud-Sync Protection**: SQLite database and browser sessions reside in `C:\Users\Ankita\Desktop\JobPilotData` to prevent cloud sync corruption.

---

## Architecture & Subsystems

1. **Core Contracts & Pipeline (`jobpilot/core/`)**:
   - Strictly typed Pydantic contracts (`JobRecord`, `MatchResult`, `VisaEvidence`, `ResumeDoc`, `CoverLetterDoc`, `ApplicationPackage`).
   - Central `PluginRegistry` for discovery sources, LLM providers, document renderers, and ATS handlers.
   - Standardized `PipelineStage` base class and dynamic `FeatureFlags`.
   - `safety.py`: Enforces zero hallucination, prohibits unverified answers to legal/sensitive questions, and enforces candidate approval.

2. **Database & Verified Profile (`jobpilot/database/` & `jobpilot/profiles/`)**:
   - 12 SQLAlchemy ORM models with SQLite repository layer.
   - `ankita_profile.yaml`: Canonical verified candidate facts (69 verified facts, 27 tracked `NEEDS_USER_INPUT` flags).
   - `answer_bank.yaml`: Form question answer bank.

3. **Discovery & Normalization (`jobpilot/discovery/` & `jobpilot/extraction/`)**:
   - Discovery sources: SearXNG meta-search, Greenhouse API, Lever API, Remotive API, Adzuna API.
   - Multi-tier deduplication via normalized URL hashes and company/title content hashes.
   - LLM-powered `RoleExpander` across EXACT, ADJACENT, and STRETCH tiers.
   - Multi-currency salary parser (INR LPA/Lakhs, USD, EUR, GBP), experience range extractor, skill parser, and `JobQualityChecker`.

4. **Matching Engine (`jobpilot/matching/`)**:
   - 2-stage matching: Vector cosine similarity pre-ranking (`nomic-embed-text`) + 7-dimension scoring.
   - Soft experience penalties (-0.15/year gap with `concerns` flag; no automatic rejection).
   - Hard filters (DevOps/SysAdmin, Java/Spring-primary, NOT_SUITABLE visa).
   - Thumbs-up/down adaptive weight calibration.

5. **Immigration Evidence Layer (`jobpilot/immigration/`)**:
   - Evaluators for India (Domestic authorization, confidence HIGH), UK (Skilled Worker), Germany (EU Blue Card / Opportunity Card), Netherlands (Highly Skilled Migrant), Canada (GSS / Express Entry), Australia (Skills in Demand), Singapore (COMPASS), UAE (Green Visa).
   - Unverified threshold rule confidence capping: until set to `verified: true` by the user, confidence is strictly capped at `LOW`.
   - Mandatory legal disclaimer included in every `VisaEvidence` record.

6. **Account & Session Management (`jobpilot/accounts/`)**:
   - `Vault`: Secure credential storage using Windows Credential Manager (`keyring`) with encrypted local fallback. Zero plaintext in SQLite or logs.
   - `creator.py`: Generates cryptographically strong passwords satisfying enterprise ATS complexity rules.
   - `session_manager.py`: Persists Playwright browser context states in `JobPilotData/sessions/`.
   - `email_verifier.py`: Extracts activation links and 4-8 digit OTP codes from emails with manual fallback.

7. **Application Preparation & Resume Optimizer (`jobpilot/applications/`)**:
   - `ResumeMaster`: Formats master resume and domain variants (`ai_engineer`, `ai_automation`, `data_analytics`).
   - `ResumeOptimizer`: Three modes (`OFF`, `SUGGEST`, `AUTO`). Reorders existing verified skills and bullets to match target job; enforces `assert_optimizer_no_new_claims`.
   - `CoverLetterGenerator`: Tailored letters grounded strictly in real verified profile data.
   - `AnswerEngine`: Matches ATS form questions to profile facts and answer bank. Flags legal/sensitive questions as `NEEDS_USER_INPUT`.
   - `QAChecker`: Pre-submission truthfulness auditor ensuring 0 hallucinations and 0 unapproved submissions.

8. **Document Generation (`jobpilot/documents/`)**:
   - `FormatDetector`: Auto-detects ATS document preferences (defaults to PDF; generates DOCX or TXT if mandated).
   - `html_template.py`: Clean, single-column, ATS-parseable HTML/CSS templates.
   - `PDFRenderer`: Playwright headless Chromium/Chrome/Edge renderer generating pixel-perfect PDFs.
   - `DocxRenderer`: Microsoft Word `.docx` generator using `python-docx`.

9. **Browser Automation & Submission Gate (`jobpilot/browser/`)**:
   - `FieldMapper`: Classifies form inputs for Greenhouse, Lever, Ashby, Workday.
   - `HandoffManager`: Detects Cloudflare Turnstile, reCAPTCHA, hCaptcha, MFA prompts, and unresolved questions.
   - `FormFiller`: Safely populates fields and uploads documents; skips unresolved fields for human completion.
   - `ReviewScreen`: Displays pre-submission inspection summary.
   - `SubmissionGate`: Safety gate requiring candidate to explicitly type `"SUBMIT"` to authorize final submission.

10. **Tracker & Follow-Ups (`jobpilot/tracker/`)**:
    - `StatusManager`: Lifecycle state machine (`DRAFT -> REVIEW -> SUBMITTED -> INTERVIEW -> OFFER`).
    - `AuditTrail`: Immutable event logging to SQLite `application_events` table.
    - `FollowUpManager`: Calculates 5-day business deadlines and generates polite follow-up inquiry drafts.

11. **Unified Dashboard (`jobpilot/dashboard/`)**:
    - Streamlit web application with 10 comprehensive modules and modern dark-mode UI.

---

## Quick Start Guide

### 1. Setup Environment
Ensure Python 3.11+ is installed.
```bash
pip install -r requirements.txt
```

### 2. Initialize Database & Profiles
```bash
python scripts/setup_db.py
```
Initializes the SQLite database at `C:\Users\Ankita\Desktop\JobPilotData\jobpilot.db`, sets up all 12 tables, and loads candidate facts.

### 3. Launch the Unified Streamlit Dashboard
```bash
python scripts/run_dashboard.py
```
Launches the 10-module web dashboard at `http://localhost:8501`.

### 4. CLI Tools
- **Job Discovery:**
  ```bash
  python scripts/run_discovery.py --countries "India, Germany, Netherlands" --roles "AI_ENGINEER, AI_AUTOMATION" --auto-approve-roles
  ```
- **Job Matching:**
  ```bash
  python scripts/run_matching.py --limit 50 --min-score 0.50
  ```

### 5. Run Full Test Suite
```bash
pytest tests/ -v
```
All **128 tests** across all 11 modules pass with 100% green status.

---

## Configuration Files

- `config/settings.yaml`: App settings, data directory paths, LLM model routing, matching dimension weights, browser timeouts.
- `config/immigration_rules.yaml`: Per-country routes, salary thresholds, and government verification status flags.
- `config/role_families.yaml`: Role family hierarchy, technical keywords, and hard exclusion filters.
- `jobpilot/profiles/ankita_profile.yaml`: Canonical verified facts for candidate.
- `jobpilot/profiles/answer_bank.yaml`: Form question answer bank.

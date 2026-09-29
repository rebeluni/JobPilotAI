# JobPilot AI — Comprehensive Project Plan

> **Status:** Planning Document · Version 2.0  
> **Author:** Architect Agent (Antigravity) — updated from Claude review session  
> **Date:** 2026-09-29  
> **Project Folder:** `C:\Users\Ankita\OneDrive\Documents\JobPilotAI`

> [!IMPORTANT]
> **v2.0 Changes:** Phase 0 added (core contracts + registry + feature flags), RoleExpander module, Resume Optimizer with toggle, format-aware document renderer, Phase 8b (Accounts & Sessions with credential vault + email verifier + HandoffManager), feedback loop, interview prep, networking module, audit trail, immigration thresholds moved to config, answer bank corrected, OneDrive/SQLite data-sync warning, profile made user-configurable.

---

## Table of Contents

1. [Project Vision & Principles](#1-project-vision--principles)
2. [Technology Stack](#2-technology-stack)
3. [Project Directory Structure](#3-project-directory-structure)
4. [Database Schema (SQLite)](#4-database-schema-sqlite)
5. [User Truth Database & Profile](#5-user-truth-database--profile)
6. [Core Contracts & Plugin Registry](#6-core-contracts--plugin-registry)
7. [LLM Abstraction Layer](#7-llm-abstraction-layer)
8. [Module-by-Module Architecture](#8-module-by-module-architecture)
   - [8.1 Discovery Layer & RoleExpander](#81-discovery-layer--roleexpander)
   - [8.2 Extraction & Normalization](#82-extraction--normalization)
   - [8.3 Matching Engine (Hybrid Embedding + LLM)](#83-matching-engine-hybrid-embedding--llm)
   - [8.4 Immigration Intelligence Layer](#84-immigration-intelligence-layer)
   - [8.5 Resume Optimizer & Cover Letter Engine](#85-resume-optimizer--cover-letter-engine)
   - [8.6 Document Renderer (Format Registry)](#86-document-renderer-format-registry)
   - [8.7 Application Answer Engine](#87-application-answer-engine)
   - [8.8 Browser Automation Layer](#88-browser-automation-layer)
   - [8.9 Accounts & Sessions (Credential Vault + Email Verifier)](#89-accounts--sessions-credential-vault--email-verifier)
   - [8.10 Human Review & Submission Gate](#810-human-review--submission-gate)
   - [8.11 Feedback Loop & Match Calibration](#811-feedback-loop--match-calibration)
   - [8.12 Networking Module](#812-networking-module)
   - [8.13 Interview Prep Module](#813-interview-prep-module)
   - [8.14 Job Quality & Freshness Checks](#814-job-quality--freshness-checks)
   - [8.15 Streamlit Dashboard](#815-streamlit-dashboard)
9. [Phase-by-Phase Implementation Plan](#9-phase-by-phase-implementation-plan)
10. [Configuration System](#10-configuration-system)
11. [Safety & Ethics Rules (Hard-coded)](#11-safety--ethics-rules-hard-coded)
12. [Testing Strategy](#12-testing-strategy)
13. [Security Guidelines](#13-security-guidelines)
14. [Key Implementation Decisions & Risks](#14-key-implementation-decisions--risks)
15. [Dependency List](#15-dependency-list)
16. [Execution Checklist for Each Phase](#16-execution-checklist-for-each-phase)

---

## 1. Project Vision & Principles

JobPilot AI is a **local-first**, **truth-preserving**, **entirely free**, **AI-powered** job platform. It is not a blind mass-application bot. It discovers, evaluates, and prepares job applications, automates account creation, login, and form filling, and keeps the human in control of final submission and sensitive decisions.

### Core Principles (NON-NEGOTIABLE — enforced in code, not just comments)

| ID | Principle |
|----|-----------|
| P-1 | Never fabricate user experience, skills, certifications, education, employment history, work authorization, salary history, project responsibilities, metrics, or achievements. |
| P-2 | If information is unavailable in the verified user profile, return `NEEDS_USER_INPUT`. Never guess. |
| P-3 | The user must explicitly approve every job application before final submission. |
| P-4 | Never make immigration determinations. Always attribute sources, flag confidence levels, and include a legal disclaimer. |
| P-5 | The system must be entirely free. No paid APIs unless the user explicitly opts in and configures a key. |
| P-6 | The LLM provider must be swappable without rewriting any application logic. |
| P-7 | All credentials live in environment variables or the OS credential vault (keyring). Never in source code, YAML, or the database. |
| P-8 | Discovery is read-only and non-destructive. Rate limit requests. Respect delays. |
| P-9 | Modules communicate only through shared Pydantic schemas. No module imports another module's internals. |
| P-10 | Every module must degrade gracefully when a neighboring module is disabled via feature flag. |

### New Principles (v2.0)

| ID | Principle |
|----|-----------|
| P-11 | Account creation and login can be automated. CAPTCHA, 2FA, and unexpected screens must pause and hand control to the user. |
| P-12 | The Resume Optimizer may never add a skill, metric, or claim that is not already in the verified profile. It may only reorder, select, and emphasize. |
| P-13 | Immigration thresholds are never hardcoded. They live in `config/immigration_rules.yaml` with a `source_date` and `verified` flag. |
| P-14 | The profile path is configurable. No code is hardcoded to "Ankita". |

---

## 2. Technology Stack

| Category | Choice | Rationale |
|----------|--------|-----------|
| Primary Language | Python 3.11+ | Strong AI/ML ecosystem, async support, cross-platform |
| Database | SQLite + SQLAlchemy + **Alembic** | Local-first, zero config; Alembic prevents data loss on schema change |
| LLM Local | Ollama (e.g., `llama3.1:8b`, `mistral`, `qwen2.5`) | Free, local, private |
| Embeddings (local) | `nomic-embed-text` via Ollama | Free local embeddings for bulk matching |
| LLM Remote (optional) | Gemini / Anthropic / OpenAI (opt-in only) | Configurable; system works with zero API keys |
| Job Discovery | SearXNG (self-hosted or public) + Greenhouse + Lever + Adzuna + Remotive + HN | All free public APIs or scraping |
| Browser Automation | Playwright (Python) | Form filling, PDF generation via `page.pdf()`, session persistence |
| Dashboard | Streamlit | Python-native, no frontend needed |
| Config | YAML + `python-dotenv` | Human-readable; secrets stay in `.env` or keyring |
| HTTP | `httpx` (async) | Modern async HTTP |
| HTML Parsing | `BeautifulSoup4` + `lxml` | Reliable HTML extraction |
| Scheduling | `APScheduler` | In-process scheduling |
| Testing | `pytest` + `pytest-asyncio` | Standard Python testing |
| CLI | `Click` | Clean CLI interface |
| Data Validation | `Pydantic v2` | Schema validation, serialization, inter-module contracts |
| Logging | `loguru` + `rich` | Structured, colorized logs |
| Resume (source) | YAML/JSON structured master resume | Structured data enables optimizer; not free-form DOCX |
| Resume (render) | `python-docx` + Jinja2 → DOCX; Playwright `page.pdf()` → PDF | PDF via Playwright avoids Windows GTK (weasyprint) issues |
| Credential Vault | `keyring` (Windows Credential Manager) | Free, encrypted by OS login; no passwords in files |
| Email Verification | `imaplib` (stdlib) or Gmail API free tier | Auto-read verification emails |
| Session Persistence | Playwright `storage_state` per site | Stay logged in without re-authenticating |
| Notifications | `win10toast` | Windows toast alerts for handoff events |

> [!CAUTION]
> **OneDrive + SQLite Risk:** The project folder is inside OneDrive. An active SQLite database being cloud-synced can corrupt. **Move `data/` outside OneDrive** or exclude it from sync before running. Session files and `data/` must never sync to the cloud — they contain PII and login tokens.

---

## 3. Project Directory Structure

```
JobPilotAI/
│
├── PLAN.md
├── README.md
├── requirements.txt
├── .env.example
├── .gitignore
├── alembic.ini                         # Alembic migration config
│
├── config/
│   ├── settings.yaml                   # Main config (targets, modules, LLM, browser)
│   ├── search_queries.yaml             # Dynamic query templates
│   ├── immigration_rules.yaml          # Per-country thresholds (source_date + verified flag)
│   ├── role_families.yaml              # Role family definitions and keyword maps
│   └── role_expansions_cache.yaml      # LLM-generated + user-approved role expansions (auto-managed)
│
├── data/                               # !! Move this OUTSIDE OneDrive !!
│   ├── jobpilot.db                     # SQLite database
│   ├── sessions/                       # Playwright storage_state per site (login tokens — sensitive)
│   ├── resumes/                        # Rendered resume files (DOCX + PDF)
│   ├── cover_letters/                  # Generated cover letter files
│   ├── exports/                        # CSV/JSON exports
│   ├── audit/                          # Screenshots + form snapshots at submission time
│   └── cache/                          # HTTP response cache
│
├── jobpilot/
│   ├── __init__.py
│   │
│   ├── core/                           # Shared schemas & registry — the contract layer
│   │   ├── __init__.py
│   │   ├── schemas.py                  # ALL shared Pydantic schemas (JobRecord, MatchResult, etc.)
│   │   ├── registry.py                 # PluginRegistry for sources, providers, renderers, ATS handlers
│   │   ├── pipeline.py                 # PipelineStage base class (run(input) -> output)
│   │   ├── feature_flags.py            # Feature flag loader and accessor
│   │   └── safety.py                   # SafetyViolation + all safety assertion functions
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                   # SQLAlchemy ORM models
│   │   ├── repository.py               # CRUD operations
│   │   └── alembic/                    # Alembic migration versions
│   │       ├── env.py
│   │       └── versions/
│   │
│   ├── profiles/
│   │   ├── __init__.py
│   │   ├── loader.py                   # Load profile from YAML path (configurable, not hardcoded)
│   │   ├── answer_bank.py              # Answer bank loader and question matcher
│   │   └── {username}_profile.yaml    # User's verified fact file (path set in settings.yaml)
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── base.py                     # LLMProvider + EmbeddingProvider abstract interfaces
│   │   ├── ollama_provider.py          # Ollama LLM + embeddings implementation
│   │   ├── gemini_provider.py
│   │   ├── anthropic_provider.py
│   │   ├── openai_provider.py
│   │   └── factory.py                  # Provider factory (reads config + registry)
│   │
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── base.py                     # BaseDiscoverySource (PipelineStage subclass)
│   │   ├── searxng.py
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── adzuna.py                   # Adzuna API (free tier)
│   │   ├── remotive.py                 # Remotive public API
│   │   ├── hn_hiring.py                # HN "Who's Hiring" scraper
│   │   ├── ashby.py                    # Ashby public boards
│   │   ├── smartrecruiters.py          # SmartRecruiters public boards
│   │   ├── workable.py                 # Workable public boards
│   │   ├── career_pages.py
│   │   ├── role_expander.py            # RoleExpander: LLM-powered job title expansion
│   │   ├── query_builder.py
│   │   └── deduplicator.py
│   │
│   ├── extraction/
│   │   ├── __init__.py
│   │   ├── html_extractor.py
│   │   ├── api_extractor.py
│   │   ├── normalizer.py
│   │   └── quality_checker.py          # Job freshness, ghost-job, and scam detection
│   │
│   ├── matching/
│   │   ├── __init__.py
│   │   ├── engine.py                   # Orchestrator: embeddings → shortlist → LLM judge
│   │   ├── embedder.py                 # nomic-embed-text via Ollama for bulk ranking
│   │   ├── scorer.py                   # Per-dimension scoring functions
│   │   ├── filters.py                  # Soft penalties (not hard filters) for experience gap
│   │   ├── feedback.py                 # Thumbs up/down → weight calibration
│   │   └── calibration.py              # Labeled test set + scoring metric
│   │
│   ├── immigration/
│   │   ├── __init__.py
│   │   ├── classifier.py
│   │   ├── evidence.py
│   │   ├── routes.py                   # Loads from immigration_rules.yaml (not hardcoded)
│   │   └── countries/
│   │       ├── uk.py
│   │       ├── germany.py
│   │       ├── netherlands.py
│   │       ├── canada.py
│   │       ├── australia.py
│   │       ├── singapore.py
│   │       ├── uae.py
│   │       └── india.py
│   │
│   ├── applications/
│   │   ├── __init__.py
│   │   ├── resume_selector.py
│   │   ├── resume_optimizer.py         # Optimizer with OFF/SUGGEST/AUTO modes
│   │   ├── resume_master.py            # Loads structured master resume YAML
│   │   ├── cover_letter_gen.py
│   │   ├── answer_engine.py
│   │   ├── qa_checker.py
│   │   └── templates/
│   │       ├── resume_base.jinja2
│   │       ├── cover_letter.jinja2
│   │       └── motivation.jinja2
│   │
│   ├── documents/
│   │   ├── __init__.py
│   │   ├── base.py                     # DocumentRenderer interface
│   │   ├── pdf_renderer.py             # Playwright page.pdf() renderer
│   │   ├── docx_renderer.py            # python-docx renderer
│   │   ├── txt_renderer.py             # Plain text renderer
│   │   ├── format_detector.py          # Reads form accept attr + posting text → chooses format
│   │   └── registry.py                 # Format registry (registered via PluginRegistry)
│   │
│   ├── browser/
│   │   ├── __init__.py
│   │   ├── agent.py                    # Main browser automation orchestrator
│   │   ├── field_mapper.py
│   │   ├── form_filler.py
│   │   ├── form_types.py
│   │   ├── review_screen.py
│   │   ├── submission_gate.py
│   │   └── handoff_manager.py          # Detects CAPTCHA/2FA/unexpected → pauses + notifies user
│   │
│   ├── accounts/
│   │   ├── __init__.py
│   │   ├── vault.py                    # keyring-based credential vault
│   │   ├── creator.py                  # Automated account creation flow
│   │   ├── login.py                    # Automated login with saved sessions
│   │   ├── email_verifier.py           # IMAP/Gmail API email verification
│   │   └── session_manager.py          # Playwright storage_state manager
│   │
│   ├── tracker/
│   │   ├── __init__.py
│   │   ├── follow_ups.py               # Follow-up reminders and draft emails
│   │   ├── status_updater.py           # Detect status changes from email or manual input
│   │   └── audit_trail.py              # Screenshot + form snapshot at submission
│   │
│   ├── networking/
│   │   ├── __init__.py
│   │   └── message_gen.py              # Recruiter outreach + referral request message drafts
│   │
│   ├── interview/
│   │   ├── __init__.py
│   │   ├── prep.py                     # Per-job question set generation
│   │   └── company_notes.py            # Company research notes from job posting
│   │
│   └── dashboard/
│       ├── __init__.py
│       ├── app.py
│       ├── pages/
│       │   ├── 01_discovery.py
│       │   ├── 02_shortlist.py
│       │   ├── 03_international.py
│       │   ├── 04_applications.py
│       │   ├── 05_tracker.py
│       │   ├── 06_networking.py
│       │   ├── 07_interview.py
│       │   ├── 08_profile.py
│       │   └── 09_settings.py
│       └── components/
│           ├── job_card.py
│           ├── visa_badge.py
│           ├── match_score_bar.py
│           ├── optimizer_toggle.py     # Resume optimizer ON/OFF/SUGGEST per session
│           └── filters.py
│
├── scripts/
│   ├── setup_db.py
│   ├── run_discovery.py
│   ├── run_matching.py
│   ├── run_application.py
│   └── export_jobs.py
│
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── test_profile.yaml
│   │   ├── sample_jobs.json
│   │   └── sample_greenhouse_response.json
│   ├── contract/                        # Contract tests — validate every module's output schema
│   │   ├── test_job_record_contract.py
│   │   ├── test_match_result_contract.py
│   │   ├── test_visa_evidence_contract.py
│   │   └── test_resume_doc_contract.py
│   ├── test_database.py
│   ├── test_extraction.py
│   ├── test_deduplication.py
│   ├── test_role_expander.py
│   ├── test_matching.py
│   ├── test_immigration.py
│   ├── test_answer_engine.py
│   ├── test_truth_validation.py
│   ├── test_resume_optimizer.py
│   ├── test_document_renderer.py
│   ├── test_browser_mapping.py
│   ├── test_handoff_manager.py
│   └── test_qa_checker.py
│
└── docs/
    ├── ARCHITECTURE.md
    ├── IMMIGRATION_LOGIC.md
    ├── USER_PROFILE_GUIDE.md
    ├── RESUME_OPTIMIZER_GUIDE.md
    ├── BROWSER_AGENT_GUIDE.md
    └── ACCOUNTS_SESSIONS_GUIDE.md
```

---

## 4. Database Schema (SQLite)

All tables use SQLAlchemy ORM. Migrations managed by **Alembic** (never wipe data on schema change).

### 4.1 `jobs` Table

```sql
CREATE TABLE jobs (
    job_id                          TEXT PRIMARY KEY,  -- SHA256(company + title + url)
    company                         TEXT NOT NULL,
    title                           TEXT NOT NULL,
    description                     TEXT,
    location                        TEXT,
    country                         TEXT,
    remote_policy                   TEXT,              -- REMOTE/HYBRID/ONSITE/UNKNOWN
    employment_type                 TEXT,              -- FULL_TIME/PART_TIME/CONTRACT/UNKNOWN
    salary_min                      REAL,
    salary_max                      REAL,
    currency                        TEXT,
    experience_min                  INTEGER,
    experience_max                  INTEGER,
    skills                          TEXT,              -- JSON array
    role_family                     TEXT,
    role_tier                       TEXT,              -- EXACT/ADJACENT/STRETCH (from RoleExpander)
    job_url                         TEXT NOT NULL,
    source                          TEXT NOT NULL,
    date_posted                     TEXT,
    date_found                      TEXT NOT NULL,
    is_expired                      INTEGER DEFAULT 0,
    is_ghost_job                    INTEGER DEFAULT 0, -- Suspected repost with no real opening
    quality_score                   REAL,              -- 0-1 quality signal
    -- Immigration
    visa_status                     TEXT,
    visa_evidence                   TEXT,              -- JSON blob
    immigration_route               TEXT,
    sponsor_verified                INTEGER DEFAULT 0,
    relocation_support              INTEGER DEFAULT 0,
    international_applicant_signal  TEXT,
    work_authorization_requirement  TEXT,
    -- Matching
    embedding_vector                TEXT,              -- JSON float array for semantic matching
    match_score                     REAL,
    match_status                    TEXT,
    match_reasoning                 TEXT,              -- JSON blob
    recommended_resume              TEXT,
    application_priority            TEXT,
    -- Status
    status                          TEXT DEFAULT 'NEW',
    user_feedback                   TEXT,              -- THUMBS_UP/THUMBS_DOWN/null
    is_duplicate                    INTEGER DEFAULT 0,
    created_at                      TEXT NOT NULL,
    updated_at                      TEXT NOT NULL
);
```

### 4.2 `companies` Table

```sql
CREATE TABLE companies (
    company_id       TEXT PRIMARY KEY,
    name             TEXT NOT NULL,
    domain           TEXT,
    country          TEXT,
    greenhouse_board TEXT,
    lever_site       TEXT,
    ashby_board      TEXT,
    career_page_url  TEXT,
    known_sponsor    INTEGER DEFAULT 0,
    sponsor_evidence TEXT,            -- JSON
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
```

### 4.3 `site_accounts` Table (NEW)

```sql
CREATE TABLE site_accounts (
    account_id      TEXT PRIMARY KEY,
    site_url        TEXT NOT NULL,        -- Base URL of the site (e.g. myworkdayjobs.com)
    site_name       TEXT NOT NULL,
    username        TEXT NOT NULL,        -- Usually email address
    -- Password stored in OS keyring under key: jobpilot:{site_url}:{username}
    -- NEVER stored here
    session_file    TEXT,                 -- Path to Playwright storage_state JSON
    created_at      TEXT NOT NULL,
    last_used_at    TEXT,
    notes           TEXT
);
```

### 4.4 `applications` Table

```sql
CREATE TABLE applications (
    application_id   TEXT PRIMARY KEY,
    job_id           TEXT NOT NULL REFERENCES jobs(job_id),
    account_id       TEXT REFERENCES site_accounts(account_id),
    status           TEXT DEFAULT 'DRAFT',  -- DRAFT/REVIEW/SUBMITTED/REJECTED/INTERVIEW/OFFER
    resume_version   TEXT,
    resume_optimized INTEGER DEFAULT 0,     -- Was optimizer applied?
    optimizer_mode   TEXT,                  -- OFF/SUGGEST/AUTO
    cover_letter_id  TEXT,
    applied_at       TEXT,
    platform         TEXT,                  -- ats_greenhouse/lever/workday/direct/email
    application_url  TEXT,
    notes            TEXT,
    user_approved    INTEGER DEFAULT 0,     -- MUST be 1 before any submission
    qa_passed        INTEGER DEFAULT 0,
    qa_report        TEXT,
    audit_screenshot TEXT,                  -- Path to screenshot taken at submission
    audit_form_data  TEXT,                  -- JSON snapshot of all form values at submission
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
```

### 4.5 `application_answers` Table

```sql
CREATE TABLE application_answers (
    answer_id        TEXT PRIMARY KEY,
    application_id   TEXT NOT NULL REFERENCES applications(application_id),
    field_label      TEXT NOT NULL,
    field_type       TEXT,
    answer_value     TEXT,
    answer_source    TEXT,   -- user_profile/answer_bank/generated/needs_user_input/user_verified
    is_verified      INTEGER DEFAULT 0,
    created_at       TEXT NOT NULL
);
```

### 4.6 `visa_evidence` Table

```sql
CREATE TABLE visa_evidence (
    evidence_id      TEXT PRIMARY KEY,
    job_id           TEXT REFERENCES jobs(job_id),
    company_id       TEXT REFERENCES companies(company_id),
    country          TEXT NOT NULL,
    evidence_type    TEXT,           -- job_posting/government_source/employer_profile/inferred
    source_url       TEXT,
    source_date      TEXT,
    content_snippet  TEXT,
    confidence       TEXT,           -- HIGH/MEDIUM/LOW
    classification   TEXT,
    disclaimer       TEXT DEFAULT 'Informational only. Not legal immigration advice.',
    created_at       TEXT NOT NULL
);
```

### 4.7 `user_profile` Table

```sql
CREATE TABLE user_profile (
    key          TEXT PRIMARY KEY,
    value        TEXT NOT NULL,
    value_type   TEXT,
    is_verified  INTEGER DEFAULT 1,
    last_updated TEXT NOT NULL
);
```

### 4.8 `resume_versions` Table

```sql
CREATE TABLE resume_versions (
    version_id      TEXT PRIMARY KEY,
    variant         TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    format          TEXT NOT NULL,   -- docx/pdf/txt
    version_number  INTEGER DEFAULT 1,
    is_active       INTEGER DEFAULT 1,
    optimizer_mode  TEXT,            -- OFF/SUGGEST/AUTO
    notes           TEXT,
    created_at      TEXT NOT NULL
);
```

### 4.9 `cover_letters` Table

```sql
CREATE TABLE cover_letters (
    letter_id      TEXT PRIMARY KEY,
    job_id         TEXT REFERENCES jobs(job_id),
    application_id TEXT REFERENCES applications(application_id),
    content        TEXT NOT NULL,
    file_path      TEXT,
    format         TEXT,
    is_approved    INTEGER DEFAULT 0,
    created_at     TEXT NOT NULL
);
```

### 4.10 `search_runs` Table

```sql
CREATE TABLE search_runs (
    run_id          TEXT PRIMARY KEY,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    query_count     INTEGER DEFAULT 0,
    jobs_found      INTEGER DEFAULT 0,
    jobs_new        INTEGER DEFAULT 0,
    jobs_duplicate  INTEGER DEFAULT 0,
    status          TEXT DEFAULT 'RUNNING',
    error_message   TEXT,
    config_snapshot TEXT
);
```

### 4.11 `application_events` Table

```sql
CREATE TABLE application_events (
    event_id       TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(application_id),
    event_type     TEXT NOT NULL,  -- CREATED/REVIEWED/SUBMITTED/EMAIL_RECEIVED/STATUS_CHANGE/FOLLOW_UP
    event_data     TEXT,           -- JSON
    created_at     TEXT NOT NULL
);
```

### 4.12 `match_feedback` Table (NEW)

```sql
CREATE TABLE match_feedback (
    feedback_id   TEXT PRIMARY KEY,
    job_id        TEXT NOT NULL REFERENCES jobs(job_id),
    feedback      TEXT NOT NULL,   -- THUMBS_UP/THUMBS_DOWN
    weight_delta  TEXT,            -- JSON of weight adjustments applied
    created_at    TEXT NOT NULL
);
```

---

## 5. User Truth Database & Profile

### 5.1 Profile YAML Structure

The profile path is set in `config/settings.yaml` as `user.profile_path`. It is **not hardcoded** anywhere in the codebase. Multiple users are supported by pointing to different YAML files.

```yaml
# jobpilot/profiles/ankita_profile.yaml (path configured in settings.yaml)
# THIS IS THE CANONICAL SOURCE OF TRUTH
# NEVER auto-populate fields without explicit user confirmation

personal:
  full_name: "Ankita Yadav"
  email: NEEDS_USER_INPUT
  phone: NEEDS_USER_INPUT
  location_city: "Mumbai"
  location_state: "Maharashtra"
  location_country: "India"
  linkedin_url: NEEDS_USER_INPUT
  github_url: NEEDS_USER_INPUT
  portfolio_url: NEEDS_USER_INPUT

work_authorization:
  india: true
  other_countries: false
  requires_sponsorship_india: false
  requires_sponsorship_international: true
  visa_status_note: "Indian citizen. Authorized in India without sponsorship. International roles require per-job immigration evaluation per country-specific rules."

education:
  - degree: "B.Tech"
    field: "Artificial Intelligence & Data Science"
    institution: NEEDS_USER_INPUT
    graduation_year: NEEDS_USER_INPUT
    gpa: NEEDS_USER_INPUT

experience:
  total_years_professional: 1
  total_years_approximate: true

employment_history:
  - employer: NEEDS_USER_INPUT
    title: NEEDS_USER_INPUT
    start_date: NEEDS_USER_INPUT
    end_date: NEEDS_USER_INPUT
    responsibilities: NEEDS_USER_INPUT
    achievements: NEEDS_USER_INPUT
    # Employment history is STRUCTURED DATA for the resume optimizer to use
    # Each responsibility must be tagged with skills it demonstrates
    skills_demonstrated: NEEDS_USER_INPUT

skills:
  programming: [Python, JavaScript, TypeScript, SQL]
  ai_ml: [Machine Learning, Generative AI, LLMs, RAG, AI Agents]
  platforms_tools: [Make.com, Power Automate, PowerApps, Tableau, Power BI, AWS, Docker, Git, GitHub]
  data: [Data Pipelines, Data Analytics, Automation]
  integrations: [REST APIs, Webhooks, CRM Integrations]

preferences:
  notice_period_days: NEEDS_USER_INPUT
  salary_expectation_inr: NEEDS_USER_INPUT
  salary_expectation_usd: NEEDS_USER_INPUT
  willing_to_relocate: NEEDS_USER_INPUT
  preferred_remote: NEEDS_USER_INPUT
  target_role_families:
    - AI_ENGINEER
    - AI_AUTOMATION
    - AI_SOLUTIONS_ENGINEER
    - AI_INTEGRATION_ENGINEER
    - PRODUCT_SYSTEMS
    - CRM_AUTOMATION
    - DATA_ANALYTICS
    - SOLUTIONS_ENGINEER
  target_countries: [India, Germany, Netherlands, UK, Canada, Australia, Singapore, UAE]
  avoid_roles:
    - Pure DevOps
    - Linux/SysAdmin
    - Infrastructure-heavy
    - Java/Spring-heavy
    - DSA-heavy Software Engineering
```

### 5.2 Answer Bank (Corrected)

> [!WARNING]
> **v2.0 Fix:** The v1.0 answer bank pre-filled "1 year" for Python, JS, SQL, LLM, RAG etc. without user verification, violating P-1. All `years_of_experience` entries are now `NEEDS_USER_INPUT` until the user explicitly confirms each one. The user must verify and update these before any application can use them.

```yaml
# jobpilot/profiles/answer_bank.yaml

work_authorization:
  india_answer: "Yes, I am authorized to work in India without any sponsorship."
  international_answer: "NEEDS_USER_INPUT_PER_JOB"

years_of_experience:
  # !! USER MUST VERIFY EACH ONE BEFORE THEY BECOME ACTIVE !!
  python: NEEDS_USER_INPUT
  javascript: NEEDS_USER_INPUT
  typescript: NEEDS_USER_INPUT
  sql: NEEDS_USER_INPUT
  ai_ml: NEEDS_USER_INPUT
  llm: NEEDS_USER_INPUT
  rag: NEEDS_USER_INPUT
  api: NEEDS_USER_INPUT
  automation: NEEDS_USER_INPUT
  crm: NEEDS_USER_INPUT
  make_com: NEEDS_USER_INPUT
  power_automate: NEEDS_USER_INPUT
  tableau: NEEDS_USER_INPUT
  power_bi: NEEDS_USER_INPUT
  aws: NEEDS_USER_INPUT

highest_education: "Bachelor of Technology (B.Tech) in Artificial Intelligence & Data Science"
notice_period: NEEDS_USER_INPUT
salary_expectation_inr: NEEDS_USER_INPUT
salary_expectation_usd: NEEDS_USER_INPUT
willing_to_relocate: NEEDS_USER_INPUT
preferred_work_mode: NEEDS_USER_INPUT
```

---

## 6. Core Contracts & Plugin Registry

This is the most critical new addition in v2.0. Without it, modules become entangled.

### 6.1 The Rule

> **Every module communicates only through schemas defined in `jobpilot/core/schemas.py`. No module ever imports from another module's internals.**

This means:
- `matching/engine.py` receives a `List[JobRecord]` and returns a `List[MatchResult]`
- It does not know about `discovery/searxng.py` or `extraction/normalizer.py`
- If `immigration` is disabled, `matching/engine.py` receives `MatchInput` with `visa_status=UNKNOWN` and scores accordingly

### 6.2 Shared Schemas (`core/schemas.py`)

All inter-module Pydantic models live here. Key schemas:

```python
class JobRecord(BaseModel): ...       # Output of extraction, input to matching + immigration
class MatchResult(BaseModel): ...     # Output of matching, input to applications
class VisaEvidence(BaseModel): ...    # Output of immigration, stored in DB
class ResumeDoc(BaseModel): ...       # Output of resume_optimizer, input to document renderer
class CoverLetterDoc(BaseModel): ...  # Output of cover_letter_gen, input to document renderer
class ApplicationPackage(BaseModel):  # Input to browser agent: job + resume + cover letter + answers
    job: JobRecord
    match: MatchResult
    resume: ResumeDoc
    cover_letter: Optional[CoverLetterDoc]
    answers: List[ApplicationAnswer]
```

### 6.3 Pipeline Stage Interface

```python
# jobpilot/core/pipeline.py

from abc import ABC, abstractmethod
from typing import Any

class PipelineStage(ABC):
    """Every pipeline stage implements this interface."""
    stage_name: str

    @abstractmethod
    async def run(self, input_data: Any) -> Any:
        """Process input, return output. Both typed by core/schemas.py."""
        ...

    async def health_check(self) -> bool:
        """Return False if this stage's dependencies are unavailable."""
        return True
```

When a stage is disabled via feature flags, its `run()` returns a safe passthrough or empty result. No other stage breaks.

### 6.4 Plugin Registry

```python
# jobpilot/core/registry.py

class PluginRegistry:
    """
    Central registry for all swappable components.
    Adding a new discovery source, LLM provider, document renderer, or ATS handler
    means adding ONE file and ONE config line — nothing else changes.
    """
    _discovery_sources: dict[str, type[BaseDiscoverySource]] = {}
    _llm_providers: dict[str, type[LLMProvider]] = {}
    _document_renderers: dict[str, type[DocumentRenderer]] = {}
    _ats_handlers: dict[str, type[ATSHandler]] = {}

    @classmethod
    def register_source(cls, name: str):
        """@PluginRegistry.register_source("adzuna")"""
        def decorator(klass): cls._discovery_sources[name] = klass; return klass
        return decorator
    # ... similar for other registries
```

### 6.5 Feature Flags

```yaml
# In config/settings.yaml
modules:
  discovery: on
  extraction: on
  matching: on
  immigration: on          # off → all jobs classified UNCLEAR, no blocking
  resume_optimizer: off    # Default off until stable
  cover_letter: on
  browser_automation: on
  accounts_sessions: on
  feedback_loop: on
  networking: off          # off → networking page shows "coming soon"
  interview_prep: off
  job_quality_checks: on
```

```python
# jobpilot/core/feature_flags.py

def is_enabled(module_name: str) -> bool:
    """Check if a module is enabled. Always safe to call."""
    ...
```

---

## 7. LLM Abstraction Layer

### 7.1 Interface Design

```python
# jobpilot/llm/base.py

class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: str = "", temperature: float = 0.1) -> str: ...
    @abstractmethod
    async def structured_output(self, prompt: str, schema: dict, system: str = "") -> dict: ...
    @abstractmethod
    async def classify(self, text: str, categories: list[str], system: str = "") -> str: ...
    @property
    @abstractmethod
    def provider_name(self) -> str: ...
    @property
    @abstractmethod
    def model_name(self) -> str: ...

class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
    @abstractmethod
    async def embed_one(self, text: str) -> list[float]: ...
```

### 7.2 Task-Level Routing (Hybrid Strategy)

The key insight: use cheap local embeddings for bulk ranking, LLM only for top-N re-ranking.

```yaml
llm:
  default_provider: ollama
  embedding_provider: ollama        # nomic-embed-text via Ollama (free, fast)
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.1:8b"            # Or mistral, qwen2.5 — config only
    embedding_model: "nomic-embed-text"
  gemini:
    model: NEEDS_CONFIG              # Model names live in config only, never in code
  anthropic:
    model: NEEDS_CONFIG
  openai:
    model: NEEDS_CONFIG

  task_routing:
    bulk_ranking: ollama_embeddings  # nomic-embed-text — fast, free, handles 200+ jobs
    shortlist_reranking: ollama      # LLM judges only top 20 from embedding ranking
    classification: ollama
    extraction: ollama
    cover_letter: ollama             # Upgrade to stronger model if quality is poor
    answer_generation: ollama
    immigration_analysis: ollama
    role_expansion: ollama           # RoleExpander uses LLM to suggest adjacent titles
    resume_optimizer: ollama
```

---

## 8. Module-by-Module Architecture

### 8.1 Discovery Layer & RoleExpander

#### RoleExpander (NEW — replaces static ROLE_ALIASES)

The RoleExpander uses the LLM to generate adjacent and stretch job titles from the user's preferred role families. Results are cached and shown to the user for one-time approval.

```
User provides: AI_ENGINEER, AI_AUTOMATION, SOLUTIONS_ENGINEER

LLM generates 3 tiers:
  EXACT:    "AI Engineer", "ML Engineer", "Generative AI Engineer"
  ADJACENT: "Applied AI Engineer", "Automation Developer", "AI Integration Specialist",
             "Technical AI Consultant", "AI Product Engineer"
  STRETCH:  "Technical Solutions Architect" (stretch — flagged as lower priority)

Cached in: config/role_expansions_cache.yaml
User sees diff and approves once. Never auto-updates without showing the diff.
```

```python
# discovery/role_expander.py

class RoleExpander(PipelineStage):
    stage_name = "role_expander"

    async def run(self, role_families: list[str]) -> RoleExpansion:
        """Return approved+cached or generate+show diff for approval."""
        cached = self._load_cache()
        if cached and not cached.needs_refresh:
            return cached
        expanded = await self.llm.complete(EXPANSION_PROMPT.format(roles=role_families))
        diff = self._compute_diff(cached, expanded)
        # Show diff in dashboard / CLI; block until user approves
        return RoleExpansion(tiers=expanded, approved=False, pending_review=True)
```

#### Discovery Sources (registered via PluginRegistry)

| Source | Method | Best For |
|--------|--------|---------|
| SearXNG | HTTP JSON API | General web search across all engines |
| Greenhouse | `boards.greenhouse.io` API | Startup / tech company ATS |
| Lever | `jobs.lever.co` API | Startup / tech company ATS |
| Adzuna | Free API (check coverage for target countries) | India, UK, Germany, Australia |
| Remotive | Public JSON API | Remote-first jobs globally |
| HN "Who's Hiring" | Monthly thread scraper | Tech startups, AI companies |
| Ashby | Public board scraping | AI/tech startups |
| SmartRecruiters | Public board API | Mid-large companies |
| Workable | Public job listings | Diverse company sizes |
| Career pages | BS4 scraping | Any company with a careers page |

> [!NOTE]
> LinkedIn and Naukri forbid automation in their ToS and are aggressive about banning accounts. Keep both strictly manual. Company ATS sites (Workday, Greenhouse, Lever) are different — you're applying on your own behalf.

#### Deduplication (3 levels, unchanged)
1. URL-level: exact URL → skip
2. Content-level: SHA256(`normalized_company + normalized_title + country`) → skip
3. Embedding similarity (optional): cosine distance < 0.1 → flag as near-duplicate

### 8.2 Extraction & Normalization

Core schema: `JobRecord` from `core/schemas.py`. No other module's types used.

New fields: `role_tier` (EXACT/ADJACENT/STRETCH from RoleExpander), `embedding_vector` (computed after extraction for bulk matching), `is_expired`, `is_ghost_job`, `quality_score`.

**Salary extraction:** regex handles "£80,000", "70-90k USD", "₹20 LPA", "competitive" → `UNKNOWN`. Never guesses.

### 8.3 Matching Engine (Hybrid Embedding + LLM)

**Two-stage pipeline:**

```
Stage 1 — Bulk Embedding Ranking (cheap, fast):
  - Embed job description + title using nomic-embed-text
  - Embed user profile summary using nomic-embed-text
  - Compute cosine similarity for all N jobs → ranked list
  - This handles 200+ jobs in seconds on CPU

Stage 2 — LLM Re-ranking (thorough, slower):
  - Take top 20-30 from embedding stage
  - LLM scores each against user profile on all dimensions
  - Returns MatchResult with full reasoning

Hard filters remain but applied AFTER LLM scoring, not before:
  - Java/Spring-primary with no Python/AI → SKIP (not soft penalty)
  - Pure DevOps/Linux/SysAdmin primary → SKIP
  - Immigration NOT_SUITABLE → SKIP

Experience gap → SOFT PENALTY (not hard filter):
  - Job requires 3 years, user has 1 → score penalty of -0.15 on experience dimension
  - Still appears in results with CONCERNS flag
  - Many postings say 3+ but hire at 1-2 years; user should decide
  - Configurable: matching.experience_gap_penalty (default 0.15 per excess year)
```

**Scoring dimensions (configurable weights):**

| Dimension | Default Weight |
|-----------|---------------|
| Role relevance (title + description) | 0.25 |
| Technical skill match | 0.25 |
| Experience match | 0.20 |
| Location/remote compatibility | 0.10 |
| Immigration feasibility | 0.10 |
| Seniority fit | 0.05 |
| Education match | 0.05 |

### 8.4 Immigration Intelligence Layer

> [!WARNING]
> **v2.0 Fix — Stale Thresholds:** All immigration salary thresholds are moved to `config/immigration_rules.yaml` with `source_date` and `verified: false` flag. They are never hardcoded in Python. The user must manually verify and set `verified: true` after checking the government source. Any `verified: false` threshold causes the country's classification confidence to be capped at LOW.

```yaml
# config/immigration_rules.yaml (excerpt)
countries:
  UK:
    route: "Skilled Worker Visa"
    min_salary_gbp: NEEDS_VERIFICATION   # Previously £26,200 — verify at gov.uk
    source_url: "https://www.gov.uk/skilled-worker-visa/your-job"
    source_date: "NEEDS_VERIFICATION"
    verified: false

  Germany:
    route: "EU Blue Card (§ 18g AufenthG)"
    min_salary_eur: NEEDS_VERIFICATION   # Previously €45,300 — verify at make-it-in-germany.com
    source_url: "https://www.make-it-in-germany.com/en/visa/kinds-of-visa/eu-blue-card"
    source_date: "NEEDS_VERIFICATION"
    verified: false

  Netherlands:
    route: "Highly Skilled Migrant (Kennismigrant)"
    min_salary_eur: NEEDS_VERIFICATION   # Verify at ind.nl
    source_url: "https://ind.nl/en/work/working_in_the_Netherlands/Pages/Highly-skilled-migrant.aspx"
    source_date: "NEEDS_VERIFICATION"
    verified: false
    # Add Canada, Australia, Singapore, UAE similarly
```

Classification logic is unchanged from v1.0. Evidence stored in `visa_evidence` table with disclaimer.

### 8.5 Resume Optimizer & Cover Letter Engine

#### Master Resume (Structured Data)

The resume is no longer a free-form DOCX. It is a **structured YAML** with tagged bullets. This is what makes the optimizer possible.

```yaml
# Inside ankita_profile.yaml — master_resume section
master_resume:
  summary: NEEDS_USER_INPUT
  employment:
    - employer: NEEDS_USER_INPUT
      title: NEEDS_USER_INPUT
      bullets:
        - text: NEEDS_USER_INPUT
          skills_demonstrated: [Python, LLMs, RAG]     # Tags for optimizer selection
          impact_level: HIGH                            # HIGH/MEDIUM/LOW — for ordering
        - text: NEEDS_USER_INPUT
          skills_demonstrated: [Make.com, Power Automate, REST APIs]
          impact_level: HIGH
  projects:
    - name: NEEDS_USER_INPUT
      bullets:
        - text: NEEDS_USER_INPUT
          skills_demonstrated: [AI Agents, Generative AI]
          impact_level: HIGH
```

#### Resume Optimizer Modes

Set per-session in the dashboard or CLI flag `--optimizer off/suggest/auto`:

| Mode | Behavior |
|------|---------|
| `OFF` (default until stable) | Base resume variant used unchanged |
| `SUGGEST` | Optimizer generates a diff of reordering/emphasis changes; user reviews and approves before file is generated |
| `AUTO` | Optimizer applies safe changes automatically; diff still shown at review screen |

**Optimizer constraints (enforced by safety.py):**
- May reorder bullets to surface most relevant skills first
- May select which bullets to include/exclude per resume variant
- May mirror the job's wording for skills the user already has
- **MUST NOT** add any skill, metric, claim, or responsibility not in the master resume
- Truth validator checks every optimized line against master resume before file generation

### 8.6 Document Renderer (Format Registry)

Replaces the ad-hoc `weasyprint` suggestion. Avoids Windows GTK dependency issues.

```python
# documents/format_detector.py

class FormatDetector:
    """
    Determine the best document format for a given application.
    Priority:
    1. Read the file input's `accept` HTML attribute — most reliable
    2. Scan job posting text for explicit format mentions (.docx, PDF, etc.)
    3. Default to PDF
    """
    def detect(self, page_html: str, job_description: str) -> str:
        accept_attr = self._extract_accept_attr(page_html)
        if accept_attr:
            return self._parse_accept_to_format(accept_attr)  # → "pdf" / "docx" / "txt"
        mentioned = self._scan_posting(job_description)
        if mentioned:
            return mentioned
        return "pdf"   # Default
```

```python
# documents/pdf_renderer.py — uses Playwright, already in the stack

class PDFRenderer(DocumentRenderer):
    async def render(self, resume_doc: ResumeDoc) -> bytes:
        # Render resume HTML template → page.pdf()
        # Single-column, ATS-friendly layout
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.set_content(self._render_html(resume_doc))
            pdf_bytes = await page.pdf(format="A4", margin={"top": "20mm", ...})
            return pdf_bytes
```

Format registry entries: `pdf` → PDFRenderer, `docx` → DOCXRenderer, `txt` → TXTRenderer. New formats added via `@PluginRegistry.register_renderer("md")`.

### 8.7 Application Answer Engine

Answer pipeline unchanged from v1.0, but now reads from corrected answer bank (all NEEDS_USER_INPUT until user verifies). Strict LLM prompt enforces no fabrication.

### 8.8 Browser Automation Layer

#### Playwright Agent Steps (updated for accounts)

```
1. Check site_accounts table for existing account + session
2. If session exists: load storage_state → verify still logged in
3. If no session: check site_accounts for credentials → run login flow
4. If no account: run account creation flow (creator.py)
5. Watch for CAPTCHA/2FA → HandoffManager.pause() → notify user → resume
6. Navigate to application URL
7. Detect ATS type via registry
8. Extract all form fields with labels, types, required flags
9. Map fields → user profile keys
10. Fill deterministic fields
11. Generate answers for text fields via answer_engine
12. Upload resume/cover letter in detected format
13. Flag ambiguous/legal/sensitive fields → NEEDS_USER_INPUT
14. Run pre-submission QA
15. Save audit screenshot + form snapshot
16. STOP → render review screen
17. Wait for explicit user approval (typed "SUBMIT")
18. Click submit ONLY after approval
```

#### HandoffManager (NEW)

```python
# browser/handoff_manager.py

class HandoffManager:
    HANDOFF_TRIGGERS = [
        "captcha", "recaptcha", "hcaptcha", "i am not a robot",
        "verify you are human", "unusual activity",
        "two-factor", "2fa", "verification code",
        "passport", "government id", "payment",
        "social security", "aadhaar", "pan card"
    ]

    async def check_and_pause_if_needed(self, page) -> bool:
        """
        Returns True if handoff was triggered and user has resumed.
        Returns False if no handoff needed.
        """
        trigger = await self._detect_trigger(page)
        if trigger:
            await self._notify_user(trigger)   # Windows toast + dashboard banner
            await self._pause_until_user_resumes()
            return True
        return False

    async def _notify_user(self, trigger: str):
        # win10toast notification
        # Dashboard banner set to HANDOFF_REQUIRED
        ...
```

**What remains manual (handoff triggers):**
- CAPTCHA / bot challenges
- 2FA prompts (phone/authenticator app)
- Unexpected "unusual activity" screens
- Anything asking for government ID, passport, or payment info

**What is automated:**
- Account registration (email + strong auto-generated password stored in keyring)
- Email verification link/OTP reading (email_verifier.py via IMAP)
- Login with saved credentials
- Session persistence via storage_state

### 8.9 Accounts & Sessions (Credential Vault + Email Verifier)

#### Credential Vault

```python
# accounts/vault.py

import keyring

VAULT_NAMESPACE = "jobpilot"

class CredentialVault:
    def store_password(self, site_url: str, username: str, password: str):
        key = f"{VAULT_NAMESPACE}:{site_url}:{username}"
        keyring.set_password(VAULT_NAMESPACE, key, password)

    def get_password(self, site_url: str, username: str) -> Optional[str]:
        key = f"{VAULT_NAMESPACE}:{site_url}:{username}"
        return keyring.get_password(VAULT_NAMESPACE, key)

    def generate_strong_password(self) -> str:
        """Generate a unique strong password. Never reuse across sites."""
        import secrets, string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
        return ''.join(secrets.choice(alphabet) for _ in range(24))
```

#### Email Verifier

```python
# accounts/email_verifier.py

class EmailVerifier:
    """
    Uses a dedicated job-search inbox (not the user's main email).
    Reads verification emails via IMAP. Extracts links or OTPs.
    Credentials stored in keyring, not .env.
    """
    async def wait_for_verification(self, sender_domain: str, timeout_seconds=120) -> str:
        """
        Poll inbox for email from sender_domain.
        Return verification link or OTP string.
        """
        ...
```

> [!NOTE]
> Use a **dedicated email address** for job applications — not your main personal inbox. This limits exposure and simplifies IMAP monitoring. A free Gmail address works. Store the app password in keyring, never in `.env`.

#### Session Manager

```python
# accounts/session_manager.py

class SessionManager:
    """Saves and loads Playwright browser context storage_state per site."""
    sessions_dir: Path  # data/sessions/ — OUTSIDE OneDrive, excluded from git

    async def save_session(self, context, site_url: str, username: str):
        path = self.sessions_dir / f"{self._site_key(site_url)}_{username}.json"
        await context.storage_state(path=str(path))
        # Update site_accounts table with session_file path

    async def load_session(self, context, site_url: str, username: str) -> bool:
        path = self.sessions_dir / f"{self._site_key(site_url)}_{username}.json"
        if path.exists():
            await context.add_init_script(...)  # restore storage state
            return True
        return False
```

### 8.10 Human Review & Submission Gate

Review screen content (updated to include optimizer status and audit trail):

```
┌──────────────────────────────────────────────────────────┐
│  JobPilot AI — Application Review                        │
│  Job: {title} at {company}           [{match_score}%]    │
│  Resume: ai_engineer_v3.pdf          [Optimizer: SUGGEST] │
├──────────────────────────────────────────────────────────┤
│  FILLED FIELDS:                                          │
│  ✅ Full Name: ...                   [profile]           │
│  ✅ Email: ...                       [profile]           │
│  ✅ Work Authorization: Yes (India)  [user_verified]     │
│  ✅ Years Python Experience: ...     [user_verified]     │
│  ✅ Resume: ai_engineer_v3.pdf       [pdf]               │
│  ⚠️  Notice Period: ...              [needs_review]      │
├──────────────────────────────────────────────────────────┤
│  OPTIMIZER DIFF (approve/reject):                        │
│  [SUGGEST MODE — review changes before file is created]  │
│  + Moved Python/LLM bullets above Make.com bullets       │
│  + Highlighted RAG in summary line                       │
├──────────────────────────────────────────────────────────┤
│  QA REPORT:                                              │
│  ✅ All required fields filled                           │
│  ✅ No contradictions detected                           │
│  ⚠️  Notice period needs confirmation                   │
├──────────────────────────────────────────────────────────┤
│  Type "SUBMIT" to submit or "CANCEL" to abort:           │
└──────────────────────────────────────────────────────────┘
```

**Hard block conditions (unchanged from v1.0 + new):**
- Required field is `NEEDS_USER_INPUT`
- International work auth not `user_verified`
- QA detected contradiction or unsupported claim
- User has not typed "SUBMIT"
- Optimizer diff not reviewed (in SUGGEST mode)

### 8.11 Feedback Loop & Match Calibration

```python
# matching/feedback.py

class FeedbackLoop:
    """Thumbs up/down on any matched job adjusts matching weights."""

    async def record_feedback(self, job_id: str, feedback: str):
        # Store in match_feedback table
        # Compute weight delta based on which dimensions were strong/weak
        # Apply delta to matching weights (with bounds to prevent runaway drift)
        # Weights are bounded: 0.05 <= any_weight <= 0.40

    async def calibrate(self, labeled_test_set: list[dict]) -> dict:
        """
        Measure match quality against a small labeled set (jobs marked GOOD/BAD manually).
        Returns precision, recall, and F1 per role family.
        """
```

### 8.12 Networking Module

```python
# networking/message_gen.py

class NetworkingMessageGen(PipelineStage):
    """
    Generates recruiter outreach and referral request messages.
    Only enabled when modules.networking = on.
    All messages grounded in verified profile; never fabricates connections or claims.
    """
    MESSAGE_TYPES = ["linkedin_connection", "recruiter_email", "referral_request", "follow_up"]
```

### 8.13 Interview Prep Module

```python
# interview/prep.py

class InterviewPrep(PipelineStage):
    """
    For each application:
    - Generate likely interview questions from job description
    - Generate STAR-method answer outlines using verified profile facts
    - Generate company research notes from job posting
    Only enabled when modules.interview_prep = on.
    """
```

### 8.14 Job Quality & Freshness Checks

```python
# extraction/quality_checker.py

class JobQualityChecker(PipelineStage):
    """
    Flags:
    - Expired postings (date_posted older than 60 days, or explicit "position filled" text)
    - Ghost jobs (identical posting reappeared multiple times over months with no changes)
    - Suspected scam (no company domain, unrealistic salary, grammatical anomalies)
    - Missing critical fields (no salary, no location, no description)
    Returns quality_score (0-1) and specific flags stored on JobRecord.
    """
```

### 8.15 Streamlit Dashboard

**Pages (expanded):**

| Page | Purpose |
|------|---------|
| 🔍 Discovery | Run search, today's jobs, role expansion approval |
| ⭐ Shortlist | Top matches, sorted by score, with feedback thumbs |
| 🌍 International | Immigration evidence, classified by VisaStatus |
| 🇮🇳 India Jobs | India-only jobs |
| 📝 Applications | Full tracker: status, timeline, submitted docs |
| 📅 Tracker | Follow-ups, reminders, status changes |
| 🤝 Networking | Recruiter/referral message drafts (off by default) |
| 🎯 Interview Prep | Per-job question sets (off by default) |
| 👤 Profile | Edit profile, verify answer bank entries |
| ⚙️ Settings | LLM, feature flags, optimizer mode, search config |

**Session-level optimizer toggle** in sidebar: `OFF` / `SUGGEST` / `AUTO` — persists for the session, reverts to config default on restart.

---

## 9. Phase-by-Phase Implementation Plan

### Phase 0: Core Contracts, Registry & Feature Flags

> **This phase MUST complete before any other phase begins. It sets the rules that prevent modules from becoming entangled.**

**Deliverables:**
- `jobpilot/core/schemas.py` — all shared Pydantic schemas (empty body OK, just structure)
- `jobpilot/core/registry.py` — PluginRegistry with decorators
- `jobpilot/core/pipeline.py` — PipelineStage base class
- `jobpilot/core/feature_flags.py` — feature flag accessor
- `jobpilot/core/safety.py` — SafetyViolation + all assertion functions
- `alembic.ini` + `jobpilot/database/alembic/env.py` — Alembic initialized
- `config/settings.yaml` — full template including `modules:` section
- `config/immigration_rules.yaml` — all countries with NEEDS_VERIFICATION placeholders
- `.env.example`, `.gitignore`
- `tests/contract/` — 4 contract test files (validate output schemas)

**Tests:** All 4 contract tests pass against mock data

**Completion criteria:** `pytest tests/contract/ -v` passes. No module-to-module imports exist anywhere.

---

### Phase 1: Project Foundation & Database

**Deliverables:**
- Full directory structure (all `__init__.py`)
- `requirements.txt` with pinned versions
- `jobpilot/database/models.py` — all 12 SQLAlchemy models
- `jobpilot/database/repository.py`
- `jobpilot/profiles/loader.py` — profile loaded from `settings.yaml:user.profile_path`
- `jobpilot/profiles/answer_bank.py`
- Profile YAML template (all NEEDS_USER_INPUT filled by user before Phase 7)
- `scripts/setup_db.py` — initialize DB, run Alembic migrations

**CLI:**
```bash
python scripts/setup_db.py
# Database initialized at: C:\Users\Ankita\Desktop\JobPilotData\jobpilot.db  ← outside OneDrive
# Alembic migrations applied: 1 (initial schema)
# User profile loaded from: jobpilot/profiles/ankita_profile.yaml
# Verified facts: 5 | NEEDS_USER_INPUT: 18
```

**Tests:** `test_database.py` (all 12 tables, insert/retrieve/update)

**Completion criteria:** All tables created; profile loads; NEEDS_USER_INPUT fields detected; Alembic migration runs cleanly.

---

### Phase 2: SearXNG Job Discovery

**Deliverables:**
- `jobpilot/discovery/base.py`
- `jobpilot/discovery/searxng.py` (registered via PluginRegistry)
- `jobpilot/discovery/query_builder.py`
- `jobpilot/discovery/deduplicator.py`
- `jobpilot/discovery/role_expander.py`
- `jobpilot/llm/base.py`, `ollama_provider.py`, `factory.py`
- `scripts/run_discovery.py`

**SearXNG setup:**
```bash
docker run -d -p 8080:8080 searxng/searxng
```

**CLI:**
```bash
python scripts/run_discovery.py --countries India Germany --roles AI_ENGINEER
# RoleExpander: Generated 12 adjacent titles. Review in dashboard before proceeding? [y/n]
# Running 18 queries across SearXNG...
# Found 62 job URLs | 39 new | 23 duplicates skipped
# Search run: run_20260929_123000
```

**Tests:** `test_deduplication.py`, `test_role_expander.py`, `test_searxng.py` (mocked)

---

### Phase 3: Extraction & Normalization

**Deliverables:**
- `jobpilot/extraction/html_extractor.py`
- `jobpilot/extraction/api_extractor.py`
- `jobpilot/extraction/normalizer.py`
- `jobpilot/extraction/quality_checker.py`
- `jobpilot/discovery/greenhouse.py`, `lever.py`, `adzuna.py`, `remotive.py`

**Completion criteria:** 80%+ of discovered jobs have title/company/country/description; all pass `JobRecord` Pydantic validation; quality scores computed.

---

### Phase 4: Matching Engine

**Deliverables:**
- `jobpilot/matching/engine.py` — 2-stage: embeddings → LLM rerank
- `jobpilot/matching/embedder.py` — nomic-embed-text via Ollama
- `jobpilot/matching/scorer.py`
- `jobpilot/matching/filters.py` — soft penalty for experience gap
- `scripts/run_matching.py`

**Completion criteria:** Every job gets `match_score` + `match_status`; experience gap applies penalty not rejection; hard filters reject Java/Spring-primary and DevOps-primary roles; top 10 matches are intuitive.

---

### Phase 5: Immigration Evidence Layer

**Deliverables:**
- `jobpilot/immigration/` full module
- User prompted to verify `immigration_rules.yaml` thresholds against government sources

**Completion criteria:** India = `INDIA`; international classified with evidence; no `CONFIRMED` without real source; no hardcoded salary thresholds.

---

### Phase 6: Resume Optimizer & Cover Letter Engine

**Deliverables:**
- `jobpilot/applications/resume_master.py` — loads structured YAML master resume
- `jobpilot/applications/resume_optimizer.py` — OFF/SUGGEST/AUTO modes
- `jobpilot/applications/resume_selector.py`
- `jobpilot/applications/cover_letter_gen.py`
- `jobpilot/documents/` — full format registry with PDFRenderer (Playwright) + DOCXRenderer
- All Jinja2 templates

**Default:** `resume_optimizer: off` in settings. Toggle on per session.

**Completion criteria:** Cover letters generated for 3 test jobs; PDF generated via Playwright (no weasyprint); optimizer diff shown before file generation in SUGGEST mode; no fabricated content in any output.

---

### Phase 7: Application Answer Engine

**Deliverables:** `jobpilot/applications/answer_engine.py`

**Critical tests:**
```python
answer("Years of Python experience?")  # → user_verified value OR NEEDS_USER_INPUT
answer("Describe Kubernetes experience?")  # → NEEDS_USER_INPUT (not in profile)
answer("Led a team of 10?")  # → NEEDS_USER_INPUT
answer("Are you authorized to work in India?")  # → "Yes, I am authorized..."
answer("Are you authorized to work in Germany?")  # → NEEDS_USER_INPUT_PER_JOB
```

**Completion criteria:** 100% answers are verified or NEEDS_USER_INPUT. Zero fabrication.

---

### Phase 8: Playwright Form Filling

**Deliverables:**
- `jobpilot/browser/agent.py`
- `jobpilot/browser/field_mapper.py`
- `jobpilot/browser/form_filler.py`
- `jobpilot/browser/form_types.py`
- ATS handlers registered via PluginRegistry (Greenhouse, Lever, Workday, custom)

**Completion criteria:** Fills Greenhouse test application; format-detected PDF uploaded; NEEDS_USER_INPUT fields highlighted; review screen renders correctly.

---

### Phase 8b: Accounts & Sessions

**Deliverables:**
- `jobpilot/accounts/vault.py` — keyring integration
- `jobpilot/accounts/creator.py` — automated account creation
- `jobpilot/accounts/login.py` — automated login
- `jobpilot/accounts/email_verifier.py` — IMAP verification
- `jobpilot/accounts/session_manager.py` — storage_state persistence
- `jobpilot/browser/handoff_manager.py` — CAPTCHA/2FA detection + user notification
- `site_accounts` table (already in schema)

**Completion criteria:** Successfully creates account and logs into a test Workday site; session persisted; CAPTCHA triggers pause + Windows toast; no passwords stored outside keyring.

---

### Phase 9: Human Review + Submission Gate

**Deliverables:**
- `jobpilot/applications/qa_checker.py`
- `jobpilot/browser/review_screen.py`
- `jobpilot/browser/submission_gate.py`
- `jobpilot/tracker/audit_trail.py` — screenshot + form snapshot at submission

**Completion criteria:** Submission blocked without typed "SUBMIT"; QA catches contradictions; optimizer diff shown and approved in SUGGEST mode; audit files saved; `user_approved=1` set only after approval.

---

### Phase 10: Feedback Loop, Tracker & Additional Modules

**Deliverables:**
- `jobpilot/matching/feedback.py`, `calibration.py`
- `jobpilot/tracker/follow_ups.py`, `status_updater.py`
- `jobpilot/networking/message_gen.py` (feature-flagged off by default)
- `jobpilot/interview/prep.py`, `company_notes.py` (feature-flagged off by default)

---

### Phase 11: Streamlit Dashboard

**Deliverables:** `jobpilot/dashboard/` — all 10 pages + components

**Run:**
```bash
streamlit run jobpilot/dashboard/app.py
```

**Completion criteria:** All pages load; optimizer toggle works per session; feedback thumbs update match weights; immigration evidence visible; handoff status visible.

---

## 10. Configuration System

### `config/settings.yaml` — Full Template

```yaml
app:
  name: "JobPilot AI"
  version: "0.2.0"
  data_dir: "C:/Users/Ankita/Desktop/JobPilotData"  # OUTSIDE OneDrive
  log_level: "INFO"

user:
  profile_path: "jobpilot/profiles/ankita_profile.yaml"   # Configurable — not hardcoded

modules:
  discovery: on
  extraction: on
  matching: on
  immigration: on
  resume_optimizer: off        # Toggle per session; default off until stable
  cover_letter: on
  browser_automation: on
  accounts_sessions: on
  feedback_loop: on
  networking: off
  interview_prep: off
  job_quality_checks: on

searxng:
  base_url: "http://localhost:8080"
  engines: [google, bing, duckduckgo]
  max_results_per_query: 20
  request_delay_seconds: 2
  timeout_seconds: 30

discovery:
  target_countries: [India, Germany, Netherlands, UK, Canada, Australia, Singapore, UAE]
  target_role_families: [AI_ENGINEER, AI_AUTOMATION, AI_SOLUTIONS_ENGINEER, PRODUCT_SYSTEMS, CRM_AUTOMATION, DATA_ANALYTICS, SOLUTIONS_ENGINEER]
  remote_preference: ANY
  max_jobs_per_run: 200
  deduplicate: true
  rate_limit_requests_per_minute: 20     # Be polite

llm:
  default_provider: ollama
  embedding_provider: ollama
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.1:8b"
    embedding_model: "nomic-embed-text"
  gemini:
    model: NEEDS_CONFIG     # Set only if user opts in
  anthropic:
    model: NEEDS_CONFIG
  openai:
    model: NEEDS_CONFIG
  task_routing:
    bulk_ranking: ollama_embeddings
    shortlist_reranking: ollama
    classification: ollama
    extraction: ollama
    cover_letter: ollama
    answer_generation: ollama
    immigration_analysis: ollama
    role_expansion: ollama
    resume_optimizer: ollama

matching:
  weights:
    role_relevance: 0.25
    technical_skill: 0.25
    experience: 0.20
    location_remote: 0.10
    immigration: 0.10
    seniority: 0.05
    education: 0.05
  min_match_score_shortlist: 0.55
  experience_gap_penalty: 0.15         # Per excess year (soft penalty, not hard filter)
  embedding_top_n: 30                  # LLM reranks only these top N from embedding stage

browser:
  headless: false
  slow_mo_ms: 100
  screenshot_on_review: true
  default_browser: chromium
  rate_limit_actions_per_minute: 30

resume_optimizer:
  default_mode: "off"                  # off/suggest/auto
  session_override: true               # Allow per-session toggle in dashboard

dashboard:
  port: 8501
  theme: dark
```

---

## 11. Safety & Ethics Rules (Hard-coded)

```python
# jobpilot/core/safety.py

class SafetyViolation(Exception):
    pass

def assert_no_fabrication(answer: str, source: str, profile: dict) -> None:
    """Every claim must be verifiably grounded in profile."""
    if source == "generated":
        # LLM self-check: list all claims → verify each exists in profile
        ...

def assert_user_approved(application_id: str, db) -> None:
    app = db.get_application(application_id)
    if not app.user_approved:
        raise SafetyViolation(f"Application {application_id} not user-approved. Submission blocked.")

def assert_no_needs_user_input_in_required_fields(answers: list) -> None:
    for a in answers:
        if a.is_required and a.answer_value == "NEEDS_USER_INPUT":
            raise SafetyViolation(f"Required field '{a.field_label}' unresolved.")

def assert_no_legal_auto_answer(field_label: str, answer_source: str) -> None:
    SENSITIVE = ["felony", "criminal", "background", "legally authorized",
                 "work authorization", "disability", "veteran", "accommodation",
                 "salary history", "previous compensation", "passport", "government id"]
    if any(p in field_label.lower() for p in SENSITIVE):
        if answer_source != "user_verified":
            raise SafetyViolation(f"Sensitive field '{field_label}' requires user_verified source.")

def assert_optimizer_no_new_claims(original: ResumeDoc, optimized: ResumeDoc) -> None:
    """Optimizer must never introduce text not in original master resume."""
    ...

def assert_no_password_in_code(value: str) -> None:
    """Called before any string is written to DB, YAML, or logs."""
    if len(value) > 8 and any(c in value for c in "!@#$%^&*"):
        # Heuristic: possible password being logged — raise warning
        raise SafetyViolation("Possible credential being written to non-vault storage.")
```

---

## 12. Testing Strategy

### Coverage Targets

| Module | Test File | Target |
|--------|-----------|--------|
| Core contracts | `tests/contract/` | 100% |
| Database CRUD | `test_database.py` | 90% |
| Deduplication | `test_deduplication.py` | 100% |
| Role expander | `test_role_expander.py` | 85% |
| Extraction | `test_extraction.py` | 85% |
| Matching engine | `test_matching.py` | 85% |
| Immigration classifier | `test_immigration.py` | 90% |
| Answer engine | `test_answer_engine.py` | 95% |
| Truth validation / safety | `test_truth_validation.py` | 100% |
| Resume optimizer | `test_resume_optimizer.py` | 95% |
| Document renderer | `test_document_renderer.py` | 85% |
| Browser field mapping | `test_browser_mapping.py` | 80% |
| Handoff manager | `test_handoff_manager.py` | 90% |
| QA checker | `test_qa_checker.py` | 100% |

### Critical Test Cases

```python
# test_truth_validation.py
def test_no_fabrication_in_cover_letter(): ...
def test_needs_user_input_blocks_submission(): ...
def test_international_work_auth_requires_user_verified(): ...
def test_experience_not_inflated(): ...
def test_unverified_skill_returns_needs_user_input(): ...
def test_india_job_no_sponsorship_required(): ...
def test_submission_gate_blocks_without_approval(): ...
def test_answer_bank_all_needs_user_input_until_verified(): ...

# test_resume_optimizer.py
def test_optimizer_off_returns_base_resume_unchanged(): ...
def test_optimizer_does_not_add_new_claims(): ...
def test_optimizer_suggest_generates_diff(): ...
def test_optimizer_truth_validator_catches_fabrication(): ...

# test_handoff_manager.py
def test_captcha_triggers_pause(): ...
def test_resume_after_handoff(): ...

# test_document_renderer.py
def test_pdf_default_when_no_accept_attr(): ...
def test_docx_when_accept_attr_specifies_docx(): ...
def test_format_detector_reads_posting_text(): ...
```

---

## 13. Security Guidelines

### Secrets Management

```bash
# .env.example — never commit .env
SEARXNG_BASE_URL=http://localhost:8080
DB_PATH=C:/Users/Ankita/Desktop/JobPilotData/jobpilot.db
SESSIONS_DIR=C:/Users/Ankita/Desktop/JobPilotData/sessions
# Optional — only if user opts into remote LLM
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
# Job application email (dedicated inbox, not main email)
JOB_EMAIL_ADDRESS=
JOB_EMAIL_IMAP_SERVER=imap.gmail.com
# IMAP app password stored in keyring — NOT HERE
```

### `.gitignore` must include:
```
.env
data/
*.db
sessions/
data/resumes/
data/cover_letters/
data/audit/
jobpilot/profiles/*.yaml    # Contains PII
config/role_expansions_cache.yaml
__pycache__/
*.pyc
.pytest_cache/
```

### Data Safety

- `data/` directory must live **outside OneDrive** to prevent SQLite corruption
- `sessions/` contains Playwright login tokens — treat as sensitive as passwords
- `ankita_profile.yaml` contains PII — never push to any repository
- Logs must never contain profile data, passwords, or session tokens

---

## 14. Key Implementation Decisions & Risks

### Design Decisions (v2.0)

| Decision | Rationale |
|----------|-----------|
| Phase 0 (core contracts) before all feature phases | Prevents module entanglement; change one module without breaking others |
| Embedding-first, LLM-second matching | Embeddings handle 200+ jobs cheaply; LLM only re-ranks top 30 |
| Experience gap = soft penalty, not hard filter | Many 3-year postings hire at 1-2 years; user should decide |
| RoleExpander with user-approved cache | Smarter than static aliases; user stays in control of scope |
| Resume as structured YAML, not free DOCX | Enables optimizer; without structure, optimizer would be unsafe |
| Playwright for PDF, not weasyprint | Avoids Windows GTK dependency; already in stack |
| Keyring for passwords, not .env | OS-encrypted; no credential appears in any file |
| data/ outside OneDrive | Prevents SQLite file corruption from cloud sync |
| Alembic for migrations | Schema changes don't wipe data |

### Risk Register (v2.0)

| Risk | Severity | Mitigation |
|------|----------|-----------|
| OneDrive SQLite corruption | **CRITICAL** | Move data/ outside OneDrive before first run |
| Answer bank prefilling wrong values | **HIGH** | All entries NEEDS_USER_INPUT; user verifies each |
| Stale immigration thresholds | **HIGH** | immigration_rules.yaml requires manual verify; LOW confidence until verified |
| Optimizer introducing fabrication | **HIGH** | truth_validator checks every line; SafetyViolation on any new claim |
| Account ban from automation | **MEDIUM** | Human-speed delays, rate limits; avoid LinkedIn/Naukri |
| CAPTCHA not detected → form submitted | **HIGH** | HandoffManager scans page text proactively before every action |
| Session token corruption | **MEDIUM** | Validate session before use; gracefully fall back to login |
| Ollama model quality for nuanced matching | **MEDIUM** | Embedding pre-ranking; LLM only judges top N where quality matters more |
| SearXNG returning few job-specific results | **MEDIUM** | Supplemented by Greenhouse, Lever, Adzuna, Remotive APIs |

---

## 15. Dependency List (`requirements.txt`)

```
# Core
httpx==0.27.*
pydantic==2.7.*
python-dotenv==1.0.*
pyyaml==6.0.*
click==8.1.*
rich==13.*

# Database
sqlalchemy==2.0.*
alembic==1.13.*

# HTML Parsing
beautifulsoup4==4.12.*
lxml==5.*

# LLM (local)
ollama==0.3.*

# Browser Automation + PDF
playwright==1.45.*

# Dashboard
streamlit==1.38.*

# Scheduling
apscheduler==3.10.*

# Resume Generation
python-docx==1.1.*
jinja2==3.1.*

# Credential Vault
keyring==25.*

# Windows Notifications
win10toast==0.9.*         # Windows only

# Testing
pytest==8.*
pytest-asyncio==0.23.*
pytest-mock==3.14.*

# Async
anyio==4.*

# Logging
loguru==0.7.*
```

---

## 16. Execution Checklist for Each Phase

**Before Phase 0:**
- [ ] Create `C:\Users\Ankita\Desktop\JobPilotData\` (or another folder OUTSIDE OneDrive)
- [ ] Exclude this folder from OneDrive sync

**Before starting any subsequent phase:**
- [ ] Phase 0 contract tests pass: `pytest tests/contract/ -v`
- [ ] Previous phase all tests pass: `pytest tests/ -v`
- [ ] DB initialized and Alembic migrations applied
- [ ] `config/settings.yaml` has correct `app.data_dir` (pointing outside OneDrive)
- [ ] Phase 2+: SearXNG running at configured URL
- [ ] Phase 4+: Ollama running (`ollama serve`), `llama3.1:8b` and `nomic-embed-text` pulled
- [ ] Phase 8+: `playwright install chromium` completed
- [ ] Phase 8b+: Dedicated job-application email address created; IMAP app password in keyring

**After completing each phase:**
- [ ] Full test suite passes: `pytest tests/ -v`
- [ ] No hardcoded credentials anywhere
- [ ] No module imports another module's internals (grep: `from jobpilot.matching import` inside `discovery/` etc.)
- [ ] Feature flag for new module added to `settings.yaml`
- [ ] `README.md` updated with new run instructions
- [ ] `NEEDS_USER_INPUT` fields surfaced (not silently defaulted)

---

## Quick Start (After Phase 1 + 2)

```bash
# 1. Create data directory OUTSIDE OneDrive
mkdir "C:\Users\Ankita\Desktop\JobPilotData"
mkdir "C:\Users\Ankita\Desktop\JobPilotData\sessions"

# 2. Enter project directory
cd "C:\Users\Ankita\OneDrive\Documents\JobPilotAI"

# 3. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 5. Pull Ollama models
ollama pull llama3.1:8b
ollama pull nomic-embed-text

# 6. Set up environment
copy .env.example .env
# Edit .env: set DB_PATH and SESSIONS_DIR to C:\Users\Ankita\Desktop\JobPilotData\...

# 7. Fill your profile (CRITICAL — before Phase 7 can run)
# Edit jobpilot/profiles/ankita_profile.yaml
# Replace NEEDS_USER_INPUT with your actual verified data
# Verify answer_bank.yaml entries (set actual values for years_of_experience)

# 8. Verify immigration rules (IMPORTANT)
# Open config/immigration_rules.yaml
# Check each country's threshold against the linked government source
# Set verified: true for each confirmed threshold

# 9. Initialize database
python scripts/setup_db.py

# 10. Start SearXNG
docker run -d -p 8080:8080 searxng/searxng

# 11. Run Phase 0 tests first
pytest tests/contract/ -v

# 12. Run discovery
python scripts/run_discovery.py --countries India Germany --roles AI_ENGINEER

# 13. Launch dashboard
streamlit run jobpilot/dashboard/app.py
```

---

> **Note to Execution Agent:**
> 1. Start with **Phase 0 only** — core contracts, registry, and feature flags. No feature code until Phase 0 tests pass.
> 2. Then **Phase 1** — database and profile loading.
> 3. Then **Phase 2** — discovery.
> 4. After each phase: run all tests, fix failures, never skip.
> 5. Ankita's profile YAML needs user input for email, phone, LinkedIn, GitHub, employer, institution, employment history, salary expectations, notice period, and all `years_of_experience` entries in the answer bank before Phase 7 can function.
> 6. Immigration thresholds in `config/immigration_rules.yaml` need manual verification against government websites before Phase 5 can report HIGH confidence.

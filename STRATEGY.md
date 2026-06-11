# Job Application Pipeline — Strategy

## Overview

A semi-automated pipeline that collects job offers, tailors application documents per offer, submits applications, and maintains a structured record of every application sent.

The pipeline is designed to be **supervised, not fully autonomous**: a human approves each tailored CV/cover letter before submission. Full automation of the submission step is treated as optional and job-board-specific.

---

## Sophie's Profile & Target Map

### Core expertise (from CV)
- **EU digital & tech law** — AI Act, DSA, DMA, GDPR, IT services law (currently at Milieu, previously DPO at Hosteur France)
- **EU policy & lobbying** — legislative monitoring, policy strategy, EU liaison (Belgian Bar Association)
- **EU institutional law** — competition, trademark, EU staff law (General Court traineeship)
- **Research for EU institutions** — three publications for the European Parliament and Commission
- **Languages** — French (native), English (fluent), Italian (fluent) — trilingual in the three main EU working languages

### Target roles (priority order)

| Role | Why it fits |
|---|---|
| **Tech / Digital Regulatory Affairs** | Direct match — AI Act, DSA, DMA compliance is her current daily work |
| **Government / Public Affairs Officer** | Lobbying + legislative monitoring at Bar Association; trilingual |
| **Policy Officer (EU institutions / agencies)** | Strong institutional background + publications for EP and Commission |
| **Data Protection Officer (DPO)** | Already held the title; GDPR + health data hands-on experience |
| **Compliance Officer — AI / DSA / DMA** | Cutting-edge specialisation; Saarland AI law summer school |
| **EU Affairs Consultant** | Public affairs firms are a natural step from Milieu-style consulting |
| **Legal Counsel — EU Digital Law** | Law firms with EU regulatory practice (Bird & Bird, Fieldfisher, etc.) |
| **AI Governance / Policy Specialist** | Publications on AI/workplace; growing field with few qualified specialists |

### Target industries

| Industry | Key employers in Brussels / EU |
|---|---|
| **Big Tech platforms** | Google, Meta, Apple, Microsoft, Amazon, TikTok, Spotify (all have Brussels policy teams) |
| **Telecom** | Proximus, Orange, Vodafone, Deutsche Telekom, GSMA |
| **EU Institutions & agencies** | DG CONNECT, DG JUST, ENISA, EDPS, EDPB, European Parliament |
| **Public affairs firms** | Fleishman-Hillard, Hague Corporate Affairs, Kreab, Burson, FTI Consulting, APCO |
| **Law firms (EU digital practice)** | Bird & Bird, Linklaters, Fieldfisher, Taylor Wessing, Freshfields, Loyens & Loeff |
| **Think tanks / civil society** | Bruegel, ECIPE, Access Now, AlgorithmWatch, Future of Life Institute |
| **Industry associations** | DigitalEurope, CCIA Europe, GSMA, BusinessEurope |
| **Consulting (regulatory)** | Deloitte (public sector), PwC Regulatory, EY Law, KPMG EU policy |
| **Healthcare / pharma** | Health data expertise; EHDS (European Health Data Space) is active now |
| **Financial services** | AI Act financial sector compliance; data governance under DORA/GDPR |

### Search keywords (for collector config)

```yaml
primary:
  - "regulatory affairs" + (EU OR digital OR tech OR AI)
  - "government affairs" + (technology OR platform OR digital)
  - "public affairs" + (technology OR policy)
  - "policy officer" + (digital OR AI OR data OR tech)
  - "compliance officer" + (GDPR OR "AI Act" OR DSA OR DMA)
  - "data protection officer"
  - "EU affairs" + (technology OR digital)
  - "AI governance"
  - "DSA compliance" OR "DMA compliance" OR "AI Act compliance"
  - "legal counsel" + (regulatory OR digital OR EU)

secondary:
  - "legal researcher" + (EU OR digital OR policy)
  - "EU law" + (technology OR digital OR data)
  - "competition law" + EU
  - "privacy counsel" OR "privacy officer"
  - "tech policy" + (Brussels OR EU OR Europe)
```

### Geography
**Germany (Berlin / Munich / Hamburg / Frankfurt) — top priority** · Belgium (Brussels) · France (Paris) · Remote EU acceptable

> Note: Sophie's CV lists no German, which is a real constraint for many German roles. The collector should flag whether a posting explicitly requires German. Roles at EU-facing organisations, Big Tech, international law firms, and think tanks in Germany regularly operate in English and are the best fit.

---

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌───────────────────┐
│  1. COLLECTOR   │───▶│  2. DATABASE     │───▶│  3. ADAPTER       │
│  Scrapes job    │    │  SQLite — jobs,  │    │  Claude tailors   │
│  boards / RSS   │    │  contacts,       │    │  CV + cover       │
│  on a schedule  │    │  applications    │    │  letter per offer │
└─────────────────┘    └──────────────────┘    └────────┬──────────┘
                                                         │
                                              human review / approval
                                                         │
                                               ┌─────────▼──────────┐
                                               │  4. APPLICATOR     │
                                               │  Sends application │
                                               │  (email or browser │
                                               │  automation)       │
                                               └─────────┬──────────┘
                                                         │
                                               ┌─────────▼──────────┐
                                               │  5. TRACKER        │
                                               │  Appends row to    │
                                               │  applications.csv  │
                                               └────────────────────┘
```

---

## Phase 1 — Job Collector

**Goal:** Discover new job offers daily and store raw data.

**Sources (priority-ranked for Sophie's profile):**

| Source | URL | Why |
|---|---|---|
| **EurActiv Jobs** | jobs.euractiv.com | Premier EU affairs job board; policy/regulatory roles dominate |
| **Eurobrussels** | eurobrussels.com | Brussels-specific EU affairs; daily new postings |
| **LinkedIn Jobs** | linkedin.com/jobs | Essential; company-direct postings + Easy Apply |
| **IAPP Job Board** | iapp.org/job-board | Data protection / privacy roles globally |
| **EU Institutions (EPSO)** | epso.europa.eu | Official EU civil servant + contract agent posts |
| **EU Agency career pages** | ENISA, EDPS, EDPB, EBA, ESMA | Direct scrape; not always on LinkedIn |
| **Welcome to the Jungle** | welcometothejungle.com | Strong in France; good for Paris-based roles |
| **Indeed Belgium / France / Germany** | indeed.be / .fr / .de | Broad coverage; catches SME postings |
| **StepStone Germany** | stepstone.de | Largest German job board; strong in legal/policy |
| **XING Jobs** | xing.com/jobs | Germany's LinkedIn equivalent; good for mid-senior roles |
| **Interamt** | interamt.de | German public sector / government jobs |
| **Company career pages** | See target employer list above | Direct scrape for Big Tech Brussels/Berlin policy teams |

**RSS feeds available (free, no scraping needed):**
- EurActiv Jobs RSS
- Eurobrussels RSS
- EPSO vacancy RSS
- StepStone RSS (per search query)

**Germany-specific target employers (Berlin / Munich):**
- Big Tech EU policy hubs: Google (Berlin), Twitter/X (Hamburg), Amazon (Berlin), Zalando (Berlin), SAP (Walldorf)
- Think tanks: Stiftung Neue Verantwortung / SNV (Berlin), Alexander von Humboldt Institut für Internet und Gesellschaft (Berlin), AlgorithmWatch (Berlin)
- Law firms with digital practice: Fieldfisher (Frankfurt/Munich), Taylor Wessing (Hamburg/Munich/Frankfurt), Bird & Bird (Frankfurt/Munich)
- Public affairs firms: Hague Corporate Affairs (Berlin), MSL Germany, APCO Berlin
- Government: Bundeskartellamt (Bonn), BSI (Bonn), BfDI (Bonn — data protection)

**What gets extracted per offer:**
| Field | Description |
|---|---|
| `title` | Job title |
| `company` | Employer name |
| `url` | Original posting URL |
| `description` | Full text of the job description |
| `requirements` | Extracted skills / qualifications |
| `location` | City / remote flag |
| `salary` | Range if listed |
| `posted_date` | When the offer appeared |
| `deadline` | Application deadline if stated |
| `contact_name` | Recruiter / HR name if listed |
| `contact_email` | Recruiter email if listed |
| `contact_linkedin` | Recruiter LinkedIn URL if listed |
| `source` | Which job board |

**Deduplication:** Hash of `(company, title, url)` — skip if already in DB.

**Schedule:** Run daily via a cron job or Windows Task Scheduler.

---

## Phase 2 — Database

**Engine:** SQLite (single file, zero infra, portable).

**Schema (3 tables):**

```
jobs          — one row per unique job offer
contacts      — one row per person at a company (many-to-one with jobs)
applications  — one row per application sent (many-to-one with jobs)
```

**Job status lifecycle:**
```
new → reviewed → approved → applied → followed_up → closed
               → rejected (by us)
```

A simple CLI or TUI will let you review `new` jobs, mark them `approved` or `rejected`, and trigger the next phase.

---

## Phase 3 — CV & Cover Letter Adapter

**Goal:** Use Claude to rewrite/highlight sections of the base CV and write a targeted cover letter for each approved job.

**Inputs:**
- `base_cv.md` — your canonical CV in Markdown (easy to diff/version)
- `base_cover_letter.md` — template cover letter
- Job `description` + `requirements` from the DB

**What Claude does:**
1. Identify the 3–5 key skills/themes in the job description
2. Reorder or rephrase bullet points in the CV to lead with matching experience
3. Write a cover letter that opens with the company's specific context, maps your experience to their needs, and closes with a concrete ask
4. Return structured output: adapted CV sections + full cover letter text

**Outputs (saved to `output/<company>_<date>/`):**
- `cv_adapted.md` — Markdown diff-friendly version
- `cv_adapted.pdf` — Generated from Markdown via Pandoc or WeasyPrint
- `cover_letter.md`
- `cover_letter.pdf`

**Model:** Claude Sonnet 4.6 (balance of quality and cost). Opus for senior/competitive roles.

---

## Phase 4 — Applicator

**Chosen mode: Manual + Docs** — the pipeline generates a ready-to-submit package; Sophie applies herself.

The `apply` skill (Claude Code skill) guides Sophie through the submission:
1. Opens the job URL in the browser
2. Displays a checklist: which form fields to fill, which files to attach
3. Prompts Sophie to confirm when submitted
4. On confirmation, writes the row to `applications.csv` and sets job status to `applied`

This gives full control, avoids anti-bot detection entirely, and keeps a clean audit trail.

**Email applications** (when a job posts a direct address) are also supported: the skill drafts the email body, attaches the PDFs, and Sophie reviews + sends from her own client.

---

## Phase 5 — Application Tracker (CSV)

Every application appended to `applications.csv` with these columns:

| Column | Example |
|---|---|
| `applied_date` | 2026-06-08 |
| `company` | Acme Corp |
| `job_title` | Policy Analyst |
| `job_url` | https://... |
| `source` | LinkedIn |
| `contact_name` | Marie Dupont |
| `contact_email` | marie.dupont@acme.com |
| `contact_linkedin` | linkedin.com/in/mariedupont |
| `application_mode` | email / easy_apply / manual |
| `cv_version` | output/acme_2026-06-08/cv_adapted.pdf |
| `cover_letter_version` | output/acme_2026-06-08/cover_letter.pdf |
| `status` | applied / interview / rejected / offer |
| `follow_up_date` | 2026-06-15 |
| `notes` | Free text |

The CSV is the source of truth for follow-ups. A separate script can read it and remind you of pending follow-ups.

---

## Tech Stack

| Component | Choice | Reason |
|---|---|---|
| Language | Python 3.11+ | Best ecosystem for scraping + LLM + automation |
| Web scraping | Playwright (async) | Handles JS-heavy pages; same tool for automation |
| Job scraping | `python-jobspy` (free) | Scrapes LinkedIn, Indeed, Glassdoor, Google Jobs in one call |
| EU board scraping | Playwright (async) | For EurActiv, Eurobrussels, StepStone, XING, EPSO |
| RSS ingestion | `feedparser` (free) | EurActiv, Eurobrussels, EPSO vacancy feeds |
| Job board APIs | SerpAPI (upgrade path) | Add later if free scraping gets consistently blocked |
| LLM | Claude via `anthropic` SDK | Structured output, long context for full JD |
| Database | SQLite via `sqlite3` / SQLAlchemy | Zero infra, file-based, portable |
| Document generation | Pandoc + LaTeX or WeasyPrint | MD → PDF without Word dependency |
| Scheduling | Windows Task Scheduler / cron | Trigger collector daily |
| Config | `.env` + `config.yaml` | API keys, search terms, target locations |

---

## Repository Layout (proposed)

```
job-poster-sophie/
├── STRATEGY.md             ← this file
├── config.yaml             ← search terms, locations, sources to enable
├── .env                    ← API keys (gitignored)
├── base_cv.md              ← your canonical CV
├── base_cover_letter.md    ← template cover letter
├── applications.csv        ← append-only application log
├── pipeline/
│   ├── collector.py        ← Phase 1: scrape & store jobs
│   ├── database.py         ← Phase 2: SQLite schema & helpers
│   ├── adapter.py          ← Phase 3: Claude CV/cover letter tailoring
│   ├── applicator.py       ← Phase 4: send applications
│   └── tracker.py          ← Phase 5: write to CSV
├── output/                 ← generated docs, one folder per application
│   └── acme_2026-06-08/
│       ├── cv_adapted.md
│       ├── cv_adapted.pdf
│       ├── cover_letter.md
│       └── cover_letter.pdf
├── scripts/
│   ├── review.py           ← CLI to review new jobs and approve/reject
│   └── followup.py         ← reads CSV, lists overdue follow-ups
└── requirements.txt
```

---

## Implementation Roadmap

| Step | What | Effort |
|---|---|---|
| 1 | Set up DB schema + `database.py` | Small |
| 2 | Build collector — `python-jobspy` + RSS feeds | Small |
| 3 | Add Playwright scraper for EU-specific boards (EurActiv, Eurobrussels, StepStone, XING) | Medium |
| 4 | Build `review.py` CLI — browse new jobs, approve/reject | Small |
| 5 | Build adapter — Claude tailors CV + cover letter per job | Medium |
| 6 | Build `apply` skill — generates submission checklist, prompts Sophie to confirm, writes to CSV | Small |
| 7 | Build `followup.py` — reads CSV, lists overdue follow-ups | Small |
| 8 | Scheduling — daily collector run via Windows Task Scheduler | Small |

---

## Open Questions (decisions needed before building)

1. ~~**Field / job types**~~ ✅ Resolved — see Target Map above.
2. ~~**CV format**~~ ✅ Resolved — PDF provided; will convert to Markdown as editable source.
3. ~~**Geography**~~ ✅ Resolved — Germany top priority (Berlin/Munich/Hamburg/Frankfurt), Belgium (Brussels), France (Paris), Remote EU acceptable.
4. ~~**Application email**~~ ✅ Resolved — `sophie.patras@coleurope.eu`
5. ~~**Anti-bot tolerance**~~ ✅ Resolved — pipeline generates tailored documents; Sophie submits manually. No browser automation.
6. ~~**SerpAPI**~~ ✅ Resolved — start free (see stack below); add SerpAPI later only if scraping gets blocked.

### Free scraping stack

| Tool | Covers | Cost |
|---|---|---|
| `python-jobspy` | LinkedIn, Indeed, Glassdoor, Google Jobs, ZipRecruiter | Free / open source |
| `feedparser` + RSS | EurActiv Jobs, Eurobrussels, EPSO vacancies | Free |
| Playwright | StepStone (DE), XING Jobs, Welcome to the Jungle, Interamt, IAPP | Free |

**`python-jobspy`** is the key find: a single Python library that hits LinkedIn, Indeed, Glassdoor, and Google Jobs simultaneously, handles headers/rate-limiting internally, and returns a clean pandas DataFrame. Covers ~80% of sources with no API key needed.

**Upgrade trigger:** if LinkedIn or Indeed start blocking consistently (returns 0 results 3 days in a row), add SerpAPI for that source only.

"""
Adapter — uses an LLM to tailor Sophie's CV and cover letter for each approved job.

Supported providers (set llm.provider in config.yaml):
  google    : Google Gemini free tier — get a key at aistudio.google.com
  anthropic : Claude — requires a paid API key
  ollama    : fully local — install from ollama.ai, then: ollama pull llama3.2
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

ROOT        = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config.yaml"
BASE_CV     = ROOT / "base_cv.md"
BASE_CL     = ROOT / "base_cover_letter.md"
OUTPUT_DIR  = ROOT / "output"

_SYSTEM_PROMPT = """\
You are an expert EU job application consultant helping Sophie Patras tailor her application \
materials for a specific role.

Sophie is an EU digital law specialist based near Brussels with these core strengths:
- Hands-on expertise in AI Act, DSA, DMA, GDPR and IT services law (current role at Milieu \
Law & Policy Consulting)
- Former Data Protection Officer (Hosteur France)
- Lobbying, legislative monitoring and EU liaison experience (Belgian Bar Association)
- Published researcher for the European Parliament and European Commission
- Trilingual: French (native), English (fluent), Italian (fluent)
- College of Europe LL.M + traineeship at the General Court of the EU

Your output must be a single JSON object — no markdown fences, no commentary outside the JSON.
"""

_USER_PROMPT = """\
## Job posting

**Title:** {title}
**Company:** {company}
**Location:** {location}
**Source:** {source}

{description}

---

## Sophie's base CV

{cv_text}

---

## Cover letter template

{cover_letter_template}

---

## Your task

Produce a JSON object with exactly these keys:

{{
  "key_themes": ["3–5 key requirements extracted from the job posting"],
  "match_score": <integer 0–100 indicating how well Sophie's profile fits>,
  "match_notes": "<2–3 sentences: why this is a strong or weak match, what to emphasise>",
  "cv_adapted": "<Sophie's full CV in Markdown, adapted for this role>",
  "cover_letter": "<Full cover letter in Markdown, ready to send>",
  "email_subject": "<Concise application email subject line, e.g. 'Application – Policy Officer | Sophie Patras'>",
  "email_body": "<Plain-text email body (no markdown). 3–5 sentences: introduce Sophie, reference the role, mention both PDFs are attached. Professional but direct. Sign off with name and phone.>"
}}

Rules for CV adaptation:
- Only rephrase or reorder existing content — never fabricate experience
- Elevate bullet points that directly match the job's key requirements
- Where Sophie's existing work involves specific regulations named in the posting \
(AI Act, DSA, GDPR, DMA, etc.), make those explicit
- Keep every position; you may omit weak-match bullet points within a position
- Preserve the exact Markdown structure of the base CV

Rules for cover letter:
- Replace every placeholder in the template with real content
- Open with something specific and concrete about this company or role — not a generic opener
- Structure: hook (why this company) → experience match (2 most relevant things) → closing ask
- Tone: confident, direct, EU-policy register — not stiff, not overly enthusiastic
- Maximum 350 words
- Do not begin with "I am writing to apply for…"
- Close with Sophie's full contact details
- Write in English unless the job posting is clearly in French or German \
(if French: write in French; if German: write in English — Sophie has no German)
"""


def _load_config() -> dict:
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _build_prompt(job, cv_text: str, cover_letter_template: str) -> str:
    return _USER_PROMPT.format(
        title=job["title"],
        company=job["company"],
        location=job["location"] or "Not specified",
        source=job["source"] or "—",
        description=job["description"] or "No description available.",
        cv_text=cv_text,
        cover_letter_template=cover_letter_template,
    )


def _strip_fences(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[^\n]*\n", "", raw)
        raw = re.sub(r"\n```$", "", raw.strip())
    return raw


def _parse_json(raw: str) -> dict:
    return json.loads(_strip_fences(raw))


# ── Provider implementations ──────────────────────────────────────────────────

def _call_google(prompt: str, config: dict) -> dict:
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GOOGLE_API_KEY not set. Get a free key at https://aistudio.google.com/app/apikey "
            "and add it to your .env file."
        )

    client     = genai.Client(api_key=api_key)
    model_name = config["llm"].get("google_model", "gemini-2.0-flash")

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_PROMPT,
            temperature=0.3,
        ),
    )
    return _parse_json(response.text)


def _call_anthropic(prompt: str, config: dict) -> dict:
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. Add it to your .env file "
            "or switch to provider: google in config.yaml."
        )

    client     = anthropic.Anthropic(api_key=api_key)
    model_name = config["llm"].get("anthropic_model", "claude-sonnet-4-6")

    message = client.messages.create(
        model=model_name,
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_json(message.content[0].text)


def _call_ollama(prompt: str, config: dict) -> dict:
    import requests as req

    base_url   = config["llm"].get("ollama_url", "http://localhost:11434")
    model_name = config["llm"].get("ollama_model", "llama3.2")

    response = req.post(
        f"{base_url}/api/chat",
        json={
            "model": model_name,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "stream": False,
        },
        timeout=180,
    )
    response.raise_for_status()
    return _parse_json(response.json()["message"]["content"])


def _call_llm(prompt: str, config: dict) -> dict:
    provider = config["llm"].get("provider", "google")
    if provider == "google":
        return _call_google(prompt, config)
    elif provider == "anthropic":
        return _call_anthropic(prompt, config)
    elif provider == "ollama":
        return _call_ollama(prompt, config)
    else:
        raise ValueError(
            f"Unknown llm.provider '{provider}'. "
            "Valid options: google, anthropic, ollama"
        )


# ── Output helpers ────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:40]


def _try_pdf(md_path: Path) -> bool:
    pdf_path = md_path.with_suffix(".pdf")
    try:
        subprocess.run(
            ["pandoc", str(md_path), "-o", str(pdf_path),
             "--pdf-engine=xelatex", "-V", "geometry:margin=2cm",
             "-V", "fontsize=11pt"],
            check=True, capture_output=True, timeout=30,
        )
        return True
    except FileNotFoundError:
        return False
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def _save_outputs(job, result: dict) -> Path:
    from datetime import datetime
    date_str    = datetime.now().strftime("%Y-%m-%d")
    slug        = _slugify(job["company"])
    out_dir     = OUTPUT_DIR / f"{slug}_{job['id']}_{date_str}"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "cv_adapted.md").write_text(result["cv_adapted"],    encoding="utf-8")
    (out_dir / "cover_letter.md").write_text(result["cover_letter"], encoding="utf-8")
    (out_dir / "meta.json").write_text(
        json.dumps({
            "job_id":       job["id"],
            "title":        job["title"],
            "company":      job["company"],
            "location":     job["location"],
            "key_themes":   result.get("key_themes", []),
            "match_score":  result.get("match_score"),
            "match_notes":  result.get("match_notes", ""),
            "email_subject": result.get("email_subject", ""),
            "email_body":    result.get("email_body", ""),
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_dir


# ── Public API ────────────────────────────────────────────────────────────────

def adapt_for_job(job_id: int) -> dict:
    """Tailor CV + cover letter for a single job. Returns result dict with output_dir."""
    from .database import get_job

    job    = get_job(job_id)
    if not job:
        raise ValueError(f"Job {job_id} not found in database.")

    config = _load_config()

    # Load .env so GOOGLE_API_KEY / ANTHROPIC_API_KEY are available
    try:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
    except ImportError:
        pass

    cv_text   = BASE_CV.read_text(encoding="utf-8")
    cl_tmpl   = BASE_CL.read_text(encoding="utf-8")
    prompt    = _build_prompt(job, cv_text, cl_tmpl)

    result    = _call_llm(prompt, config)
    out_dir   = _save_outputs(job, result)

    result["pdf_generated"] = _try_pdf(out_dir / "cv_adapted.md") and _try_pdf(out_dir / "cover_letter.md")
    result["output_dir"]    = out_dir
    return result


def adapt_all_approved() -> list[dict]:
    """Adapt all approved jobs that haven't been adapted yet."""
    from .database import get_jobs

    results = []
    for job in get_jobs(status="approved"):
        slug = _slugify(job["company"])
        if list(OUTPUT_DIR.glob(f"{slug}_{job['id']}_*")):
            logger.info(f"Skipping job {job['id']} ({job['company']}) — already adapted.")
            continue
        try:
            result = adapt_for_job(job["id"])
            result["job"] = dict(job)
            results.append(result)
        except Exception as exc:
            logger.error(f"Adapter failed for job {job['id']} ({job['company']}): {exc}")
            results.append({"job": dict(job), "error": str(exc)})

    return results

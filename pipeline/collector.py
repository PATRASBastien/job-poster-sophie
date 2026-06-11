"""
Collector — fetches job offers from all configured sources and saves new ones to the DB.

Sources:
  - jobspy   : LinkedIn, Indeed, Glassdoor, Google Jobs (via python-jobspy)
  - rss      : EurActiv, Eurobrussels, EPSO (via feedparser)
  - playwright: StepStone DE, XING Jobs, Welcome to the Jungle
"""

import logging
import time
from pathlib import Path

import feedparser
import pandas as pd
import yaml

from .database import add_job, init_db

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

_GERMAN_REQUIRED_SIGNALS = [
    "german required", "german language", "deutschkenntnisse",
    "deutsch erforderlich", "native german", "deutsch fließend",
    "fließend deutsch", "german native speaker", "muttersprachlich deutsch",
]


def load_config(config_path: Path = CONFIG_PATH) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _detect_language_req(text: str) -> str:
    lower = text.lower()
    if any(signal in lower for signal in _GERMAN_REQUIRED_SIGNALS):
        return "German required"
    return ""


# ── JobSpy ────────────────────────────────────────────────────────────────────

def collect_jobspy(config: dict) -> int:
    """Scrape LinkedIn, Indeed, Glassdoor, Google Jobs via python-jobspy."""
    try:
        from jobspy import scrape_jobs
    except ImportError:
        logger.error("python-jobspy not installed. Run: pip install python-jobspy")
        return 0

    cfg = config["search"]
    # Run primary keywords only; secondary adds noise on daily runs
    keywords = cfg["keywords"]["primary"]
    new_count = 0

    for keyword in keywords:
        for location in cfg["locations"]:
            try:
                df = scrape_jobs(
                    # Glassdoor consistently returns 400 for non-US locations — excluded
                    site_name=["linkedin", "indeed", "google"],
                    search_term=keyword,
                    location=location,
                    results_wanted=cfg.get("results_per_search", 25),
                    hours_old=cfg.get("hours_old", 72),
                    verbose=0,
                )
                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    description = str(row.get("description") or "")
                    salary = _format_salary(row)

                    job_id = add_job(
                        title=str(row.get("title") or "").strip(),
                        company=str(row.get("company") or "").strip(),
                        url=str(row.get("job_url") or ""),
                        description=description,
                        location=str(row.get("location") or location),
                        salary=salary,
                        posted_date=str(row.get("date_posted") or ""),
                        source=str(row.get("site") or "jobspy"),
                        language_req=_detect_language_req(description),
                    )
                    if job_id:
                        new_count += 1

                time.sleep(1)  # polite delay between searches

            except Exception as exc:
                logger.warning(f"JobSpy failed [{keyword} / {location}]: {exc}")

    return new_count


def _format_salary(row) -> str:
    if pd.isna(row.get("min_amount")):
        return ""
    lo = row["min_amount"]
    hi = row.get("max_amount", "")
    currency = row.get("currency", "")
    period = row.get("salary_source", "")
    return f"{lo}–{hi} {currency} {period}".strip()


# ── RSS ───────────────────────────────────────────────────────────────────────

def collect_rss(config: dict) -> int:
    """Parse RSS feeds from EurActiv, Eurobrussels, EPSO."""
    new_count = 0

    for feed_cfg in config.get("rss_feeds", []):
        name = feed_cfg["name"]
        url  = feed_cfg["url"]
        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                logger.warning(f"RSS feed '{name}' could not be parsed: {feed.bozo_exception}")
                continue

            for entry in feed.entries:
                raw_title = entry.get("title", "").strip()
                link      = entry.get("link", "")
                summary   = entry.get("summary", "")
                published = entry.get("published", "")

                title, company = _split_rss_title(raw_title, fallback_company=name)

                job_id = add_job(
                    title=title,
                    company=company,
                    url=link,
                    description=summary,
                    posted_date=published,
                    source=name,
                    language_req=_detect_language_req(summary),
                )
                if job_id:
                    new_count += 1

        except Exception as exc:
            logger.warning(f"RSS feed '{name}' failed: {exc}")

    return new_count


def _split_rss_title(raw: str, fallback_company: str = "") -> tuple[str, str]:
    """
    Many RSS job titles follow "Job Title | Company Name" or "Job Title at Company".
    Returns (title, company).
    """
    if " | " in raw:
        parts = raw.split(" | ", 1)
        return parts[0].strip(), parts[1].strip()
    if " – " in raw:
        parts = raw.split(" – ", 1)
        return parts[0].strip(), parts[1].strip()
    lower = raw.lower()
    if " at " in lower:
        idx = lower.rfind(" at ")
        return raw[:idx].strip(), raw[idx + 4:].strip()
    return raw, fallback_company


# ── Playwright ────────────────────────────────────────────────────────────────

def collect_playwright(config: dict) -> int:
    enabled = {s["name"]: s["enabled"] for s in config.get("playwright_sources", [])}
    new_count = 0

    if enabled.get("StepStone DE"):
        new_count += _scrape_stepstone(config)

    if enabled.get("XING Jobs"):
        new_count += _scrape_xing(config)

    if enabled.get("Welcome to the Jungle"):
        new_count += _scrape_wttj(config)

    return new_count


def _de_locations(config: dict) -> list[str]:
    return [loc for loc in config["search"]["locations"] if "Germany" in loc]


def _scrape_stepstone(config: dict) -> int:
    """
    StepStone DE scraper.
    Selectors are fragile — verify against live site if results drop to zero.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("playwright not installed. Run: pip install playwright && playwright install chromium")
        return 0

    cfg       = config["search"]
    keywords  = cfg["keywords"]["primary"][:6]
    locations = _de_locations(config)[:3]
    new_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "en-GB,en;q=0.9"})

        for keyword in keywords:
            for location in locations:
                city = location.split(",")[0].strip()
                url = f"https://www.stepstone.de/jobs?q={keyword.replace(' ', '+')}&c={city}&radius=30"
                try:
                    page.goto(url, timeout=20000)
                    page.wait_for_timeout(2000)

                    cards = page.query_selector_all("article[data-testid='job-item']")
                    for card in cards[:cfg.get("results_per_search", 25)]:
                        title_el   = card.query_selector("a[data-at='job-item-title']")
                        company_el = card.query_selector("[data-at='job-item-company-name']")
                        title   = title_el.inner_text().strip()   if title_el   else ""
                        company = company_el.inner_text().strip() if company_el else ""
                        href    = title_el.get_attribute("href")  if title_el   else ""
                        job_url = f"https://www.stepstone.de{href}" if href and href.startswith("/") else href or ""

                        if not title:
                            continue

                        job_id = add_job(
                            title=title,
                            company=company,
                            url=job_url,
                            location=location,
                            source="StepStone",
                            language_req=_detect_language_req(title),
                        )
                        if job_id:
                            new_count += 1

                    time.sleep(1.5)

                except Exception as exc:
                    logger.warning(f"StepStone failed [{keyword} / {city}]: {exc}")

        browser.close()

    return new_count


def _scrape_xing(config: dict) -> int:
    """
    XING Jobs scraper.
    Selectors are fragile — verify against live site if results drop to zero.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return 0

    cfg       = config["search"]
    keywords  = cfg["keywords"]["primary"][:6]
    locations = _de_locations(config)[:3]
    new_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for keyword in keywords:
            for location in locations:
                city = location.split(",")[0].strip()
                url = f"https://www.xing.com/jobs/search?keywords={keyword.replace(' ', '%20')}&location={city}"
                try:
                    page.goto(url, timeout=20000)
                    page.wait_for_timeout(2500)

                    cards = page.query_selector_all("[data-testid='job-listing-item']")
                    for card in cards[:cfg.get("results_per_search", 25)]:
                        title_el   = card.query_selector("a[data-testid='job-listing-item-title']")
                        company_el = card.query_selector("[data-testid='job-listing-item-company-name']")
                        title   = title_el.inner_text().strip()   if title_el   else ""
                        company = company_el.inner_text().strip() if company_el else ""
                        href    = title_el.get_attribute("href")  if title_el   else ""
                        job_url = f"https://www.xing.com{href}" if href and href.startswith("/") else href or ""

                        if not title:
                            continue

                        job_id = add_job(
                            title=title,
                            company=company,
                            url=job_url,
                            location=location,
                            source="XING",
                            language_req=_detect_language_req(title),
                        )
                        if job_id:
                            new_count += 1

                    time.sleep(1.5)

                except Exception as exc:
                    logger.warning(f"XING failed [{keyword} / {city}]: {exc}")

        browser.close()

    return new_count


def _scrape_wttj(config: dict) -> int:
    """
    Welcome to the Jungle scraper.
    Selectors are fragile — verify against live site if results drop to zero.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return 0

    cfg       = config["search"]
    keywords  = cfg["keywords"]["primary"][:6]
    new_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for keyword in keywords:
            url = (
                f"https://www.welcometothejungle.com/en/jobs"
                f"?query={keyword.replace(' ', '%20')}&aroundQuery=Europe"
            )
            try:
                page.goto(url, timeout=20000)
                page.wait_for_timeout(2500)

                cards = page.query_selector_all("li[data-testid='search-results-list-item-wrapper']")
                for card in cards[:cfg.get("results_per_search", 25)]:
                    title_el   = card.query_selector("h3")
                    company_el = card.query_selector("span[data-testid='job-search-results-company-name']")
                    link_el    = card.query_selector("a")
                    title   = title_el.inner_text().strip()   if title_el   else ""
                    company = company_el.inner_text().strip() if company_el else ""
                    href    = link_el.get_attribute("href")   if link_el    else ""
                    job_url = f"https://www.welcometothejungle.com{href}" if href and href.startswith("/") else href or ""

                    if not title:
                        continue

                    job_id = add_job(
                        title=title,
                        company=company,
                        url=job_url,
                        source="Welcome to the Jungle",
                        language_req=_detect_language_req(title),
                    )
                    if job_id:
                        new_count += 1

                time.sleep(1.5)

            except Exception as exc:
                logger.warning(f"WTTJ failed [{keyword}]: {exc}")

        browser.close()

    return new_count


# ── Entry point ───────────────────────────────────────────────────────────────

def run_all(config_path: Path = CONFIG_PATH) -> dict[str, int]:
    """Run all enabled collectors. Returns a dict of {source: new_jobs_count}."""
    config = load_config(config_path)
    init_db()

    results: dict[str, int] = {}

    if config["sources"].get("jobspy"):
        logger.info("Running JobSpy collector...")
        results["jobspy"] = collect_jobspy(config)

    if config["sources"].get("rss"):
        logger.info("Running RSS collector...")
        results["rss"] = collect_rss(config)

    if config["sources"].get("playwright"):
        logger.info("Running Playwright collector...")
        results["playwright"] = collect_playwright(config)

    return results

import requests
import json
import os
import time
import re

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "YOUR_DISCORD_OR_SLACK_WEBHOOK_URL_HERE")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

STATE_FILE = "seen_jobs.json"

# ---------------------------------------------------------------------------
# KEYWORDS  (case-insensitive match against job title)
# ---------------------------------------------------------------------------

KEYWORDS = [
    # Analyst roles
    "data analyst", "business analyst", "product analyst",
    "analytics engineer", "data scientist", "insights analyst",
    "growth analyst", "strategy analyst", "market analyst",
    "research analyst", "quantitative analyst", "quant analyst",
    "bi analyst", "reporting analyst", "operations analyst",
    "revenue analyst", "risk analyst", "financial analyst",

    # Web3 / Blockchain / Crypto
    "blockchain analyst", "blockchain developer", "crypto analyst",
    "web3 analyst", "web3 developer", "defi analyst",
    "token analyst", "protocol analyst", "on-chain analyst",
    "smart contract", "solidity", "crypto researcher",
    "blockchain engineer", "crypto engineer",

    # Data Engineering (adjacent, often cross-posted)
    "data engineer", "analytics engineer",

    # Product
    "product manager", "product owner",
]

# ---------------------------------------------------------------------------
# COMPANIES — structured by ATS
# ---------------------------------------------------------------------------

COMPANIES = [

    # ── GREENHOUSE ─────────────────────────────────────────────────────────
    # Finance / Crypto / Web3
    {"name": "Coinbase",       "ats": "greenhouse", "id": "coinbase"},
    {"name": "Gemini",         "ats": "greenhouse", "id": "gemini"},
    {"name": "Kraken",         "ats": "greenhouse", "id": "kraken"},
    {"name": "Chainalysis",    "ats": "greenhouse", "id": "chainalysis"},
    {"name": "Alchemy",        "ats": "greenhouse", "id": "alchemy"},
    {"name": "Nansen",         "ats": "greenhouse", "id": "nansen"},
    # Data / Tech
    {"name": "Stripe",         "ats": "greenhouse", "id": "stripe"},
    {"name": "Databricks",     "ats": "greenhouse", "id": "databricks"},
    {"name": "dbt Labs",       "ats": "greenhouse", "id": "dbtlabs"},
    {"name": "Amplitude",      "ats": "greenhouse", "id": "amplitude"},
    {"name": "Mixpanel",       "ats": "greenhouse", "id": "mixpanel"},
    {"name": "Plaid",          "ats": "greenhouse", "id": "plaid"},
    {"name": "Brex",           "ats": "greenhouse", "id": "brex"},
    {"name": "Retool",         "ats": "greenhouse", "id": "retool"},
    {"name": "Figma",          "ats": "greenhouse", "id": "figma"},  # designer-heavy but has PMs/analysts
    {"name": "Notion",         "ats": "greenhouse", "id": "notion"},
    {"name": "Linear",         "ats": "greenhouse", "id": "linear"},
    {"name": "Weights & Biases", "ats": "greenhouse", "id": "wandb"},
    {"name": "Scale AI",       "ats": "greenhouse", "id": "scaleai"},

    # ── LEVER ──────────────────────────────────────────────────────────────
    {"name": "OpenSea",        "ats": "lever", "id": "opensea"},
    {"name": "Consensys",      "ats": "lever", "id": "consensys"},
    {"name": "Dune Analytics", "ats": "lever", "id": "dune-analytics"},
    {"name": "CoinGecko",      "ats": "lever", "id": "coingecko"},
    {"name": "Messari",        "ats": "lever", "id": "messari"},
    {"name": "Ripple",         "ats": "lever", "id": "ripple"},
    {"name": "Aave",           "ats": "lever", "id": "aave-companies"},
    {"name": "Anchorage Digital", "ats": "lever", "id": "anchoragedigital"},
    {"name": "Figma (Lever)",  "ats": "lever", "id": "figma"},
    {"name": "Carta",          "ats": "lever", "id": "carta"},
    {"name": "Productboard",   "ats": "lever", "id": "productboard"},

    # ── WORKDAY ────────────────────────────────────────────────────────────
    # Subdomain is the Workday tenant ID (subdomain of myworkdayjobs.com)
    {"name": "Polygon Labs",   "ats": "workday", "id": "polygon"},
    {"name": "Binance",        "ats": "workday", "id": "binancecareers"},
    {"name": "Visa",           "ats": "workday", "id": "visa"},
    {"name": "Mastercard",     "ats": "workday", "id": "mastercard"},
    {"name": "PayPal",         "ats": "workday", "id": "paypal"},
    {"name": "Intuit",         "ats": "workday", "id": "intuit"},
    {"name": "Salesforce",     "ats": "workday", "id": "salesforce"},
    {"name": "Walmart",        "ats": "workday", "id": "walmart"},
    {"name": "Adobe",          "ats": "workday", "id": "adobe"},
    {"name": "Uber",           "ats": "workday", "id": "uber"},
    {"name": "Airbnb",         "ats": "workday", "id": "airbnb"},
    {"name": "Workday",        "ats": "workday", "id": "workday"},
    {"name": "ServiceNow",     "ats": "workday", "id": "servicenow"},

    # ── ASHBY  ─────────────────────────────────────────────────────────────
    # Trendy for startups — good for Web3/AI companies
    {"name": "Anthropic",      "ats": "ashby", "id": "anthropic"},
    {"name": "EigenLayer",     "ats": "ashby", "id": "eigenlayer"},
    {"name": "Starkware",      "ats": "ashby", "id": "starkware"},
    {"name": "Uniswap Labs",   "ats": "ashby", "id": "uniswaplabs"},
    {"name": "Base (Coinbase Layer2)", "ats": "ashby", "id": "base"},
    {"name": "Paradigm",       "ats": "ashby", "id": "paradigm"},

    # ── EIGHTFOLD ──────────────────────────────────────────────────────────
    # Large enterprises using Eightfold AI
    {"name": "Wipro",          "ats": "eightfold", "id": "wipro"},
    {"name": "Infosys",        "ats": "eightfold", "id": "infosys"},
    {"name": "TCS",            "ats": "eightfold", "id": "tcs"},
    {"name": "HCL",            "ats": "eightfold", "id": "hcltech"},
    {"name": "Wells Fargo",    "ats": "eightfold", "id": "wellsfargo"},
    {"name": "Micron",         "ats": "eightfold", "id": "micron"},

    # ── WORKABLE ───────────────────────────────────────────────────────────
    {"name": "Covalent",       "ats": "workable", "id": "covalent-network"},
    {"name": "Bitquery",       "ats": "workable", "id": "bitquery"},
]

# ---------------------------------------------------------------------------
# LINKEDIN SEARCH CONFIGS
# These are treated differently — we scrape LinkedIn's public job search
# ---------------------------------------------------------------------------

LINKEDIN_SEARCHES = [
    # (keywords, location, remote_filter)
    # remote_filter: 1=onsite, 2=remote, 3=hybrid
    {"keywords": "blockchain analyst OR crypto analyst OR web3 analyst",  "location": "India",   "remote": "2"},
    {"keywords": "data analyst OR product analyst OR business analyst",    "location": "India",   "remote": "2"},
    {"keywords": "blockchain developer OR web3 developer OR solidity",     "location": "India",   "remote": "2"},
    {"keywords": "crypto analyst OR DeFi analyst",                         "location": "Remote",  "remote": "2"},
    {"keywords": "on-chain analyst OR token analyst OR protocol analyst",  "location": "",        "remote": "2"},
    {"keywords": "data analyst blockchain",                                "location": "India",   "remote": ""},
]

FREELANCE_SEARCHES = [
    # Platforms that have public APIs or scrapeable pages
    # We flag these as freelance opportunities
    {"platform": "upwork_rss", "query": "blockchain analyst data analyst web3"},
    {"platform": "remoteok",   "query": "analyst"},
]

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_seen_jobs() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}


def save_seen_jobs(seen_jobs: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(seen_jobs, f, indent=4)


def is_relevant(title: str) -> bool:
    if not KEYWORDS:
        return True
    t = title.lower()
    return any(kw.lower() in t for kw in KEYWORDS)


def send_alert(source: str, job_title: str, job_url: str,
               location: str = "", job_type: str = ""):
    tag = f"[{job_type}] " if job_type else ""
    loc = f" | 📍 {location}" if location else ""
    print(f"  🚨  {tag}{source} → {job_title}{loc}")

    text = (
        f"🚀 *New Job Alert!*\n"
        f"*Company/Source:* {source}\n"
        f"*Role:* {job_title}\n"
        f"{f'*Location:* {location}' + chr(10) if location else ''}"
        f"{f'*Type:* {job_type}' + chr(10) if job_type else ''}"
        f"*Link:* {job_url}"
    )

    # Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"},
                timeout=10,
            )
        except Exception as e:
            print(f"    Telegram send failed: {e}")

    # Webhook (Discord / Slack)
    if WEBHOOK_URL and WEBHOOK_URL != "YOUR_DISCORD_OR_SLACK_WEBHOOK_URL_HERE":
        try:
            requests.post(WEBHOOK_URL, json={"content": text}, timeout=10)
        except Exception as e:
            print(f"    Webhook send failed: {e}")


# ---------------------------------------------------------------------------
# ATS FETCHERS
# ---------------------------------------------------------------------------

def check_greenhouse(company_id: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        jobs = []
        for job in r.json().get("jobs", []):
            jobs.append({
                "id":       str(job["id"]),
                "title":    job.get("title", ""),
                "url":      job.get("absolute_url", ""),
                "location": job.get("location", {}).get("name", ""),
            })
        return jobs
    except Exception as e:
        print(f"    [Greenhouse] Error for {company_id}: {e}")
        return []


def check_lever(company_id: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{company_id}?mode=json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
        jobs = []
        for job in r.json():
            categories = job.get("categories", {})
            location = categories.get("location", "") or categories.get("allLocations", [""])[0]
            jobs.append({
                "id":       job["id"],
                "title":    job.get("text", ""),
                "url":      job.get("hostedUrl", ""),
                "location": location,
            })
        return jobs
    except Exception as e:
        print(f"    [Lever] Error for {company_id}: {e}")
        return []


def check_workday(tenant_id: str) -> list[dict]:
    """
    Workday exposes a consistent REST endpoint across all tenants.
    We search for our core keywords to avoid pulling 10k+ jobs.
    """
    search_terms = [
        "analyst", "blockchain", "crypto", "web3", "data engineer"
    ]
    seen_ids: set = set()
    jobs = []

    for term in search_terms:
        url = (
            f"https://{tenant_id}.wd1.myworkdayjobs.com/wday/cxs/"
            f"{tenant_id}/External/jobs"
        )
        payload = {
            "appliedFacets": {},
            "limit": 20,
            "offset": 0,
            "searchText": term,
        }
        try:
            r = requests.post(url, json=payload, headers={**HEADERS, "Content-Type": "application/json"}, timeout=12)
            r.raise_for_status()
            data = r.json()
            for job in data.get("jobPostings", []):
                jid = job.get("bulletFields", [""])[0] or job.get("title", "") + job.get("postedOn", "")
                ext_id = job.get("externalPath", jid)
                if ext_id in seen_ids:
                    continue
                seen_ids.add(ext_id)
                jobs.append({
                    "id":       ext_id,
                    "title":    job.get("title", ""),
                    "url":      f"https://{tenant_id}.wd1.myworkdayjobs.com{job.get('externalPath', '')}",
                    "location": job.get("locationsText", ""),
                })
        except Exception as e:
            print(f"    [Workday] Error for {tenant_id}/{term}: {e}")
        time.sleep(0.5)

    return jobs


def check_ashby(company_id: str) -> list[dict]:
    """Ashby ATS public API."""
    url = "https://api.ashbyhq.com/posting-api/job-board"
    try:
        r = requests.post(
            url,
            json={"organizationHostedJobsPageName": company_id},
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        jobs = []
        for job in r.json().get("jobs", []):
            jobs.append({
                "id":       job.get("id", ""),
                "title":    job.get("title", ""),
                "url":      job.get("jobUrl", ""),
                "location": job.get("location", ""),
            })
        return jobs
    except Exception as e:
        print(f"    [Ashby] Error for {company_id}: {e}")
        return []


def check_eightfold(company_id: str) -> list[dict]:
    """
    Eightfold AI powers career sites for many large enterprises.
    The API endpoint pattern is consistent across tenants.
    """
    search_terms = ["analyst", "blockchain", "data", "crypto"]
    seen_ids: set = set()
    jobs = []

    for term in search_terms:
        url = f"https://careers.{company_id}.com/api/apply/v2/jobs"
        params = {
            "domain": f"{company_id}.com",
            "query": term,
            "triggerGoButton": "false",
            "start": 0,
            "num": 20,
            "pid": "",
            "exclude_pid": "",
            "pt": "false",
        }
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=12)
            r.raise_for_status()
            for job in r.json().get("positions", []):
                jid = str(job.get("id", ""))
                if jid in seen_ids:
                    continue
                seen_ids.add(jid)
                jobs.append({
                    "id":       jid,
                    "title":    job.get("name", ""),
                    "url":      f"https://careers.{company_id}.com/jobs/{jid}",
                    "location": job.get("location", ""),
                })
        except Exception as e:
            print(f"    [Eightfold] Error for {company_id}/{term}: {e}")
        time.sleep(0.5)

    return jobs


def check_workable(company_id: str) -> list[dict]:
    """Workable public job board API."""
    url = f"https://apply.workable.com/api/v1/widget/accounts/{company_id}/jobs"
    try:
        r = requests.post(
            url,
            json={"query": "", "location": [], "department": [], "worktype": [], "remote": []},
            headers={**HEADERS, "Content-Type": "application/json"},
            timeout=10,
        )
        r.raise_for_status()
        jobs = []
        for job in r.json().get("results", []):
            jobs.append({
                "id":       job.get("shortcode", job.get("id", "")),
                "title":    job.get("title", ""),
                "url":      f"https://apply.workable.com/{company_id}/j/{job.get('shortcode', '')}",
                "location": job.get("location", {}).get("country", ""),
            })
        return jobs
    except Exception as e:
        print(f"    [Workable] Error for {company_id}: {e}")
        return []


# ---------------------------------------------------------------------------
# AMAZON JOBS (kept from original)
# ---------------------------------------------------------------------------

def check_amazon_jobs(base_query: str = "data analyst", country_code: str = "IND") -> list[dict]:
    url = "https://www.amazon.jobs/en/search.json"
    params = {
        "base_query": base_query,
        "country":    country_code,
        "result_limit": 15,
        "sort":       "recent",
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        jobs = []
        for job in r.json().get("jobs", []):
            jobs.append({
                "id":       str(job.get("id_icims", job.get("id", ""))),
                "title":    job.get("title", ""),
                "url":      "https://www.amazon.jobs" + job.get("job_path", ""),
                "location": job.get("normalized_location", "India"),
            })
        return jobs
    except Exception as e:
        print(f"    [Amazon] Error: {e}")
        return []


# ---------------------------------------------------------------------------
# LINKEDIN  (public job search — no login required)
# ---------------------------------------------------------------------------

def check_linkedin(keywords: str, location: str = "", remote: str = "") -> list[dict]:
    """
    Uses LinkedIn's public jobs search endpoint (no auth needed).
    Returns up to 25 results per query.
    """
    params = {
        "keywords":        keywords,
        "location":        location,
        "f_TPR":           "r86400",   # posted in last 24 hours
        "position":        1,
        "pageNum":         0,
        "start":           0,
        "count":           25,
    }
    if remote:
        params["f_WT"] = remote   # 1=onsite, 2=remote, 3=hybrid

    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    try:
        r = requests.get(url, params=params, headers={
            **HEADERS,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }, timeout=15)
        r.raise_for_status()

        # LinkedIn returns HTML cards; extract job IDs and titles with regex
        html = r.text
        job_ids    = re.findall(r'data-entity-urn="urn:li:jobPosting:(\d+)"', html)
        job_titles = re.findall(r'class="sr-only"[^>]*>([^<]+)</span>', html)

        # Fallback title extraction
        if not job_titles:
            job_titles = re.findall(r'aria-label="([^"]+)"[^>]*class="[^"]*job[^"]*"', html)

        jobs = []
        for i, jid in enumerate(job_ids):
            title = job_titles[i].strip() if i < len(job_titles) else "Unknown Title"
            jobs.append({
                "id":       f"li_{jid}",
                "title":    title,
                "url":      f"https://www.linkedin.com/jobs/view/{jid}/",
                "location": location,
            })
        return jobs

    except Exception as e:
        print(f"    [LinkedIn] Error for '{keywords}': {e}")
        return []


# ---------------------------------------------------------------------------
# FREELANCE / CONTRACT PLATFORMS
# ---------------------------------------------------------------------------

def check_remoteok(query: str = "analyst") -> list[dict]:
    """
    Remote OK has a clean public JSON API — great for remote/freelance roles.
    """
    url = "https://remoteok.com/api"
    try:
        r = requests.get(url, headers={**HEADERS, "Accept": "application/json"}, timeout=12)
        r.raise_for_status()
        data = r.json()
        jobs = []
        for job in data:
            if not isinstance(job, dict) or "id" not in job:
                continue
            title = job.get("position", "")
            tags  = " ".join(job.get("tags", []))
            combined = (title + " " + tags).lower()
            if any(kw.lower() in combined for kw in KEYWORDS):
                jobs.append({
                    "id":       str(job["id"]),
                    "title":    title,
                    "url":      job.get("url", "https://remoteok.com"),
                    "location": "Remote",
                    "type":     "Remote / Freelance",
                })
        return jobs
    except Exception as e:
        print(f"    [RemoteOK] Error: {e}")
        return []


def check_wellfound(query: str = "data analyst") -> list[dict]:
    """
    Wellfound (formerly AngelList Talent) — great for startup + remote roles.
    Uses their public search API.
    """
    url = "https://wellfound.com/jobs.json"
    params = {
        "q[job_types][]": ["full_time", "contract", "part_time"],
        "q[remote]":      True,
        "q[keywords]":    query,
    }
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=12)
        r.raise_for_status()
        jobs = []
        for job in r.json().get("jobs", []):
            jobs.append({
                "id":       str(job.get("id", "")),
                "title":    job.get("title", ""),
                "url":      "https://wellfound.com" + job.get("slug", ""),
                "location": job.get("location_names", ["Remote"])[0] if job.get("location_names") else "Remote",
                "type":     job.get("job_type_name", ""),
            })
        return jobs
    except Exception as e:
        print(f"    [Wellfound] Error for '{query}': {e}")
        return []


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("  Job Scraper Starting")
    print("=" * 60)

    seen_jobs   = load_seen_jobs()
    new_jobs_found = False

    # ── 1. Standard ATS companies ──────────────────────────────────────────
    ats_map = {
        "greenhouse": check_greenhouse,
        "lever":      check_lever,
        "workday":    check_workday,
        "ashby":      check_ashby,
        "eightfold":  check_eightfold,
        "workable":   check_workable,
    }

    for company in COMPANIES:
        ats    = company["ats"]
        name   = company["name"]
        cid    = company["id"]
        fetcher = ats_map.get(ats)

        if not fetcher:
            print(f"  [SKIP] Unsupported ATS '{ats}' for {name}")
            continue

        print(f"  Scanning [{ats.upper()}] {name} …")
        current_jobs = fetcher(cid)

        memory_key   = f"{ats}_{cid}"
        company_seen = seen_jobs.get(memory_key, [])
        new_memory   = company_seen.copy()

        for job in current_jobs:
            if job["id"] not in company_seen:
                if is_relevant(job["title"]):
                    send_alert(name, job["title"], job["url"], job.get("location", ""))
                new_memory.append(job["id"])
                new_jobs_found = True

        seen_jobs[memory_key] = new_memory
        time.sleep(1)

    # ── 2. Amazon Jobs ─────────────────────────────────────────────────────
    print("\n  Scanning [AMAZON] India …")
    amazon_queries = [
        ("data analyst",       "IND"),
        ("business analyst",   "IND"),
        ("blockchain",         "IND"),
        ("product analyst",    "IND"),
    ]
    for query, country in amazon_queries:
        key = f"amazon_{query.replace(' ', '_')}_{country}"
        seen_ids = seen_jobs.get(key, [])
        new_ids  = seen_ids.copy()
        for job in check_amazon_jobs(query, country):
            if job["id"] not in seen_ids:
                if is_relevant(job["title"]):
                    send_alert("Amazon", job["title"], job["url"], job["location"])
                new_ids.append(job["id"])
                new_jobs_found = True
        seen_jobs[key] = new_ids
        time.sleep(1)

    # ── 3. LinkedIn ────────────────────────────────────────────────────────
    print("\n  Scanning [LINKEDIN] …")
    for cfg in LINKEDIN_SEARCHES:
        key = f"linkedin_{cfg['keywords'][:40]}_{cfg['location']}"
        seen_ids = seen_jobs.get(key, [])
        new_ids  = seen_ids.copy()
        for job in check_linkedin(cfg["keywords"], cfg["location"], cfg.get("remote", "")):
            if job["id"] not in seen_ids:
                if is_relevant(job["title"]):
                    send_alert(
                        "LinkedIn",
                        job["title"],
                        job["url"],
                        job.get("location", ""),
                    )
                new_ids.append(job["id"])
                new_jobs_found = True
        seen_jobs[key] = new_ids
        time.sleep(2)   # LinkedIn is stricter — be polite

    # ── 4. Remote OK (freelance/contract) ──────────────────────────────────
    print("\n  Scanning [REMOTEOK] (Freelance/Remote) …")
    key = "remoteok_general"
    seen_ids = seen_jobs.get(key, [])
    new_ids  = seen_ids.copy()
    for job in check_remoteok():
        if job["id"] not in seen_ids:
            send_alert("RemoteOK", job["title"], job["url"],
                       "Remote", job.get("type", "Remote"))
            new_ids.append(job["id"])
            new_jobs_found = True
    seen_jobs[key] = new_ids
    time.sleep(1)

    # ── 5. Wellfound (startup + freelance) ────────────────────────────────
    print("\n  Scanning [WELLFOUND] (Startups / Remote) …")
    wf_queries = ["data analyst blockchain", "web3 analyst", "crypto analyst"]
    for q in wf_queries:
        key = f"wellfound_{q.replace(' ', '_')}"
        seen_ids = seen_jobs.get(key, [])
        new_ids  = seen_ids.copy()
        for job in check_wellfound(q):
            if job["id"] not in seen_ids:
                if is_relevant(job["title"]):
                    send_alert(
                        "Wellfound",
                        job["title"],
                        job["url"],
                        job.get("location", "Remote"),
                        job.get("type", ""),
                    )
                new_ids.append(job["id"])
                new_jobs_found = True
        seen_jobs[key] = new_ids
        time.sleep(1)

    # ── Save state ─────────────────────────────────────────────────────────
    if new_jobs_found:
        save_seen_jobs(seen_jobs)
        print("\n✅  Scan complete — state saved.")
    else:
        print("\n✅  Scan complete — no new relevant jobs.")


if __name__ == "__main__":
    main()
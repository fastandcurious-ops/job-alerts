import requests
import json
import os
import time
from datetime import datetime, timezone, timedelta
import re
from urllib.parse import urlparse

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_FILE = "seen_jobs.json"

SWE_KEYWORDS = [
    "business analyst",
    "data analyst",
    "data engineer",
    "product analyst",
    "data",
    "frontend",
    "fullstack",
    "full stack",
    "member of technical staff",
    "mts",
    "technology analyst",
    "tech analyst",
    "technical associate",
    "associate",
    "sde 2",
    "sde2",
    "software engineer ii",
    "software engineer 2",
    "sde ii",
    "mid",
    "c++",
    "node",
    "react",
    "javascript",
    "typescript",
    "python",
    "software",
    "software developer",
    "swe",
    "software development engineer",
    "technical",
]

EXCLUDED_KEYWORDS = [
    "data scientist", 
    "data entry", 
    "principal", 
    "manager", 
    "vp", 
    "head", 
    "president",
]

def is_india(location_str):
    """Ensures the job is located in an Indian tech hub."""
    if not location_str:
        return False
    loc = location_str.lower()
    indian_hubs = [
        "india",
        "ind",
        "blr",
        "bengaluru",
        "bangalore",
        "delhi",
        "ncr",
        "new delhi",
        "gurgaon",
        "gurugram",
        "noida",
        "mumbai",
        "bombay",
        "hyderabad",
        "pune",
        "chennai",
        "madras",
        "kolkata",
        "ahmedabad",
        "remote - in",
        "remote-in",
        "del",
        "mum",
        "hyd",
        "chen",
        "kolk",
        "ahmd",
        "remote (india)",
        "remote (in)",
        "remote india",
        "remote",
    ]
    return any(hub in loc for hub in indian_hubs)

TARGETS = [
    # Custom API
    {"name": "Amazon", "ats": "amazon", "country": "IND", "keywords": SWE_KEYWORDS},
    
    # Greenhouse Configurations
    {"name": "Stripe", "ats": "greenhouse", "id": "stripe", "keywords": SWE_KEYWORDS},
    {"name": "Checkout.com", "ats": "greenhouse", "id": "checkoutcom", "keywords": SWE_KEYWORDS},
    {"name": "CRED", "ats": "greenhouse", "id": "cred", "keywords": SWE_KEYWORDS},
    {"name": "Groww", "ats": "greenhouse", "id": "groww", "keywords": SWE_KEYWORDS},
    {"name": "PhonePe", "ats": "greenhouse", "id": "phonepe", "keywords": SWE_KEYWORDS},
    {"name": "Razorpay", "ats": "greenhouse", "id": "razorpaysoftwareprivatelimited", "keywords": SWE_KEYWORDS},
    {"name": "Rippling", "ats": "greenhouse", "id": "rippling", "keywords": SWE_KEYWORDS},
    {"name": "Slice", "ats": "greenhouse", "id": "slice", "keywords": SWE_KEYWORDS},
    {"name": "Upstox", "ats": "greenhouse", "id": "upstox", "keywords": SWE_KEYWORDS},
    {"name": "Brex", "ats": "greenhouse", "id": "brex", "keywords": SWE_KEYWORDS},
    {"name": "Grab", "ats": "greenhouse", "id": "grab", "keywords": SWE_KEYWORDS},
    {"name": "GoTo", "ats": "greenhouse", "id": "gojek", "keywords": SWE_KEYWORDS},
    {"name": "MobiKwik", "ats": "greenhouse", "id": "mobikwik", "keywords": SWE_KEYWORDS},
    {"name": "Pine Labs", "ats": "greenhouse", "id": "pinelabs", "keywords": SWE_KEYWORDS},
    {"name": "Wise", "ats": "greenhouse", "id": "wise", "keywords": SWE_KEYWORDS},
    {"name": "Chargebee", "ats": "greenhouse", "id": "chargebee", "keywords": SWE_KEYWORDS},
    {"name": "Yubi", "ats": "greenhouse", "id": "credavenue", "keywords": SWE_KEYWORDS},
    {"name": "LendingKart", "ats": "greenhouse", "id": "lendingkart", "keywords": SWE_KEYWORDS},
    {"name": "Airbnb", "ats": "greenhouse", "id": "airbnb", "keywords": SWE_KEYWORDS},
    {"name": "Tower Research Capital", "ats": "greenhouse", "id": "towerresearchcapital", "keywords": SWE_KEYWORDS},
    {"name": "Quadeye", "ats": "greenhouse", "id": "quadeye", "keywords": SWE_KEYWORDS},
    {"name": "AlphaGrep", "ats": "greenhouse", "id": "alphagrepsecurities", "keywords": SWE_KEYWORDS},
    {"name": "Databricks", "ats": "greenhouse", "id": "databricks", "keywords": SWE_KEYWORDS},
    {"name": "Rubrik", "ats": "greenhouse", "id": "rubrik", "keywords": SWE_KEYWORDS},
    {"name": "Cohesity", "ats": "greenhouse", "id": "cohesity", "keywords": SWE_KEYWORDS},
    {"name": "Confluent", "ats": "greenhouse", "id": "confluent", "keywords": SWE_KEYWORDS},
    {"name": "Glean", "ats": "greenhouse", "id": "glean", "keywords": SWE_KEYWORDS},
    {"name": "BrowserStack", "ats": "greenhouse", "id": "browserstack", "keywords": SWE_KEYWORDS},
    {"name": "Freshworks", "ats": "greenhouse", "id": "freshworks", "keywords": SWE_KEYWORDS},
    {"name": "Cloudflare", "ats": "greenhouse", "id": "cloudflare", "keywords": SWE_KEYWORDS},
    {"name": "MindTickle", "ats": "greenhouse", "id": "mindtickle", "keywords": SWE_KEYWORDS},
    {"name": "Cleartax", "ats": "greenhouse", "id": "cleartax", "keywords": SWE_KEYWORDS},
    {"name": "Agoda", "ats": "greenhouse", "id": "agoda", "keywords": SWE_KEYWORDS},
    {"name": "DoorDash", "ats": "greenhouse", "id": "doordash", "keywords": SWE_KEYWORDS},
    {"name": "GitHub", "ats": "greenhouse", "id": "github", "keywords": SWE_KEYWORDS},
    {"name": "Twilio", "ats": "greenhouse", "id": "twilio", "keywords": SWE_KEYWORDS},
    {"name": "Dropbox", "ats": "greenhouse", "id": "dropbox", "keywords": SWE_KEYWORDS},
    
    # Lever Configurations
    {"name": "Revolut", "ats": "lever", "id": "revolut", "keywords": SWE_KEYWORDS},
    {"name": "Paytm", "ats": "lever", "id": "paytm", "keywords": SWE_KEYWORDS},
    {"name": "Perfios", "ats": "lever", "id": "perfios", "keywords": SWE_KEYWORDS},
    {"name": "PolicyBazaar", "ats": "lever", "id": "policybazaar", "keywords": SWE_KEYWORDS},
    {"name": "BizNext", "ats": "lever", "id": "biznext", "keywords": SWE_KEYWORDS},
    {"name": "Jumbotail", "ats": "lever", "id": "jumbotail", "keywords": SWE_KEYWORDS},
    {"name": "Atlassian", "ats": "lever", "id": "atlassian", "keywords": SWE_KEYWORDS},
    {"name": "Graviton Research Capital", "ats": "lever", "id": "gravitonresearchcapital", "keywords": SWE_KEYWORDS},
    {"name": "Postman", "ats": "lever", "id": "postman", "keywords": SWE_KEYWORDS},
    {"name": "Swiggy", "ats": "lever", "id": "swiggy", "keywords": SWE_KEYWORDS},
    {"name": "Zomato", "ats": "lever", "id": "zomato", "keywords": SWE_KEYWORDS},
    {"name": "Zepto", "ats": "lever", "id": "zepto", "keywords": SWE_KEYWORDS},
    {"name": "Blinkit", "ats": "lever", "id": "blinkit", "keywords": SWE_KEYWORDS},
    {"name": "Meesho", "ats": "lever", "id": "meesho", "keywords": SWE_KEYWORDS},
    {"name": "Dream11", "ats": "lever", "id": "dreamsports", "keywords": SWE_KEYWORDS},
    {"name": "Lenskart", "ats": "lever", "id": "lenskart", "keywords": SWE_KEYWORDS},
    {"name": "Delhivery", "ats": "lever", "id": "delhivery", "keywords": SWE_KEYWORDS},
    {"name": "Tekion", "ats": "lever", "id": "tekion", "keywords": SWE_KEYWORDS},
    
    # Workday Configurations
    {"name": "Mastercard", "ats": "workday", "url": "https://mastercard.wd1.myworkdayjobs.com/CorporateCareers", "keywords": SWE_KEYWORDS},
    {"name": "Walmart Global Tech", "ats": "workday", "url": "https://walmart.wd5.myworkdayjobs.com/WalmartExternal", "keywords": SWE_KEYWORDS},
    {"name": "Salesforce", "ats": "workday", "url": "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site", "keywords": SWE_KEYWORDS},
]

# --- HELPER FUNCTIONS ---
def estimate_yoe(title):
    t = title.lower()
    if any(x in t for x in ["iii", "lead", "staff", "principal", "manager", "architect"]):
        return "Senior/5+"
    elif any(x in t for x in ["ii", "mid", "senior", "sr"]):
        return "Mid/2-5"
    elif any(x in t for x in ["i", "junior", "jr", "entry", "intern", "new grad", "fresher"]):
        return "Entry/0-2"
    return "NA"

def format_time_ist(raw_time):
    dt = datetime.now(timezone.utc)
    precision = "current"

    if raw_time:
        if isinstance(raw_time, (int, float)):
            val = raw_time / 1000.0 if raw_time > 20000000000 else raw_time
            dt = datetime.fromtimestamp(val, tz=timezone.utc)
            precision = "seconds"
        elif isinstance(raw_time, str):
            raw_str = raw_time.strip()

            if raw_str.lower().startswith("posted"):
                return raw_str.title(), "N/A"

            try:
                dt = datetime.fromisoformat(raw_str.replace("Z", "+00:00"))
                precision = "seconds"
            except ValueError:
                try:
                    dt = datetime.strptime(raw_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                    precision = "minutes"
                except ValueError:
                    try:
                        dt = datetime.strptime(raw_str, "%Y-%m-%d %H").replace(tzinfo=timezone.utc)
                        precision = "hours"
                    except ValueError:
                        try:
                            dt = datetime.strptime(raw_str, "%B %d, %Y").replace(tzinfo=timezone.utc)
                            precision = "date"
                        except ValueError:
                            try:
                                dt = datetime.strptime(raw_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                precision = "date"
                            except ValueError:
                                pass 

    tz_ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt.astimezone(tz_ist)
    day_formatted = dt_ist.strftime("%A")

    if precision == "seconds":
        time_formatted = dt_ist.strftime("%I:%M:%S %p %d %b")
    elif precision == "minutes":
        time_formatted = dt_ist.strftime("%I:%M %p %d %b")
    elif precision == "hours":
        time_formatted = dt_ist.strftime("%I %p %d %b")
    elif precision == "date":
        time_formatted = dt_ist.strftime("Date Only: %d %b")
    else:
        time_formatted = dt_ist.strftime("%I:%M:%S %p %d %b CUR")

    return time_formatted, day_formatted

# --- NOTIFICATION ENGINE ---
def send_telegram_alert(company, title, url, location, time_posted, day_posted, job_id, yoe):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"🚨 [LOCAL ALERT] {company}: {title}")
        return

    header = f"🚨 **New Job : {company} | {title}**"
    body = (
        f"**🏢Company:** {company}\n"
        f"**💼Role:** {title}\n"
        f"**🕑Time posted:** {time_posted}\n"
        f"**-----------------------------**\n"
        f"**🌏Location:** {location}\n"
        f"**📅Day Posted:** {day_posted}\n"
        f"**Job Id:** {job_id}\n"
        f"**YOE:** {yoe}\n\n"
        f"**-----------------------------**\n"
        f"**Link:** [Apply Here]({url})"
    )

    message = f"{header}\n\n{body}"
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    try:
        requests.post(api_url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

# --- SCRAPER MODULES ---
def scrape_greenhouse(target):
    jobs = []
    url = f"https://boards-api.greenhouse.io/v1/boards/{target['id']}/jobs"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            for j in response.json().get("jobs", []):
                jobs.append({
                    "id": str(j["id"]),
                    "title": j.get("title", "Unknown"),
                    "url": j.get("absolute_url", ""),
                    "location": j.get("location", {}).get("name", "Remote/Unspecified"),
                    "raw_time": j.get("updated_at", ""),
                })
    except Exception as e:
        print(f"Error scraping Greenhouse for {target['name']}: {e}")
    return jobs

def scrape_lever(target):
    jobs = []
    url = f"https://api.lever.co/v0/postings/{target['id']}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            for j in response.json():
                jobs.append({
                    "id": str(j["id"]),
                    "title": j.get("text", "Unknown"),
                    "url": j.get("hostedUrl", ""),
                    "location": j.get("categories", {}).get("location", "Remote/Unspecified"),
                    "raw_time": j.get("createdAt", ""),
                })
    except Exception as e:
        print(f"Error scraping Lever for {target['name']}: {e}")
    return jobs

def scrape_amazon(target):
    jobs = []
    url = "https://www.amazon.jobs/en/search.json"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    base_query = target["keywords"][0] if target["keywords"] else ""
    params = {"base_query": base_query, "country": target.get("country", "IND"), "result_limit": 10, "sort": "recent"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 200:
            for j in response.json().get("jobs", []):
                jobs.append({
                    "id": str(j.get("id_icims", j.get("id"))),
                    "title": j.get("title", "Unknown"),
                    "url": "https://www.amazon.jobs" + j.get("job_path", ""),
                    "location": j.get("normalized_location", "India"),
                    "raw_time": j.get("posted_date", ""),
                })
    except Exception as e:
        print(f"Error scraping Amazon: {e}")
    return jobs

def scrape_workday(target):
    """Hits the hidden Workday JSON API and parses exact URLs and IDs."""
    jobs = []
    parsed_uri = urlparse(target["url"])
    domain = f"{parsed_uri.scheme}://{parsed_uri.netloc}"
    tenant = parsed_uri.netloc.split(".")[0]
    
    # Robust portal extraction (handles URLs with or without /en-US/)
    path_parts = [p for p in parsed_uri.path.split("/") if p]
    if "en-US" in path_parts:
        path_parts.remove("en-US")
    portal = path_parts[0] if path_parts else ""

    api_url = f"{domain}/wday/cxs/{tenant}/{portal}/jobs"
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    payload = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            for job in response.json().get("jobPostings", []):
                raw_href = job.get("externalPath", "")
                if raw_href:
                    # Strip query parameters (?locations=...)
                    clean_href = raw_href.split("?")[0]
                    
                    # Construct the exact URL structure Workday's UI expects
                    full_url = f"{domain}/en-US/{portal}{clean_href}"
                    
                    # Regex to extract clean Requisition ID (e.g., R-2435849 or REQ-123)
                    slug = clean_href.split("/")[-1]
                    req_match = re.search(r'((?:R|REQ)-?\d+.*)', slug, re.IGNORECASE)
                    job_id = req_match.group(1).upper() if req_match else slug

                    location = job.get("locationsText", "Remote/Unspecified")
                    raw_time = job.get("postedOn", "")

                    jobs.append({
                        "id": job_id,
                        "title": job.get("title", "Unknown"),
                        "url": full_url,
                        "location": location,
                        "raw_time": raw_time,
                    })
    except Exception as e:
        print(f"Error scraping Workday API for {target['name']}: {e}")

    return jobs

# --- CORE LOGIC ---
def is_relevant(title, keywords, excluded_keywords):
    title_lower = title.lower()
    
    # 1. Check exclusions first (Fail Fast)
    if excluded_keywords:
        if any(ex.lower() in title_lower for ex in excluded_keywords):
            return False # Immediately reject the job
            
    # 2. Check inclusions
    if not keywords:
        return True
    return any(k.lower() in title_lower for k in keywords)

def main():
    print("Initiating scan...")
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

    state_changed = False
    scrapers = {
        "greenhouse": scrape_greenhouse,
        "lever": scrape_lever,
        "amazon": scrape_amazon,
        "workday": scrape_workday,
    }

    for target in TARGETS:
        company_name = target["name"]
        ats_type = target["ats"]

        if ats_type not in scrapers:
            continue

        current_jobs = scrapers[ats_type](target)
        if company_name not in state:
            state[company_name] = []

        for job in current_jobs:
            if job["id"] not in state[company_name]:
                if is_relevant(job["title"], target.get("keywords", []), EXCLUDED_KEYWORDS) and is_india(job["location"]):
                    time_posted, day_posted = format_time_ist(job["raw_time"])
                    yoe = estimate_yoe(job["title"])

                    send_telegram_alert(
                        company=company_name,
                        title=job["title"],
                        url=job["url"],
                        location=job["location"],
                        time_posted=time_posted,
                        day_posted=day_posted,
                        job_id=job["id"],
                        yoe=yoe,
                    )

                state[company_name].append(job["id"])
                state_changed = True

        time.sleep(1)

    if state_changed:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
        print("State updated.")

if __name__ == "__main__":
    main()
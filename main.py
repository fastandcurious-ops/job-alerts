import requests
import json
import os
import time
from datetime import datetime, timezone, timedelta

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
STATE_FILE = "seen_jobs.json"

SWE_KEYWORDS = [
    "software engineer", "sde", "developer", "programmer", 
    "backend", "frontend", "fullstack", "full stack", 
    "member of technical staff", "mts", "technology analyst", 
    "tech analyst", "technical associate", "associate", 
    "c++", "node", "react", "javascript", "typescript", "python", 
    "software", "software developer", "swe", "software development engineer",
    "technical"
]

def is_india(location_str):
    """Ensures the job is located in an Indian tech hub."""
    if not location_str:
        return False
    loc = location_str.lower()
    indian_hubs = [
        "india", "ind", "blr", "bengaluru", "bangalore", 
        "delhi", "ncr", "new delhi", "gurgaon", "gurugram", "noida", 
        "mumbai", "bombay", "hyderabad", "pune", "chennai", "madras", 
        "kolkata", "ahmedabad", "remote - in", "remote-in", "del", "blr",
        "mum", "hyd", "pune", "chen", "kolk", "ahmd", 
        "remote (india)", "remote (in)", "remote india", "remote"
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
    
    # Lever Configurations
    {"name": "Revolut", "ats": "lever", "id": "revolut", "keywords": SWE_KEYWORDS},
    {"name": "Paytm", "ats": "lever", "id": "paytm", "keywords": SWE_KEYWORDS}, 
    {"name": "Perfios", "ats": "lever", "id": "perfios", "keywords": SWE_KEYWORDS},
    {"name": "PolicyBazaar", "ats": "lever", "id": "policybazaar", "keywords": SWE_KEYWORDS},
    {"name": "BizNext", "ats": "lever", "id": "biznext", "keywords": SWE_KEYWORDS},
    {"name": "Jumbotail", "ats": "lever", "id": "jumbotail", "keywords": SWE_KEYWORDS},
]

# --- HELPER FUNCTIONS ---
def estimate_yoe(title):
    """Attempts to guess seniority based on standard job titles to avoid heavy description parsing."""
    t = title.lower()
    if any(x in t for x in ["iii", "lead", "staff", "principal", "manager", "architect"]):
        return "Senior/5+"
    elif any(x in t for x in ["ii", "mid", "senior", "sr"]):
        return "Mid/2-5"
    elif any(x in t for x in ["i", "junior", "jr", "entry", "intern", "new grad", "fresher"]):
        return "Entry/0-2"
    return "NA"

def format_time_ist(raw_time):
    """Universal, ATS-agnostic time parser that cascades through precision levels."""
    dt = datetime.now(timezone.utc)
    precision = "current"
    
    if raw_time:
        if isinstance(raw_time, (int, float)):
            # Epoch timestamps inherently have second/millisecond precision
            val = raw_time / 1000.0 if raw_time > 20000000000 else raw_time
            dt = datetime.fromtimestamp(val, tz=timezone.utc)
            precision = "seconds"
        elif isinstance(raw_time, str):
            raw_str = raw_time.strip()
            
            # 1. Try full ISO format (Seconds precision)
            try:
                dt = datetime.fromisoformat(raw_str.replace('Z', '+00:00'))
                precision = "seconds"
            except ValueError:
                # 2. Try Date + Time without seconds (Minutes precision)
                try:
                    dt = datetime.strptime(raw_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
                    precision = "minutes"
                except ValueError:
                    # 3. Try Date + Hour only (Hours precision)
                    try:
                        dt = datetime.strptime(raw_str, "%Y-%m-%d %H").replace(tzinfo=timezone.utc)
                        precision = "hours"
                    except ValueError:
                        # 4. Try Date only formats
                        try:
                            # Amazon's format
                            dt = datetime.strptime(raw_str, "%B %d, %Y").replace(tzinfo=timezone.utc)
                            precision = "date"
                        except ValueError:
                            try:
                                # Standard Date format
                                dt = datetime.strptime(raw_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                                precision = "date"
                            except ValueError:
                                pass # 5. Fall through to "current"

    # Convert to IST (UTC + 5:30)
    tz_ist = timezone(timedelta(hours=5, minutes=30))
    dt_ist = dt.astimezone(tz_ist)
    day_formatted = dt_ist.strftime("%A")
    
    # Apply the requested formatting hierarchy
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

    # The Notification Header
    header = f"🚨 **New Job : {company} | {time_posted} | {yoe} | {title}**"
    
    # The Notification Body
    body = (
        f"**🏢Company:** {company}\n"
        f"**💼Role:** {title}\n"
        f"**🌏Location:** {location}\n"
        f"**🕑Time posted:** {time_posted}\n"
        f"**📅Day Posted:** {day_posted}\n"
        f"**Job Id:** {job_id}\n"
        f"**YOE:** {yoe}\n\n"
        f"**Link:** [Apply Here]({url})"
    )
    
    message = f"{header}\n\n{body}"

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    
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
                    "raw_time": j.get("updated_at", "")
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
                    "raw_time": j.get("createdAt", "")
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
                    "raw_time": j.get("posted_date", "")
                })
    except Exception as e:
         print(f"Error scraping Amazon: {e}")
    return jobs

# --- CORE LOGIC ---
def is_relevant(title, keywords):
    if not keywords: return True
    return any(k.lower() in title.lower() for k in keywords)

def main():
    print("Initiating scan...")
    state = {}
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            state = json.load(f)

    state_changed = False
    scrapers = {"greenhouse": scrape_greenhouse, "lever": scrape_lever, "amazon": scrape_amazon}

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
                # Now checking BOTH the title and the geographic location
                if is_relevant(job["title"], target.get("keywords", [])) and is_india(job["location"]):
                    
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
                        yoe=yoe
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
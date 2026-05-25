import requests
import json
import os
import time

# --- CONFIGURATION ---
# Put your webhook URL here (Slack, Discord, Teams, etc.)
WEBHOOK_URL = "YOUR_DISCORD_OR_SLACK_WEBHOOK_URL_HERE"
STATE_FILE = "seen_jobs.json"

# Define the companies you want to track and their ATS type.
# You can usually find the 'company_id' by looking at the URL of their job board 
# (e.g., boards.greenhouse.io/stripe -> id is 'stripe')
COMPANIES = [
    {"name": "Stripe", "ats": "greenhouse", "id": "stripe"},
    {"name": "Figma", "ats": "lever", "id": "figma"},
    # Add more here!
]

# Optional: Filter by keywords to avoid getting pinged for every single role
KEYWORDS = ["data engineer", "data analyst", "business analyst", "product analyst", "blockchain developer", "blockchain analyst", "crypto analyst" ]

# --- CORE LOGIC ---

def load_seen_jobs():
    """Loads the database of jobs we've already notified you about."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_seen_jobs(seen_jobs):
    """Saves the database to disk."""
    with open(STATE_FILE, "w") as f:
        json.dump(seen_jobs, f, indent=4)

def send_alert(company_name, job_title, job_url):
    """Sends a push notification via Webhook."""
    print(f"🚨 NEW JOB FOUND: {company_name} - {job_title}")
    
    # Example using Discord Webhook format
    payload = {
        "content": f"🚀 **New Job at {company_name}!**\n**Role:** {job_title}\n**Link:** {job_url}"
    }
    
    if WEBHOOK_URL != "YOUR_DISCORD_OR_SLACK_WEBHOOK_URL_HERE":
        requests.post(WEBHOOK_URL, json=payload)
    else:
        print("Webhook not configured, skipping push notification.")

def check_greenhouse(company_id):
    """Fetches jobs from Greenhouse's hidden API."""
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_id}/jobs"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for job in data.get("jobs", []):
            jobs.append({
                "id": str(job["id"]),
                "title": job["title"],
                "url": job["absolute_url"]
            })
        return jobs
    except Exception as e:
        print(f"Error fetching Greenhouse for {company_id}: {e}")
        return []

def check_lever(company_id):
    """Fetches jobs from Lever's API."""
    url = f"https://api.lever.co/v0/postings/{company_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        jobs = []
        for job in data:
            jobs.append({
                "id": str(job["id"]),
                "title": job["text"],
                "url": job["hostedUrl"]
            })
        return jobs
    except Exception as e:
        print(f"Error fetching Lever for {company_id}: {e}")
        return []

def is_relevant_job(title):
    """Checks if the job title matches your keywords."""
    if not KEYWORDS:
        return True # If no keywords, everything is relevant
    title_lower = title.lower()
    return any(keyword.lower() in title_lower for keyword in KEYWORDS)

def main():
    print("Starting job scan...")
    seen_jobs = load_seen_jobs()
    new_jobs_found = False

    for company in COMPANIES:
        print(f"Scanning {company['name']}...")
        current_jobs = []
        
        if company["ats"] == "greenhouse":
            current_jobs = check_greenhouse(company["id"])
        elif company["ats"] == "lever":
            current_jobs = check_lever(company["id"])
        else:
            print(f"Unsupported ATS: {company['ats']}")
            continue

        company_memory = seen_jobs.get(company["name"], [])
        new_company_memory = company_memory.copy()

        for job in current_jobs:
            if job["id"] not in company_memory:
                # We found a new job!
                if is_relevant_job(job["title"]):
                    send_alert(company["name"], job["title"], job["url"])
                
                # Add to memory so we don't alert again
                new_company_memory.append(job["id"])
                new_jobs_found = True

        seen_jobs[company["name"]] = new_company_memory
        
        # Be polite to APIs, add a small sleep
        time.sleep(1) 

    if new_jobs_found:
        save_seen_jobs(seen_jobs)
        print("Scan complete. State updated.")
    else:
        print("Scan complete. No new relevant jobs.")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
import os
import time
import json
import re
import asyncio
import telegram
from telegram.helpers import escape_markdown
from telegram.constants import ParseMode
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv
from selenium.webdriver.chrome.service import Service
# Load environment variables
load_dotenv()
USERNAME = os.getenv("SUP_USER")
PASSWORD = os.getenv("SUP_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# URLs
LOGIN_URL = "https://app.joinsuperset.com/students/login"
HOME_URL = "https://app.joinsuperset.com/students"
JOB_PROFILE_URL = "https://app.joinsuperset.com/students/jobprofiles"

# Cache file
DATA_FILE = "jobs_seen.json"

# ─────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────
async def _send_async(message: str) -> None:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    escaped = escape_markdown(message, version=2)
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=escaped,
        parse_mode=ParseMode.MARKDOWN_V2
    )

def notify_telegram(message: str) -> None:
    asyncio.run(_send_async(message))

# ─────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────
def normalize(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\.*$", "", text)
    return text

def clean_dynamic_text(text: str) -> str:
    return re.sub(
        r"\s*·\s*(?:just now|\d+\s+\w+\s+ago|a[n]?\s+\w+\s+ago)",
        "", text, flags=re.IGNORECASE
    ).strip()

# ─────────────────────────────────────────────
# CACHE HANDLING
# ─────────────────────────────────────────────
def load_seen():
    if not os.path.exists(DATA_FILE):
        return [set(), set()]
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            seen_home = set(normalize(x) for x in data[0]) if len(data) > 0 else set()
            seen_job = set(normalize(x) for x in data[1]) if len(data) > 1 else set()
            return [seen_home, seen_job]
    except Exception:
        return [set(), set()]

def save_seen(home_jobs, job_jobs):
    home_headers = sorted(set(job["header"] for job in home_jobs))
    job_headers = sorted(set(job["header"] for job in job_jobs))
    with open(DATA_FILE, "w") as f:
        json.dump([home_headers, job_headers], f)

# ─────────────────────────────────────────────
# BROWSER SETUP
# ─────────────────────────────────────────────

def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")   # Use the new headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # This uses Selenium Manager to automatically manage the ChromeDriver
    return webdriver.Chrome(options=chrome_options)


# ─────────────────────────────────────────────
# FETCH JOBS FROM HOME TAB
# ─────────────────────────────────────────────
def fetch_jobs():
    driver = init_driver()
    driver.get(LOGIN_URL)
    time.sleep(3)

    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(USERNAME)
    pwd = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd.send_keys(PASSWORD)
    pwd.send_keys(Keys.RETURN)
    time.sleep(5)

    cards = driver.find_elements(By.CSS_SELECTOR, "div.MuiBox-root.css-mfpd05")
    job_data = []

    for card in cards:
        try:
            header_el = card.find_element(By.CSS_SELECTOR, "div.feedHeader > p.text-base.font-bold.text-dark")
            header = normalize(clean_dynamic_text(header_el.text.strip()))

            title_el = card.find_element(By.CSS_SELECTOR, ".flex.gap-4.items-center")
            title = title_el.text.strip()

            content_el = card.find_element(
                By.CSS_SELECTOR,
                ".m-0.sm\\:m-3.lg\\:mt-4.lg\\:mr-16.lg\\:mb-5.lg\\:ml-14"
            )
            content = content_el.text.strip()

            full_text = f"{title}\n{content}"
            cleaned = clean_dynamic_text(full_text)

            if header:
                job_data.append({"header": header, "full_content": cleaned})
        except Exception:
            continue

    driver.quit()
    return job_data

# ─────────────────────────────────────────────
# FETCH JOB PROFILES TAB
# ─────────────────────────────────────────────
def fetch_job_profiles():
    driver = init_driver()
    driver.get(LOGIN_URL)
    time.sleep(3)

    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(USERNAME)
    pwd = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd.send_keys(PASSWORD)
    pwd.send_keys(Keys.RETURN)
    time.sleep(5)

    driver.get(JOB_PROFILE_URL)
    time.sleep(5)

    job_profiles = []

    # Find all job sections with stable class (ignore dynamic id)
    panels = driver.find_elements(By.CSS_SELECTOR, "div.MuiTabPanel-root")

    for panel in panels:
        try:
            blocks = panel.find_elements(By.CSS_SELECTOR, "div.p-4.flex")

            for block in blocks:
                try:
                    # Extract job title (main header)
                    header_el = block.find_element(By.CSS_SELECTOR, "div.w-full > p")
                    header = normalize(header_el.text)
                    if header:
                        job_profiles.append({"header": header})
                except Exception as e:
                    print(f"⛔ Error parsing job block: {e}")
                    continue
        except Exception as e:
            print(f"⚠️ Error in panel: {e}")
            continue

    driver.quit()

    print(f"✅ Found {len(job_profiles)} job profiles.")
    return job_profiles


# ─────────────────────────────────────────────
# MAIN LOGIC
# ─────────────────────────────────────────────
def main():
    seen_home, seen_jobs = load_seen()

    fetched_home = fetch_jobs()
    fetched_jobs = fetch_job_profiles()

    new_home = [job for job in fetched_home if job["header"] not in seen_home]
    new_jobs = [job for job in fetched_jobs if job["header"] not in seen_jobs]

    if new_home:
        for job in new_home:
            msg = f"🆕 New job posted (Home):\n{job['full_content']}\n\nDetails 👉 {HOME_URL}"
            notify_telegram(msg)

    if new_jobs:
        for job in new_jobs:
            msg = f"🆕 New job posted (Job Profile):\n{job['header']}\n\nCheck profiles 👉 {JOB_PROFILE_URL}"
            notify_telegram(msg)

    if new_home or new_jobs:
        save_seen(fetched_home, fetched_jobs)
    else:
        notify_telegram("Nothing new here 🙂")

# ─────────────────────────────────────────────
if __name__ == "__main__":
    main()

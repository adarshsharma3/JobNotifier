#!/usr/bin/env python3
import os
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import telegram
import asyncio
from selenium.webdriver.chrome.service import Service
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

USERNAME = os.getenv("SUP_USER")
PASSWORD = os.getenv("SUP_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ==== CONFIG ====

# https://app.joinsuperset.com/students
LOGIN_URL = "https://app.joinsuperset.com/students/login"

DATA_FILE = "jobs_seen.json"
# ================


async def _send_async(message: str) -> None:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

def notify_telegram(message: str) -> None:
    """
    Synchronous wrapper you can call anywhere in your script.
    It spins up a fresh asyncio loop, sends the message, then closes.
    """
    asyncio.run(_send_async(message))

# Save seen jobs
def save_seen(jobs):
    with open(DATA_FILE, "w") as f:
        json.dump(jobs, f)

# Load previously seen jobs
def load_seen():
    if not os.path.exists(DATA_FILE):
        return set()
    with open(DATA_FILE, "r") as f:
        return set(json.load(f))

# Initialize Chrome
def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # No browser GUI
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    service = Service("/usr/local/bin/chromedriver")  # 👈 wrap the driver path in Service

    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# Login and fetch jobs
def fetch_jobs():
    driver = init_driver()
    driver.get(LOGIN_URL)
    time.sleep(3)

    # Enter email and password
    email_field = driver.find_element(By.CSS_SELECTOR, "input[type='email']")
    password_field = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    email_field.send_keys(USERNAME)
    password_field.send_keys(PASSWORD)
    password_field.send_keys(Keys.RETURN)

    time.sleep(5)  # wait for dashboard

    # Get job cards
    jobs = driver.find_elements(By.CSS_SELECTOR, "div.MuiBox-root.css-mfpd05")

    job_titles = []
    for job in jobs:
        try:
            title = job.text.strip()
            if title:
                job_titles.append(title)
        except:
            continue

    driver.quit()
    return job_titles

# Main logic
def main():
    seen_jobs = load_seen()
    current_jobs = set(fetch_jobs())

    new_jobs = current_jobs - seen_jobs
    if new_jobs:
        for job in new_jobs:
            notify_telegram(f"🆕 New job posted:\n\n{job}")
        save_seen(list(current_jobs))
    else:
        notify_telegram(f"Nothing new here ")
        print("No new jobs.")


if __name__ == "__main__":
    main()

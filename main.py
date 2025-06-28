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
import html

# Load environment variables from .env
load_dotenv()

USERNAME = os.getenv("SUP_USER")
PASSWORD = os.getenv("SUP_PASS")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# URLs and file path
LOGIN_URL = "https://app.joinsuperset.com/students/login"
HOME_URL = "https://app.joinsuperset.com/students"
DATA_FILE = "jobs_seen.json"

# 📬 Telegram send message (async)
async def _send_async(message: str) -> None:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    escaped_message = escape_markdown(message, version=2)
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=escaped_message,
        parse_mode=ParseMode.MARKDOWN_V2
    )

# 🚀 Synchronous wrapper for Telegram
def notify_telegram(message: str) -> None:
    asyncio.run(_send_async(message))

# 🧼 Normalize job text
def normalize(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)  # Normalize whitespace
    text = re.sub(r"\.*$", "", text)  # Remove trailing periods
    return text

# 💾 Save seen headers only
def save_seen(jobs):
    headers = [job["header"] for job in jobs]
    with open(DATA_FILE, "w") as f:
        json.dump(sorted(headers), f)

# 📖 Load seen headers
def load_seen():
    if not os.path.exists(DATA_FILE):
        return set()
    try:
        with open(DATA_FILE, "r") as f:
            data = f.read().strip()
            if not data:
                return set()
            return set(normalize(job) for job in json.loads(data))
    except json.JSONDecodeError:
        return set()

# 🧭 Setup headless Chrome
def init_driver():
    chrome_opts = Options()
    chrome_opts.add_argument("--headless=new")
    chrome_opts.add_argument("--no-sandbox")
    chrome_opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_opts)

# 🧲 Clean dynamic text
def clean_dynamic_text(text: str) -> str:
    return re.sub(
        r"\s*·\s*(?:just now|\d+\s+\w+\s+ago|a[n]?\s+\w+\s+ago)",
        "",
        text,
        flags=re.IGNORECASE
    ).strip()

# 🧲 Fetch jobs
def fetch_jobs():
    driver = init_driver()
    driver.get(LOGIN_URL)
    time.sleep(3)

    # Log in
    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(USERNAME)
    pwd = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd.send_keys(PASSWORD)
    pwd.send_keys(Keys.RETURN)
    time.sleep(5)

    cards = driver.find_elements(By.CSS_SELECTOR, "div.MuiBox-root.css-mfpd05")
    job_data = []

    for card in cards:
        try:
            # ✅ Extract header separately
            header_el = card.find_element(By.CSS_SELECTOR, "div.feedHeader > p.text-base.font-bold.text-dark")
            header = clean_dynamic_text(header_el.text.strip())
            header = normalize(header)

            # ✅ Extract full content as before
            title_el = card.find_element(By.CSS_SELECTOR, ".flex.gap-4.items-center")
            title = title_el.text.strip()

            content_el = card.find_element(
                By.CSS_SELECTOR,
                ".m-0.sm\\:m-3.lg\\:mt-4.lg\\:mr-16.lg\\:mb-5.lg\\:ml-14",
            )
            content = content_el.text.strip()

            full_text = f"{title}\n{content}"
            cleaned_full_text = clean_dynamic_text(full_text)

            if header:
                job_data.append({
                    "header": header,
                    "full_content": cleaned_full_text
                })

        except Exception:
            continue

    driver.quit()
    return job_data

# 🧠 Main logic
def main():
    seen_headers = load_seen()
    fetched_jobs = fetch_jobs()

    # Filter new jobs based on header
    new_jobs = [job for job in fetched_jobs if job["header"] not in seen_headers]

    if new_jobs:
        for job in new_jobs:
            message = f"🆕 New job posted:\n{job['full_content']}\n\nFind more details here 👉 {HOME_URL}"
            notify_telegram(message)
        save_seen(fetched_jobs)
    else:
        notify_telegram("Nothing new here 🙂")

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import time
import json
import re
import asyncio
import telegram

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from dotenv import load_dotenv

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
    await bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message,
        parse_mode="Markdown"
    )


# 🚀 Synchronous wrapper for Telegram
def notify_telegram(message: str) -> None:
    asyncio.run(_send_async(message))


# 🧼 Normalize job text
def normalize(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)  # Replace all whitespace (newline, tabs, etc.) with single space
    return text


# 💾 Save seen jobs
def save_seen(jobs):
    with open(DATA_FILE, "w") as f:
        json.dump(sorted(list(jobs)), f)


# 📖 Load seen jobs
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


# 🧲 Scrape jobs
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
    job_texts = []

    for card in cards:
        try:
            title_el = card.find_element(By.CSS_SELECTOR, ".flex.gap-4.items-center")
            content_el = card.find_element(By.CSS_SELECTOR,
                                           ".m-0.sm\\:m-3.lg\\:mt-4.lg\\:mr-16.lg\\:mb-5.lg\\:ml-14")

            title = title_el.text.strip()
            content = content_el.text.strip()

            if title and content:
                # Store raw, clean text without Markdown
                job_texts.append(normalize(f"{title}\n{content}"))
        except Exception:
            continue

    driver.quit()
    return job_texts


# 🧠 Main logic
def main():
    seen_jobs = load_seen()
    current_jobs_raw = fetch_jobs()
    current_jobs = set(normalize(job) for job in current_jobs_raw)

    new_jobs = current_jobs - seen_jobs

    if new_jobs:
        for job in new_jobs:
            notify_telegram(
                f"🆕 New job posted:\n\n{job}\n\nFind more details here 👉 {HOME_URL}"
            )
        save_seen(current_jobs)
    else:
        notify_telegram("Nothing new here 🙂")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import os
import json
import time
import asyncio
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
import telegram
from dotenv import load_dotenv

# ── ENV ──────────────────────────────────────────────────────────────
load_dotenv()

USERNAME        = os.getenv("SUP_USER")
PASSWORD        = os.getenv("SUP_PASS")
TELEGRAM_TOKEN  = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHATID = os.getenv("TELEGRAM_CHAT_ID")

LOGIN_URL = "https://app.joinsuperset.com/students/login"
HOME_URL  = "https://app.joinsuperset.com/students"
DATA_FILE = Path("jobs_seen.json")

# ── TELEGRAM HELPERS ────────────────────────────────────────────────
async def _send_async(msg: str) -> None:
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    await bot.send_message(chat_id=TELEGRAM_CHATID, text=msg, parse_mode="Markdown")

def notify(msg: str) -> None:
    asyncio.run(_send_async(msg))

# ── LOAD / SAVE SEEN TITLES ─────────────────────────────────────────
def load_seen_titles() -> set[str]:
    if not DATA_FILE.exists():
        return set()
    try:
        raw = DATA_FILE.read_text().strip()
        return set(json.loads(raw)) if raw else set()
    except json.JSONDecodeError:
        return set()

def save_seen_titles(titles: set[str]) -> None:
    DATA_FILE.write_text(json.dumps(list(titles), indent=2))

# ── SELENIUM DRIVER ────────────────────────────────────────────────
def init_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # Selenium ≥ 4.6 will auto‑manage chromedriver
    return webdriver.Chrome(options=opts)

# ── SCRAPER ─────────────────────────────────────────────────────────
def fetch_jobs() -> list[dict]:
    """
    Returns a list of dicts: [{"title": "...", "content": "..."}]
    """
    driver = init_driver()
    driver.get(LOGIN_URL)
    time.sleep(3)

    driver.find_element(By.CSS_SELECTOR, "input[type='email']").send_keys(USERNAME)
    pwd = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
    pwd.send_keys(PASSWORD)
    pwd.send_keys(Keys.RETURN)
    time.sleep(5)

    cards = driver.find_elements(By.CSS_SELECTOR, "div.MuiBox-root.css-mfpd05")
    jobs: list[dict] = []

    for card in cards:
        try:
            title = card.find_element(By.CSS_SELECTOR,
                     ".flex.gap-4.items-center").text.strip()

            content = card.find_element(
                     By.CSS_SELECTOR,
                     ".m-0.sm\\:m-3.lg\\:mt-4.lg\\:mr-16.lg\\:mb-5.lg\\:ml-14"
                     ).text.strip()

            if title and content:
                jobs.append({"title": title, "content": content})
        except Exception:
            continue   # skip card if selector not found

    driver.quit()
    return jobs

# ── MAIN ────────────────────────────────────────────────────────────
def main() -> None:
    seen_titles   = load_seen_titles()
    fetched_jobs  = fetch_jobs()
    current_titles = {job["title"] for job in fetched_jobs}

    new_titles = current_titles - seen_titles

    if new_titles:
        for job in fetched_jobs:
            if job["title"] in new_titles:
                message = (
                    f"🆕 *New job posted*\n\n"
                    f"*{job['title']}*\n{job['content']}\n\n"
                    f"[Find more details here]({HOME_URL})"
                )
                notify(message)
        # update stored titles
        save_seen_titles(current_titles)
    else:
        notify("Nothing new here 🙂")

if __name__ == "__main__":
    main()

# Superset Job Notifier Bot

A Python-based bot that scrapes job listings from [Superset](https://app.joinsuperset.com) and sends new job alerts to subscribed users via Telegram.

---

## 🚀 Features

- Scrapes jobs from your Superset student login.
- Sends new job alerts to multiple Telegram users using a bot.
- Keeps track of already-seen jobs.
- Easily schedule it to run periodically using `cron`.
- Supports `.env` file for secure credentials.
- Supports broadcasting to multiple subscribers (via `subscribers.json`).

---

## 📦 Requirements

- Python 3.9+
- Google Chrome
- ChromeDriver (same version as Chrome)
- Telegram bot token from [BotFather](https://t.me/BotFather)

---

## 📁 Setup Instructions

1. **Clone the repo**

   ```bash
   git clone https://github.com/your-username/superset-notifier-bot.git
   cd superset-notifier-bot

    Install dependencies

python3 -m venv venv
source venv/bin/activate
pip install -r Requirements.txt

Download and place chromedriver

Ensure you download the correct version from:
👉 https://chromedriver.chromium.org/downloads

Then make it executable and place it:

chmod +x chromedriver
sudo mv chromedriver /usr/local/bin/

Create your .env file

# .env
SUP_USER=your_superset_email@example.com
SUP_PASS=your_superset_password
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=You can find your chat_id by sending a message to your bot and calling:

https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
(bot token can be get using fatherbot)

Run the bot

    python3 main.py

🔁 Schedule to Run Periodically

To make the bot check jobs every few hours, use cron.

    Open your crontab:

crontab -e

Add a cron job (e.g., every 4 hours):

0 */4 * * * cd /full/path/to/project && /full/path/to/venv/bin/python3 main.py >> logs.txt 2>&1

    Replace paths as per your machine.

    This will append logs to logs.txt.
# Facebook Marketplace Bot

An automated bot that monitors Facebook Marketplace for new listings matching your search criteria and instantly sends you an email notification with the ad's title, price, post time, and a direct link.

---

## Features

- Searches Marketplace by keyword, category, and price range
- Flexible time filter — alert on ads posted within any number of seconds / minutes / hours / days / weeks
- Sends clean HTML email notifications (title, price, posted time, ad link)
- Runs continuously, re-checking at a configurable interval
- Writes timestamped log files for every run
- Can be packaged as a standalone `.exe` with PyInstaller

---

## Quick Start

### 1. Clone / download the project

```powershell
git clone <repo-url>
cd fb_bot
```

### 2. Create and activate a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create your config file

Copy the example config and fill in your own values:

```powershell
copy config.json.example config.json
```

Then open `config.json` and edit the values (see [Configuration Reference](#configuration-reference) below).

> Never commit `config.json` to version control — it contains your passwords.

### 5. Run the bot

```powershell
python fb_marketplace_bot.py
```

A browser window will open and ask you to log in to Facebook manually. Once logged in, the bot takes over automatically.

---

## Configuration Reference

All settings live in `config.json`. Use `config.json.example` as a template.

### Facebook Credentials

| Key | Type | Description |
|-----|------|-------------|
| `FACEBOOK_EMAIL` | string | Your Facebook login email |
| `FACEBOOK_PASSWORD` | string | Your Facebook password |

### Marketplace Search Filters

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `CATEGORY` | string | `"vehicles"` | Marketplace category slug from the URL: `facebook.com/marketplace/category/<slug>`. Common values: `vehicles`, `electronics`, `furniture`, `clothing`, `garden`, `hobbies`, `toys` |
| `QUERY` | string | `""` | Search keyword (e.g. `"honda"`). Leave as `""` to browse the full category without a keyword |
| `MIN_PRICE` | integer or null | `null` | Minimum price filter. Set to `null` to disable |
| `MAX_PRICE` | integer or null | `null` | Maximum price filter. Set to `null` to disable |

### Time Filter

The bot only sends alerts for ads posted within the window you define:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `TIME_AGO` | integer | `5` | The numeric threshold |
| `TIME_UNIT` | string | `"Day"` | Unit for `TIME_AGO`. Accepted values (case-insensitive, trailing `s` or `*` ignored): `Second`, `Minute`, `Hour`, `Day`, `Week`, `Month`, `Year` |

Examples:

| `TIME_AGO` | `TIME_UNIT` | Effect |
|-----------|------------|--------|
| `30` | `"Minute"` | Ads posted within the last 30 minutes |
| `2` | `"Hour"` | Ads posted within the last 2 hours |
| `1` | `"Day"` | Ads posted within the last 1 day |
| `3` | `"Day"` | Ads posted within the last 3 days |
| `1` | `"Week"` | Ads posted within the last 1 week |

### Bot Scheduling

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `CHECK_INTERVAL` | integer | `60` | How often in seconds the bot re-checks the marketplace after the initial crawl |

### Email Notification (Gmail)

The bot uses Gmail SMTP to send notifications. You must generate a Gmail App Password — your regular Gmail password will not work.

| Key | Type | Description |
|-----|------|-------------|
| `GMAIL_USER` | string | The Gmail address the bot sends from |
| `GMAIL_PASS` | string | Your Gmail App Password (16-character code) |
| `TO_EMAIL` | string | The email address to receive notifications |

#### How to generate a Gmail App Password

1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select Mail as the app and Windows Computer as the device
3. Click Generate and copy the 16-character code
4. Paste it as the value of `GMAIL_PASS`

Requires 2-Step Verification to be enabled on your Google account.

### Logging

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `LOG_PATH` | string or null | `null` | Directory where log files are saved. If `null`, logs are written to the same folder as the script |

Log files are named: `fb_marketplace_bot_YYYYMMDD_HHMMSS.log`

---

## Example config.json

```json
{
    "FACEBOOK_EMAIL": "yourname@gmail.com",
    "FACEBOOK_PASSWORD": "your_facebook_password",

    "CATEGORY": "vehicles",
    "QUERY": "honda",
    "MIN_PRICE": 400000,
    "MAX_PRICE": 2000000,

    "TIME_AGO": 2,
    "TIME_UNIT": "Day",

    "CHECK_INTERVAL": 60,

    "GMAIL_USER": "yourname@gmail.com",
    "GMAIL_PASS": "abcd efgh ijkl mnop",
    "TO_EMAIL": "yourname@gmail.com",

    "LOG_PATH": null
}
```

---

## Email Notification Format

Each matching ad triggers one email:

| Field | Example |
|-------|---------|
| Title | Honda Civic 2005 VTi |
| Price | PKR780,000 |
| Posted | Listed a day ago in Islamabad, Pakistan |
| Ad Link | https://www.facebook.com/marketplace/item/... |

---

## Build a Standalone Executable

Package the bot as a single `.exe` using PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --onefile fb_marketplace_bot.py
```

The executable is created in the `dist/` folder. Place `config.json` in the same directory as the `.exe` before running:

```powershell
dist\fb_marketplace_bot.exe
```

You can also point to a config in a different location:

```powershell
dist\fb_marketplace_bot.exe --config C:\path\to\config.json
```

---

## Project Structure

```
fb_bot/
├── fb_marketplace_bot.py   # Main bot script
├── config.json             # Your config (git-ignored)
├── config.json.example     # Template with all options
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── dist/                   # PyInstaller output (after build)
```

---

## Notes

- ChromeDriver is managed automatically by `webdriver_manager` — no manual download needed.
- The bot opens a real Chrome browser window. Do not close it while the bot is running.
- If Facebook shows a CAPTCHA or extra login step, complete it manually in the browser window.
- `sent_ads` is stored in memory only. Restarting the bot resets it, so you may receive duplicate emails for old ads on the first run. Adjust `TIME_AGO` and `TIME_UNIT` to limit this.
- Keep `config.json` private. Add it to `.gitignore` to avoid accidentally committing credentials.

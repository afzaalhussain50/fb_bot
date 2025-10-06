# Facebook Marketplace Bot

This project is an automated bot for monitoring Facebook Marketplace listings and sending email notifications for new ads matching your criteria.

## Features
- Monitors Facebook Marketplace for new ads
- Filters by category, price range, and search query
- Sends email notifications for new ads
- Configurable via `config.json`
- Logs activity to timestamped log files
- Can be packaged as a single executable

## Setup Instructions

### 1. Create and Activate a Python Virtual Environment

Open a terminal in the project directory and run:

```powershell
python -m venv myenv
myenv\Scripts\activate
```

### 2. Install Requirements

After activating the virtual environment, install dependencies:

```powershell
pip install -r requirements.txt
```

### 3. Configure the Bot

Edit `config.json` to set your credentials and filters:

```json
{
    "FACEBOOK_EMAIL": "your_fb_email",
    "FACEBOOK_PASSWORD": "your_fb_password",
    "CATEGORY": "vehicles",
    "CHECK_INTERVAL": 50,
    "GMAIL_USER": "your_gmail",
    "GMAIL_PASS": "your_gmail_app_password",
    "TO_EMAIL": "recipient_email",
    "LOG_PATH": null,
    "MAX_MINUTES": 2,
    "MIN_PRICE": null,
    "MAX_PRICE": null,
    "QUERY": ""
}
```
- `MIN_PRICE` and `MAX_PRICE`: Set price range (integer values). Leave as `null` to ignore.
- `QUERY`: Search keyword (e.g., "honda"). Leave empty to ignore.
- `CATEGORY`: Facebook Marketplace category (e.g., "vehicles").
- `LOG_PATH`: Directory for log files. If `null`, logs are saved in the script's folder.

### 4. Run the Bot

```powershell
python fb_marketplace_bot.py
```

### 5. Log Files

Log files are created in the directory specified by `LOG_PATH` in `config.json`. If not set, they are created in the same folder as the script or executable. Log files are named like:

```
fb_marketplace_bot_YYYYMMDD_HHMMSS.log
```

### 6. Create a Single Executable

You can package the bot as a single executable using PyInstaller:

```powershell
pip install pyinstaller
pyinstaller --onefile fb_marketplace_bot.py
```

The executable will be created in the `dist` folder. You can run it directly:

```powershell
dist\fb_marketplace_bot.exe
```

## Notes
- Make sure your Gmail account allows app passwords or less secure apps for SMTP.
- ChromeDriver is managed automatically by `webdriver_manager`.
- For best results, keep your config file secure and do not share sensitive credentials.

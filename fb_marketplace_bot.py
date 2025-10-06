
import time
import smtplib
import logging
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import sys
import os
import json

# === CONFIGURATION ===
import argparse

def get_default_config_path():
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.join(os.path.dirname(sys.executable), 'config.json')
    else:
        # Running as script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

parser = argparse.ArgumentParser(description="Facebook Marketplace Bot")
parser.add_argument('--config', type=str, default=None, help='Path to config.json')
args = parser.parse_args()

config_path = args.config if args.config else get_default_config_path()
if not os.path.exists(config_path):
    print(f"[ERROR] config.json not found at {config_path}. Please create it or specify with --config.")
    sys.exit(1)
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

FACEBOOK_EMAIL = config["FACEBOOK_EMAIL"]
FACEBOOK_PASSWORD = config["FACEBOOK_PASSWORD"]
CATEGORY = config.get("CATEGORY", "vehicles")
CHECK_INTERVAL = config["CHECK_INTERVAL"]
MAX_MINUTES = config.get("MAX_MINUTES", 5)
GMAIL_USER = config["GMAIL_USER"]
GMAIL_PASS = config["GMAIL_PASS"]
TO_EMAIL = config["TO_EMAIL"]
MIN_PRICE = config.get("MIN_PRICE")
MAX_PRICE = config.get("MAX_PRICE")
QUERY = config.get("QUERY", "")

def build_marketplace_url():
    base_url = f"https://www.facebook.com/marketplace/category/{CATEGORY}"
    params = []
    # If any filter is provided, switch to search endpoint
    if MIN_PRICE is not None or MAX_PRICE is not None or QUERY:
        base_url = "https://www.facebook.com/marketplace/category/search?"
        if MIN_PRICE is not None and str(MIN_PRICE).strip() != "" and str(MIN_PRICE).lower() != "null":
            params.append(f"minPrice={MIN_PRICE}")
        if MAX_PRICE is not None and str(MAX_PRICE).strip() != "" and str(MAX_PRICE).lower() != "null":
            params.append(f"maxPrice={MAX_PRICE}")
        if QUERY:
            params.append(f"query={QUERY}")
        params.append("exact=false")
        params.append(f"category_id={CATEGORY}")
        return base_url + "&".join(params)
    else:
        return base_url

# === LOGGING ===
from datetime import datetime
if "LOG_PATH" in config and config["LOG_PATH"]:
    log_dir = config["LOG_PATH"]
else:
    if getattr(sys, 'frozen', False):
        log_dir = os.path.dirname(sys.executable)
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
os.makedirs(log_dir, exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = os.path.join(log_dir, f'fb_marketplace_bot_{timestamp}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# === SELENIUM SETUP ===
options = webdriver.ChromeOptions()
# options.add_argument("--headless")  # comment this line to see browser
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def login_to_facebook():
    logging.info("Logging into Facebook...")
    driver.get("https://www.facebook.com/login")
    time.sleep(3)
    driver.find_element(By.ID, "email").send_keys(FACEBOOK_EMAIL)
    driver.find_element(By.ID, "pass").send_keys(FACEBOOK_PASSWORD)
    driver.find_element(By.NAME, "login").click()
    time.sleep(5)

def fetch_ads(sent_ads):
    import re
    from datetime import datetime
    logging.info("Fetching current ads...")
    url = build_marketplace_url()
    logging.info(f"Marketplace URL: {url}")
    driver.get(url)
    time.sleep(5)

    ads = driver.find_elements(By.XPATH, '//a[contains(@href, "/marketplace/item/")]')
    ad_list = []

    for ad in ads:
        try:
            title = ad.text.split('\n')[0]
            link = ad.get_attribute('href')
            # Visit ad detail page to get posted time
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            driver.get(link)
            time.sleep(3)
            posted_time = "unknown"
            try:
                time_elems = driver.find_elements(By.XPATH, "//*[contains(text(),'hour') or contains(text(),'minute') or contains(text(),'day') or contains(text(),'week') or contains(text(),'month') or contains(text(),'year') or contains(text(),'just now') or contains(text(),'second') or contains(text(),'now')]")
                for elem in time_elems:
                    text = elem.text.lower()
                    if re.search(r'(posted|updated|listed|just now|minute|hour|day|week|month|year|second|now)', text):
                        posted_time = elem.text
                        break
            except Exception as e:
                logging.warning(f"Error extracting posted time for {link}: {e}")
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            pt_lower = posted_time.lower()
            include = False
            if 'second' in pt_lower:
                include = True
            elif 'minute' in pt_lower:
                match = re.search(r'(\d+)', pt_lower)
                if match and int(match.group(1)) <= MAX_MINUTES:
                    include = True
            if include and link not in sent_ads:
                try:
                    send_email({link: title})
                    sent_ads.add(link)
                    logging.info(f"Sent email for ad: {title} | {link} | {posted_time}")
                except Exception as e:
                    logging.error(f"Error sending email for ad {link}: {e}", exc_info=True)
            ad_list.append((title, link, posted_time))
        except Exception as e:
            logging.warning(f"Error reading ad: {e}")
            continue
    # Log the first 5 ads' titles, URLs, and posted times
    if ad_list:
        logging.info("First 5 visible ads (title, url, posted time):")
        for t, l, ts in ad_list[:5]:
            logging.info(f"{t} | {l} | {ts}")
    else:
        logging.info("No ads found to log.")
    return

def send_email(new_ads):
    logging.info("Sending email notification...")
    body = "\n\n".join([f"{title}\n{link}" for link, title in new_ads.items()])
    msg = MIMEText(body)
    msg['Subject'] = "📢 New Facebook Marketplace Ads Detected"
    msg['From'] = GMAIL_USER
    msg['To'] = TO_EMAIL

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASS)
            server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
        logging.info("Email sent successfully.")
    except Exception as e:
        logging.error(f"Failed to send email: {e}")

def main():
    try:
        login_to_facebook()
    except Exception as e:
        logging.error(f"Error during Facebook login: {e}", exc_info=True)
        return

    sent_ads = set()
    try:
        fetch_ads(sent_ads)
        logging.info(f"Initial crawl complete. Sent ads: {len(sent_ads)}")
    except Exception as e:
        logging.error(f"Error fetching initial ads: {e}", exc_info=True)
        return

    while True:
        try:
            time.sleep(CHECK_INTERVAL)
            fetch_ads(sent_ads)
        except Exception as e:
            logging.error(f"Error in main loop: {e}", exc_info=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Stopped by user.")
    finally:
        driver.quit()


import time
import smtplib
import logging
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver  # Force import for PyInstaller
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
TIME_AGO = config.get("TIME_AGO", 5)
TIME_UNIT = config.get("TIME_UNIT", "Minute").strip().lower().rstrip("*s")
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
driver = None

def init_driver():
    global driver
    if driver is not None:
        return driver
    
    options = Options()
    # options.add_argument("--headless")  # comment this line to see browser
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    return driver

def login_to_facebook():
    global driver
    driver = init_driver()
    
    logging.info("Opening Facebook login page...")
    logging.info("=" * 60)
    logging.info("PLEASE LOG IN MANUALLY IN THE BROWSER WINDOW")
    logging.info("The bot will automatically continue once you're logged in")
    logging.info("=" * 60)
    driver.get("https://www.facebook.com/login")
    
    # Wait for user to manually log in (wait until URL changes from login page)
    try:
        # Wait for up to 5 minutes for the user to log in
        # Check if URL no longer contains "login" which indicates successful login
        WebDriverWait(driver, 300).until(
            lambda d: "login" not in d.current_url.lower()
        )
        logging.info("Login detected! Continuing with the bot...")
        time.sleep(3)  # Give a moment for the page to fully load
    except Exception as e:
        logging.error(f"Timeout waiting for manual login: {e}")
        raise

def scrape_ad_details(link):
    """Open the ad detail page and scrape title, price, and post time."""
    import re
    details = {
        "title": "N/A",
        "price": "N/A",
        "post_time": "N/A",
    }
    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        driver.get(link)

        # Wait for h1 to appear (ensures page JS has rendered the main content)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//h1"))
            )
        except Exception:
            logging.warning(f"[scrape] Timed out waiting for h1 on: {link}")
        time.sleep(2)  # extra settle for dynamic content

        # ── TITLE ──────────────────────────────────────────────────────────
        try:
            h1_elems = driver.find_elements(By.XPATH, "//h1")
            for h1 in h1_elems:
                txt = h1.text.strip()
                if txt:
                    details["title"] = txt
                    break
        except Exception as e:
            logging.warning(f"[scrape] title error: {e}")
        logging.info(f"[scrape] title     = {details['title']!r}")

        # ── PRICE ──────────────────────────────────────────────────────────
        # Use a strict currency+digits regex to avoid picking up UI chips like "Free Stuff"
        try:
            price_re = re.compile(
                r'(PKR|Rs\.?|USD|\$|EUR|€)\s*[\d,\.]+|[\d,\.]+\s*(PKR|Rs\.?)',
                re.IGNORECASE
            )
            price_candidates = driver.find_elements(
                By.XPATH,
                "//*[contains(text(),'PKR') or contains(text(),'Rs') "
                "or contains(text(),'USD') or contains(text(),'$') "
                "or contains(text(),'EUR')]"
            )
            for c in price_candidates:
                txt = c.text.strip()
                if txt and len(txt) < 50 and price_re.search(txt):
                    details["price"] = txt
                    break

            # Fallback: bare number with commas (e.g. "460,000")
            if details["price"] == "N/A":
                num_elems = driver.find_elements(
                    By.XPATH,
                    "//*[string-length(normalize-space(text())) > 2 "
                    "and string-length(normalize-space(text())) < 30]"
                )
                for e in num_elems:
                    txt = e.text.strip()
                    if re.match(r'^[\d,\.]+$', txt) and ',' in txt:
                        details["price"] = txt
                        break
        except Exception as e:
            logging.warning(f"[scrape] price error: {e}")
        logging.info(f"[scrape] price     = {details['price']!r}")

        # ── POST TIME ──────────────────────────────────────────────────────
        try:
            listed_re = re.compile(
                r'listed.{0,10}(a |an |\d+\s+)(second|minute|hour|day|week|month|year)',
                re.IGNORECASE
            )
            all_elems = driver.find_elements(
                By.XPATH, "//*[contains(text(),'Listed') or contains(text(),'listed')]"
            )
            for elem in all_elems:
                t = elem.text.strip()
                if listed_re.search(t) and len(t) < 150:
                    details["post_time"] = t
                    break

            if details["post_time"] == "N/A":
                ago_elems = driver.find_elements(
                    By.XPATH, "//*[contains(text(),'ago') or contains(text(),'just now')]"
                )
                for elem in ago_elems:
                    t = elem.text.strip()
                    if re.search(
                        r'(\d+|a|an)\s+(second|minute|hour|day|week|month|year)s?\s*ago|just now',
                        t, re.IGNORECASE
                    ) and len(t) < 150:
                        details["post_time"] = t
                        break
        except Exception as e:
            logging.warning(f"[scrape] post_time error: {e}")
        logging.info(f"[scrape] post_time = {details['post_time']!r}")



    except Exception as e:
        logging.warning(f"Error scraping ad details for {link}: {e}")
    finally:
        try:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        except Exception:
            pass

    return details



# Unit-to-seconds conversion map
_UNIT_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour":   3600,
    "day":    86400,
    "week":   604800,
    "month":  2592000,   # ~30 days
    "year":   31536000,  # ~365 days
}

def is_within_time_limit(posted_time_text):
    """
    Returns True if the ad's posted time is within TIME_AGO TIME_UNITs.
    Parses text like:
      'Listed a day ago in Islamabad'
      '5 minutes ago'
      'Just now'
      '2 hours ago'
    """
    import re
    pt = posted_time_text.lower().strip()

    # 'just now' / 'a few seconds ago' always qualifies
    if 'just now' in pt:
        return True

    # Map unit from config -> seconds threshold
    unit_key = TIME_UNIT  # already lowercased and stripped of trailing * / s
    threshold_secs = TIME_AGO * _UNIT_SECONDS.get(unit_key, 60)

    # Try to extract a number + unit from the text
    # Handles: '5 minutes ago', 'a day ago', 'Listed 3 hours ago in ...'
    # 'a' / 'an' treated as 1
    match = re.search(
        r'(\d+|a|an)\s+(second|minute|hour|day|week|month|year)s?',
        pt
    )
    if not match:
        return False

    raw_num, raw_unit = match.group(1), match.group(2)
    num = 1 if raw_num in ('a', 'an') else int(raw_num)
    ad_secs = num * _UNIT_SECONDS.get(raw_unit, 0)

    return ad_secs <= threshold_secs


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
            link = ad.get_attribute('href')
            if not link:
                continue

            # Scrape all details from the ad page
            details = scrape_ad_details(link)
            title = details["title"]
            posted_time = details["post_time"]

            pt_lower = posted_time.lower()
            include = is_within_time_limit(posted_time)

            if include and link not in sent_ads:
                try:
                    send_email(link, details)
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

def send_email(link, details):
    """Send an HTML email with the ad's title, price, post time, and link."""
    logging.info("Sending email notification...")

    title = details.get("title", "N/A")
    price = details.get("price", "N/A")
    post_time = details.get("post_time", "N/A")

    html_body = f"""\
<html>
  <body style="font-family: Arial, sans-serif; color: #222; max-width: 600px;">
    <h2 style="color: #1877F2;">New Facebook Marketplace Ad</h2>
    <table style="border-collapse: collapse; width: 100%;">
      <tr>
        <td style="padding: 6px 12px; font-weight: bold; width: 130px;">Title</td>
        <td style="padding: 6px 12px;">{title}</td>
      </tr>
      <tr style="background:#f5f5f5;">
        <td style="padding: 6px 12px; font-weight: bold;">Price</td>
        <td style="padding: 6px 12px;">{price}</td>
      </tr>
      <tr>
        <td style="padding: 6px 12px; font-weight: bold;">Posted</td>
        <td style="padding: 6px 12px;">{post_time}</td>
      </tr>
      <tr style="background:#f5f5f5;">
        <td style="padding: 6px 12px; font-weight: bold;">Ad Link</td>
        <td style="padding: 6px 12px;"><a href="{link}">{link}</a></td>
      </tr>
    </table>
  </body>
</html>
"""

    msg = MIMEText(html_body, 'html')
    msg['Subject'] = f"New FB Marketplace Ad: {title}"
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
        if driver is not None:
            driver.quit()

import smtplib
from email.mime.text import MIMEText

# Dummy ad details
dummy_ads = {
    'https://www.facebook.com/marketplace/item/1234567890': 'Dummy Product Title'
}

# Email configuration
GMAIL_USER = "helperusa7@gmail.com"
GMAIL_PASS = "****"
TO_EMAIL = "afzaalhussain50@gmail.com"

# Compose email
body = "\n\n".join([f"{title}\n{link}" for link, title in dummy_ads.items()])
msg = MIMEText(body)
msg['Subject'] = "Test: Dummy Facebook Marketplace Ad"
msg['From'] = GMAIL_USER
msg['To'] = TO_EMAIL

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(GMAIL_USER, GMAIL_PASS)
        server.sendmail(GMAIL_USER, TO_EMAIL, msg.as_string())
    print("Dummy email sent successfully.")
except Exception as e:
    print(f"Failed to send dummy email: {e}")

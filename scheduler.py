import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import configparser

# Read configuration from .conf file
CONFIG_FILE = "check.conf"

def load_config():
    """Loads configuration from check.conf"""
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def send_email():
    """Sends an email based on the config settings"""
    config = load_config()

    SMTP_SERVER = config["SMTP"]["Server"]
    SMTP_PORT = int(config["SMTP"]["Port"])
    EMAIL_ADDRESS = config["SMTP"]["Email"]
    EMAIL_PASSWORD = config["SMTP"]["Password"]
    ENCRYPTION_METHOD = config["SMTP"].get("Encryption", "STARTTLS").strip().upper()

    TO_ADDRESS = config["Email"]["ToAddress"]
    SUBJECT = config["Email"]["Subject"]
    BODY = config["Email"]["Body"]

    try:
        # Create the email message
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_ADDRESS
        msg["Subject"] = SUBJECT
        msg.attach(MIMEText(BODY, "plain"))

        # Start SMTP connection
        if ENCRYPTION_METHOD == "SSL":
            # SSL connection (Port 465)
            session = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=20)
            session.ehlo()  # Identify to the server
        else:
            # STARTTLS or Unencrypted connection (Ports 587 or 25)
            session = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
            session.ehlo()  # Identify to the SMTP server

            # Attempt STARTTLS if enabled
            if ENCRYPTION_METHOD == "STARTTLS":
                try:
                    session.starttls()
                    session.ehlo()  # Re-identify after STARTTLS
                except smtplib.SMTPException as e:
                    print(f"Warning: STARTTLS failed: {e}")

        # Try authentication if a password is provided
        if EMAIL_PASSWORD:
            try:
                session.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            except smtplib.SMTPAuthenticationError as e:
                print(f"SMTP Authentication failed: {e}")
            except Exception as e:
                print(f"Authentication error: {e}")

        # Send the email
        session.sendmail(EMAIL_ADDRESS, TO_ADDRESS, msg.as_string())
        session.quit()
        print(f"Email sent successfully using {ENCRYPTION_METHOD}.")

    except Exception as e:
        print(f"Failed to send email: {e}")

# Load the mode from config
config = load_config()
mode = config["Schedule"].get("Mode", "Timer").strip().lower()

if mode == "timer":
    try:
        INTERVAL = int(config["Schedule"]["Interval"])
        if INTERVAL <= 0:
            raise ValueError("Interval must be greater than 0")
    except (KeyError, ValueError) as e:
        print(f"Invalid or missing interval in config: {e}. Defaulting to 15 minutes.")
        INTERVAL = 15  # Default interval if invalid

    # Send the first email immediately
    send_email()

    # Schedule the email every INTERVAL minutes
    schedule.every(INTERVAL).minutes.do(send_email)
    print(f"Email scheduler is running... Emails will be sent every {INTERVAL} minutes.")

elif mode == "time":
    try:
        schedule_time = config["Schedule"]["Time"]
    except KeyError:
        print("Missing 'Time' in config. Defaulting to 05:00.")
        schedule_time = "05:00"

    # Send the first email immediately
    send_email()

    # Schedule the email at a specific time every day
    schedule.every().day.at(schedule_time).do(send_email)
    print(f"Email scheduler is running... Emails will be sent daily at {schedule_time}.")

else:
    print(f"Invalid mode '{mode}' in config. Please set Mode to 'Timer' or 'Time'. Exiting.")
    exit(1)

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)
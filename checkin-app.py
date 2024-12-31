import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import configparser

# Read configuration from .conf file
CONFIG_FILE = "check.conf"
def load_config():
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)
    return config

def send_email():
    config = load_config()

    SMTP_SERVER = config["SMTP"]["Server"]
    SMTP_PORT = int(config["SMTP"]["Port"])
    EMAIL_ADDRESS = config["SMTP"]["Email"]
    EMAIL_PASSWORD = config["SMTP"]["Password"]

    TO_ADDRESS = config["Email"]["ToAddress"]
    SUBJECT = config["Email"]["Subject"]
    BODY = config["Email"]["Body"]

    try:
        # Create the email
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = TO_ADDRESS
        msg["Subject"] = SUBJECT

        # Attach the email body
        msg.attach(MIMEText(BODY, "plain"))

        # Connect to the SMTP server and send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Start TLS encryption
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, TO_ADDRESS, msg.as_string())

        print("Email sent successfully.")

    except Exception as e:
        print(f"Failed to send email: {e}")

# Add this line to send the email immediately when the script starts
send_email()

# Load the schedule time from the config file
config = load_config()
schedule_time = config["Schedule"]["Time"]

# Schedule the email to be sent daily at the specified time
schedule.every().day.at(schedule_time).do(send_email)

print(f"Daily email scheduler is running... Emails will be sent at {schedule_time}.")

# Keep the script running
while True:
    schedule.run_pending()
    time.sleep(1)

# Email Scheduler GUI

This is a Python-based GUI application for scheduling and sending emails. It allows you to:

- **Configure SMTP settings** (server, port, encryption, credentials)  
- **Schedule emails** on a specific time basis (daily, once, weekly, monthly) or on a repeating interval (e.g., every 15 minutes)  
- **Manually send emails now**  
- **Attach files** (e.g., PDFs, images) to your emails  
- **Store** and **edit** scheduled emails in a local **SQLite** database  

The application uses [Tkinter](https://docs.python.org/3/library/tkinter.html) for the GUI and [smtplib](https://docs.python.org/3/library/smtplib.html) for sending emails.

---

## Features

1. **SMTP Settings**  
   - Enter your SMTP server (e.g., `smtp.gmail.com` or `smtp.mailgun.org`), port, email address, and password.  
   - Choose encryption: **SSL**, **STARTTLS**, or **NONE**.

2. **Database-Backed**  
   - All SMTP settings and emails are stored in a local SQLite database named `scheduler.db`.  
   - Settings persist between runs of the application.

3. **Schedules**  
   - **Time-based** (Once, Daily, Weekly, or Monthly) at a chosen clock time (HH:MM).  
   - **Interval-based**: send the email every X minutes.

4. **Last Sent & Next Send**  
   - The GUI shows when an email was last sent, as well as an estimate of the next send time.

5. **Attachment Support**  
   - You can attach a single file to an email (e.g., PDF, image, document).  
   - Files are MIME-encoded automatically via Python’s `EmailMessage`.

6. **Manual Send**  
   - Force-send any scheduled email immediately by clicking the **Send Now** button.

---
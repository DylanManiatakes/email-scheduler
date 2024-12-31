# Daily Email Scheduler

A simple Python application that sends daily emails at a specified time using an SMTP server. The app reads its configuration from a `.conf` file, allowing flexible email content, scheduling, and server settings without modifying the code.

## Features
- Sends emails daily at a configurable time.
- Reads email settings (SMTP server, credentials, recipient, etc.) from a `.conf` file.
- Logs email success or failure to the console.
- Fully customizable email content and schedule.

## Prerequisites
- Python 3.6 or later
- Required Python libraries:
  - `smtplib`
  - `email`
  - `schedule`
  - `configparser`

## Setup

### 1. Clone or Download the Repository
Place the project files in a directory of your choice.

### 2. Create the Configuration File
Create a file named `check.conf` in the same directory as the application. Use the following template:

```ini
[SMTP]
Server = smtp.example.com
Port = 587
Email = your_email@example.com
Password = your_password

[Email]
ToAddress = recipient_email@example.com
Subject = Daily Update
Body = This is the daily email sent at a scheduled time.

[Schedule]
Time = 05:00
```

- Replace `smtp.example.com`, `your_email@example.com`, and other placeholders with actual values.
- The time format under `[Schedule]` must be in `HH:MM` (24-hour clock).

### 3. Install Dependencies
Install the required Python libraries:

```bash
pip install schedule
```

### 4. Run the Application
Run the script using:

```bash
python checkin-app.py
```

The application will read the configuration and schedule the email to be sent daily at the specified time.

### 5. Logs and Console Output
- The app logs email sending status to the console.
- If an email fails to send, the error message will be displayed.

## Configuration

### `check.conf`
The `check.conf` file controls the application behavior. Here’s what each section does:

- **[SMTP]:** Configures the SMTP server for sending emails.
  - `Server`: The SMTP server address (e.g., `smtp.gmail.com`).
  - `Port`: The SMTP server port (e.g., `587` for TLS).
  - `Email`: The sender's email address.
  - `Password`: The sender's email password.

- **[Email]:** Configures the email content.
  - `ToAddress`: The recipient's email address.
  - `Subject`: The subject of the email.
  - `Body`: The body content of the email.

- **[Schedule]:** Configures when the email is sent.
  - `Time`: Time in `HH:MM` format (24-hour clock).

## Notes
- Ensure the SMTP server credentials are valid.
- If using Gmail or similar services, you may need to enable "less secure apps" or generate an app password.
- Keep the `check.conf` file secure to protect your email credentials.

## License
This project is licensed under the MIT License.

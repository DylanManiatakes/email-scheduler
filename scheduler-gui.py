import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import smtplib
import ssl
import threading
import time
from datetime import datetime, timedelta
import os
from email.message import EmailMessage  # For adding attachments easily

DB_FILE = "scheduler.db"

def setup_database():
    """Create (or update) the SQLite database and tables if they don't exist."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Base tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smtp_settings (
            id INTEGER PRIMARY KEY,
            server TEXT,
            port INTEGER,
            email TEXT,
            password TEXT,
            encryption TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY,
            subject TEXT,
            recipients TEXT,
            body TEXT,
            mode TEXT,            -- "Time" or "Interval"
            frequency TEXT,       -- "Once", "Daily", "Weekly", "Monthly" (for "Time" mode)
            interval_minutes INTEGER, -- number of minutes for "Interval" mode
            schedule_time TEXT,   -- "HH:MM" for "Time" mode
            last_sent TEXT        -- store last sent datetime (ISO format)
        )
    """)

    # Ensure the emails table has 'attachment_path' if old DB existed
    cursor.execute("PRAGMA table_info(emails)")
    columns_info = cursor.fetchall()
    existing_cols = [col[1] for col in columns_info]
    if 'attachment_path' not in existing_cols:
        cursor.execute("ALTER TABLE emails ADD COLUMN attachment_path TEXT")

    conn.commit()
    conn.close()

class EmailSchedulerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Email Scheduler")

        # Flag to stop the scheduling thread when the app closes
        self.stop_scheduling = False

        self.setup_ui()
        self.load_smtp_settings()
        self.load_scheduled_emails()

        # Start the background scheduling thread
        self.scheduling_thread = threading.Thread(target=self.scheduling_loop, daemon=True)
        self.scheduling_thread.start()

        # Clean up on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui(self):
        """Build all the UI frames, buttons, and widgets."""
        # ----------------- SMTP Settings Frame ------------------
        self.smtp_frame = ttk.LabelFrame(self.root, text="SMTP Settings")
        self.smtp_frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(self.smtp_frame, text="SMTP Server:").pack(side="left", padx=5, pady=5)
        self.server_entry = ttk.Entry(self.smtp_frame)
        self.server_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.smtp_frame, text="Port:").pack(side="left", padx=5, pady=5)
        self.port_entry = ttk.Entry(self.smtp_frame, width=5)
        self.port_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.smtp_frame, text="Email:").pack(side="left", padx=5, pady=5)
        self.email_entry = ttk.Entry(self.smtp_frame)
        self.email_entry.pack(side="left", padx=5, pady=5)

        ttk.Label(self.smtp_frame, text="Password:").pack(side="left", padx=5, pady=5)
        self.password_entry = ttk.Entry(self.smtp_frame, show="*")
        self.password_entry.pack(side="left", padx=5, pady=5)

        self.encryption_var = tk.StringVar(value="SSL")
        ttk.Label(self.smtp_frame, text="Encryption:").pack(side="left", padx=5, pady=5)
        self.encryption_dropdown = ttk.Combobox(
            self.smtp_frame,
            textvariable=self.encryption_var,
            values=["SSL", "STARTTLS", "NONE"],
            width=8
        )
        self.encryption_dropdown.pack(side="left", padx=5, pady=5)

        ttk.Button(
            self.smtp_frame,
            text="Save SMTP Settings",
            command=self.save_smtp_settings
        ).pack(pady=5, padx=5)

        # ----------------- Scheduled Emails Frame ------------------
        self.emails_frame = ttk.LabelFrame(self.root, text="Scheduled Emails")
        self.emails_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = (
            "ID",
            "Subject",
            "Recipients",
            "Mode",
            "Frequency/Interval",
            "Schedule Time",
            "Last Sent",
            "Next Send"
        )
        self.email_list = ttk.Treeview(self.emails_frame, columns=columns, show="headings")
        for col in columns:
            self.email_list.heading(col, text=col)
            self.email_list.column(col, width=120)
        self.email_list.pack(fill="both", expand=True, padx=5, pady=5)

        # Buttons at the bottom of the frame
        button_frame = ttk.Frame(self.emails_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        self.add_email_button = ttk.Button(
            button_frame,
            text="Add New Email",
            command=self.open_add_email_window
        )
        self.add_email_button.pack(side="left", padx=5, pady=5)

        self.edit_email_button = ttk.Button(
            button_frame,
            text="Edit",
            command=self.edit_selected_email
        )
        self.edit_email_button.pack(side="left", padx=5, pady=5)

        self.send_now_button = ttk.Button(
            button_frame,
            text="Send Now",
            command=self.send_selected_email_now
        )
        self.send_now_button.pack(side="left", padx=5, pady=5)

        self.delete_email_button = ttk.Button(
            button_frame,
            text="Delete",
            command=self.delete_selected_email
        )
        self.delete_email_button.pack(side="left", padx=5, pady=5)

    # ======================= ADD NEW EMAIL =========================
    def open_add_email_window(self):
        """Opens a new window for creating a new email schedule."""
        add_email_win = tk.Toplevel(self.root)
        add_email_win.title("Add New Email")

        # Subject
        ttk.Label(add_email_win, text="Subject:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        subject_entry = ttk.Entry(add_email_win)
        subject_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Recipients
        ttk.Label(add_email_win, text="Recipients (comma-separated):").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        recipients_entry = ttk.Entry(add_email_win)
        recipients_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Body
        ttk.Label(add_email_win, text="Body:").grid(row=2, column=0, padx=5, pady=5, sticky="ne")
        body_text = tk.Text(add_email_win, width=40, height=5)
        body_text.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Mode (Time or Interval)
        ttk.Label(add_email_win, text="Mode:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        mode_var = tk.StringVar(value="Time")
        mode_combobox = ttk.Combobox(
            add_email_win,
            textvariable=mode_var,
            values=["Time", "Interval"],
            state="readonly"
        )
        mode_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Frequency (If mode = Time)
        ttk.Label(add_email_win, text="Frequency:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        frequency_var = tk.StringVar(value="Once")
        frequency_combobox = ttk.Combobox(
            add_email_win,
            textvariable=frequency_var,
            values=["Once", "Daily", "Weekly", "Monthly"],
            state="readonly"
        )
        frequency_combobox.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        # Interval (minutes) if mode=Interval
        ttk.Label(add_email_win, text="Interval (minutes):").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        interval_entry = ttk.Entry(add_email_win)
        interval_entry.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        # Schedule Time (HH:MM) if mode=Time
        ttk.Label(add_email_win, text="Schedule Time (HH:MM):").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        schedule_time_entry = ttk.Entry(add_email_win)
        schedule_time_entry.grid(row=6, column=1, padx=5, pady=5, sticky="w")

        # Attachment
        ttk.Label(add_email_win, text="Attachment (optional):").grid(row=7, column=0, padx=5, pady=5, sticky="e")
        attachment_entry = ttk.Entry(add_email_win, width=35)
        attachment_entry.grid(row=7, column=1, padx=5, pady=5, sticky="w")

        def browse_file():
            """Open file dialog to pick one attachment."""
            path = filedialog.askopenfilename()
            if path:
                attachment_entry.delete(0, tk.END)
                attachment_entry.insert(0, path)

        browse_btn = ttk.Button(add_email_win, text="Browse", command=browse_file)
        browse_btn.grid(row=7, column=2, padx=5, pady=5, sticky="w")

        def save_new_email():
            subject = subject_entry.get().strip()
            recipients = recipients_entry.get().strip()
            body = body_text.get("1.0", "end").strip()
            mode = mode_var.get()
            frequency = frequency_var.get()
            interval_minutes = interval_entry.get().strip()
            schedule_time = schedule_time_entry.get().strip()
            attachment_path = attachment_entry.get().strip() or None

            if not subject:
                messagebox.showwarning("Warning", "Subject is required.")
                return
            if not recipients:
                messagebox.showwarning("Warning", "Recipients are required.")
                return

            # Convert interval_minutes to integer if possible
            interval_val = None
            if interval_minutes:
                try:
                    interval_val = int(interval_minutes)
                except ValueError:
                    messagebox.showerror("Error", "Interval must be an integer (minutes).")
                    return

            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO emails
                    (subject, recipients, body, mode, frequency,
                     interval_minutes, schedule_time, last_sent, attachment_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                subject,
                recipients,
                body,
                mode,
                frequency,
                interval_val,
                schedule_time if schedule_time else None,
                None,  # last_sent is null initially
                attachment_path
            ))
            conn.commit()
            conn.close()

            self.load_scheduled_emails()
            messagebox.showinfo("Success", "New email scheduled!")
            add_email_win.destroy()

        ttk.Button(add_email_win, text="Save", command=save_new_email).grid(
            row=8, column=0, columnspan=3, padx=5, pady=10
        )

    # ======================= EDIT SELECTED EMAIL =========================
    def edit_selected_email(self):
        """Opens a window to edit all details of the selected email."""
        selected_item = self.email_list.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an email to edit.")
            return

        item = self.email_list.item(selected_item)
        email_id = item["values"][0]

        # Load the row fully from DB
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""SELECT subject, recipients, body, mode, frequency,
                                 interval_minutes, schedule_time, attachment_path
                          FROM emails WHERE id=?""", (email_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "Failed to retrieve email details.")
            return

        (old_subject, old_recipients, old_body, old_mode,
         old_frequency, old_interval, old_schedule_time, old_attachment) = row

        edit_win = tk.Toplevel(self.root)
        edit_win.title("Edit Scheduled Email")

        # Subject
        ttk.Label(edit_win, text="Subject:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        subject_entry = ttk.Entry(edit_win)
        subject_entry.insert(0, old_subject)
        subject_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Recipients
        ttk.Label(edit_win, text="Recipients:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        recipients_entry = ttk.Entry(edit_win)
        recipients_entry.insert(0, old_recipients)
        recipients_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Body
        ttk.Label(edit_win, text="Body:").grid(row=2, column=0, padx=5, pady=5, sticky="ne")
        body_text = tk.Text(edit_win, width=40, height=5)
        body_text.insert("1.0", old_body)
        body_text.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Mode
        ttk.Label(edit_win, text="Mode:").grid(row=3, column=0, padx=5, pady=5, sticky="e")
        mode_var = tk.StringVar(value=old_mode)
        mode_combobox = ttk.Combobox(
            edit_win,
            textvariable=mode_var,
            values=["Time", "Interval"],
            state="readonly"
        )
        mode_combobox.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        # Frequency
        ttk.Label(edit_win, text="Frequency:").grid(row=4, column=0, padx=5, pady=5, sticky="e")
        frequency_var = tk.StringVar(value=old_frequency)
        frequency_combobox = ttk.Combobox(
            edit_win,
            textvariable=frequency_var,
            values=["Once", "Daily", "Weekly", "Monthly"],
            state="readonly"
        )
        frequency_combobox.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        # Interval
        ttk.Label(edit_win, text="Interval (minutes):").grid(row=5, column=0, padx=5, pady=5, sticky="e")
        interval_entry = ttk.Entry(edit_win)
        interval_entry.insert(0, "" if old_interval is None else str(old_interval))
        interval_entry.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        # Schedule Time
        ttk.Label(edit_win, text="Schedule Time (HH:MM):").grid(row=6, column=0, padx=5, pady=5, sticky="e")
        schedule_time_entry = ttk.Entry(edit_win)
        schedule_time_entry.insert(0, "" if old_schedule_time is None else old_schedule_time)
        schedule_time_entry.grid(row=6, column=1, padx=5, pady=5, sticky="w")

        # Attachment
        ttk.Label(edit_win, text="Attachment (optional):").grid(row=7, column=0, padx=5, pady=5, sticky="e")
        attachment_entry = ttk.Entry(edit_win, width=35)
        if old_attachment:
            attachment_entry.insert(0, old_attachment)
        attachment_entry.grid(row=7, column=1, padx=5, pady=5, sticky="w")

        def browse_file_edit():
            path = filedialog.askopenfilename()
            if path:
                attachment_entry.delete(0, tk.END)
                attachment_entry.insert(0, path)

        browse_btn = ttk.Button(edit_win, text="Browse", command=browse_file_edit)
        browse_btn.grid(row=7, column=2, padx=5, pady=5, sticky="w")

        def save_changes():
            """Update the email entry in the database."""
            new_subject = subject_entry.get().strip()
            new_recipients = recipients_entry.get().strip()
            new_body = body_text.get("1.0", "end").strip()
            new_mode = mode_var.get()
            new_frequency = frequency_var.get()
            new_interval_str = interval_entry.get().strip()
            new_schedule_time = schedule_time_entry.get().strip() or None
            new_attachment = attachment_entry.get().strip() or None

            if not new_subject:
                messagebox.showwarning("Warning", "Subject is required.")
                return
            if not new_recipients:
                messagebox.showwarning("Warning", "Recipients are required.")
                return

            # Convert interval to int if provided
            new_interval = None
            if new_interval_str:
                try:
                    new_interval = int(new_interval_str)
                except ValueError:
                    messagebox.showerror("Error", "Interval must be an integer.")
                    return

            conn2 = sqlite3.connect(DB_FILE)
            cursor2 = conn2.cursor()
            cursor2.execute("""
                UPDATE emails
                SET subject=?,
                    recipients=?,
                    body=?,
                    mode=?,
                    frequency=?,
                    interval_minutes=?,
                    schedule_time=?,
                    attachment_path=?
                WHERE id=?
            """, (
                new_subject,
                new_recipients,
                new_body,
                new_mode,
                new_frequency,
                new_interval,
                new_schedule_time,
                new_attachment,
                email_id
            ))
            conn2.commit()
            conn2.close()

            self.load_scheduled_emails()
            messagebox.showinfo("Success", "Email updated successfully!")
            edit_win.destroy()

        ttk.Button(edit_win, text="Save Changes", command=save_changes).grid(
            row=8, column=0, columnspan=3, padx=5, pady=10
        )

    # ======================= DELETE SELECTED EMAIL =========================
    def delete_selected_email(self):
        selected_item = self.email_list.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an email to delete.")
            return

        item = self.email_list.item(selected_item)
        email_id = item["values"][0]

        if not messagebox.askyesno("Confirm", "Are you sure you want to delete this email?"):
            return

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emails WHERE id=?", (email_id,))
        conn.commit()
        conn.close()

        self.load_scheduled_emails()
        messagebox.showinfo("Success", "Email deleted successfully!")

    # ======================= SEND NOW (MANUAL) =========================
    def send_selected_email_now(self):
        """Immediately sends the selected email, ignoring the schedule."""
        selected_item = self.email_list.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an email to send.")
            return

        item = self.email_list.item(selected_item)
        email_id = item["values"][0]

        # Fetch email details
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""SELECT subject, recipients, body, attachment_path
                          FROM emails WHERE id=?""", (email_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("Error", "Unable to fetch selected email from database.")
            return

        subject, recipients, body, attachment_path = row
        try:
            self.send_email(subject, recipients, body, attachment_path)
            # Update last_sent since we manually sent
            conn2 = sqlite3.connect(DB_FILE)
            c2 = conn2.cursor()
            c2.execute("UPDATE emails SET last_sent=? WHERE id=?", (datetime.now().isoformat(), email_id))
            conn2.commit()
            conn2.close()

            self.load_scheduled_emails()  # Refresh so 'Last Sent' updates
            messagebox.showinfo("Success", "Email sent successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send email: {e}")

    # ======================= ACTUAL EMAIL SENDING LOGIC (WITH ATTACHMENT) =========================
    def send_email(self, subject, recipients, body, attachment_path=None):
        """Sends the email using the currently stored SMTP settings (with optional attachment)."""
        # Load SMTP settings from DB
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT server, port, email, password, encryption FROM smtp_settings")
        settings = cursor.fetchone()
        conn.close()

        if not settings:
            raise ValueError("SMTP settings not configured!")

        server, port, sender_email, password, encryption = settings

        # Build an EmailMessage, explicitly specifying UTF-8 text:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = recipients
        # The line below ensures the body is plain text, UTF-8
        msg.set_content(body, subtype='plain', charset='utf-8')

        # If there's an attachment, add it
        if attachment_path and os.path.isfile(attachment_path):
            with open(attachment_path, "rb") as f:
                file_data = f.read()
                file_name = os.path.basename(attachment_path)
            # Attempt to guess the MIME type based on the filename
            import mimetypes
            mime_type, _ = mimetypes.guess_type(file_name)
            if not mime_type:
                mime_type = "application/octet-stream"
            maintype, subtype = mime_type.split("/", 1)

            msg.add_attachment(
                file_data,
                maintype=maintype,
                subtype=subtype,
                filename=file_name
            )

        recipient_list = [r.strip() for r in recipients.split(",") if r.strip()]

        if encryption == "SSL":
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, int(port), context=context) as smtp:
                smtp.login(sender_email, password)
                smtp.send_message(msg, from_addr=sender_email, to_addrs=recipient_list)
        elif encryption == "STARTTLS":
            context = ssl.create_default_context()
            with smtplib.SMTP(server, int(port)) as smtp:
                smtp.starttls(context=context)
                smtp.login(sender_email, password)
                smtp.send_message(msg, from_addr=sender_email, to_addrs=recipient_list)
        else:
            # No encryption
            with smtplib.SMTP(server, int(port)) as smtp:
                smtp.login(sender_email, password)
                smtp.send_message(msg, from_addr=sender_email, to_addrs=recipient_list)

    # ======================= SCHEDULING LOGIC (BACKGROUND) =========================
    def scheduling_loop(self):
        """Background thread that periodically checks if any email should be sent."""
        while not self.stop_scheduling:
            self.check_schedules()
            time.sleep(60)  # Check every 60 seconds

    def check_schedules(self):
        """Fetch all emails from DB, determine if they should be sent, and send them."""
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, subject, recipients, body, mode, frequency,
                   interval_minutes, schedule_time, last_sent, attachment_path
            FROM emails
        """)
        emails = cursor.fetchall()
        conn.close()

        now = datetime.now()
        for (
            email_id, subject, recipients, body, mode, frequency,
            interval_minutes, schedule_time, last_sent, attachment_path
        ) in emails:
            # Convert last_sent from string to datetime (or None)
            last_sent_dt = None
            if last_sent:
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent)
                except ValueError:
                    last_sent_dt = None

            # Decide if it’s time to send
            need_to_send = False

            if mode == "Interval":
                if interval_minutes and interval_minutes > 0:
                    if not last_sent_dt:
                        # Never sent
                        need_to_send = True
                    else:
                        delta = now - last_sent_dt
                        if delta.total_seconds() >= interval_minutes * 60:
                            need_to_send = True

            elif mode == "Time":
                if schedule_time:
                    try:
                        sched_hour, sched_min = map(int, schedule_time.split(":"))
                    except:
                        # Invalid schedule_time format
                        continue
                    scheduled_today = now.replace(hour=sched_hour, minute=sched_min, second=0, microsecond=0)

                    if frequency == "Once":
                        if not last_sent_dt and now >= scheduled_today:
                            need_to_send = True
                    elif frequency == "Daily":
                        if now >= scheduled_today:
                            if not last_sent_dt or last_sent_dt.date() < now.date():
                                need_to_send = True
                    elif frequency == "Weekly":
                        # Simplistic approach: 7-day intervals
                        if now >= scheduled_today:
                            if not last_sent_dt or (now - last_sent_dt) >= timedelta(days=7):
                                need_to_send = True
                    elif frequency == "Monthly":
                        # Simplistic approach: 30-day intervals
                        if now >= scheduled_today:
                            if not last_sent_dt or (now - last_sent_dt) >= timedelta(days=30):
                                need_to_send = True

            if need_to_send:
                try:
                    self.send_email(subject, recipients, body, attachment_path)
                    # Update last_sent in DB
                    conn2 = sqlite3.connect(DB_FILE)
                    cursor2 = conn2.cursor()
                    cursor2.execute("""
                        UPDATE emails SET last_sent=? WHERE id=?
                    """, (datetime.now().isoformat(), email_id))
                    conn2.commit()
                    conn2.close()

                    # Refresh the UI so "Last Sent" updates immediately
                    self.root.after(0, self.load_scheduled_emails)

                except Exception as e:
                    print(f"Error sending scheduled email (ID: {email_id}): {e}")

    # ======================= SMTP SETTINGS =========================
    def save_smtp_settings(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM smtp_settings")
        cursor.execute("""
            INSERT INTO smtp_settings (server, port, email, password, encryption)
            VALUES (?, ?, ?, ?, ?)
        """, (
            self.server_entry.get(),
            self.port_entry.get(),
            self.email_entry.get(),
            self.password_entry.get(),
            self.encryption_var.get()
        ))
        conn.commit()
        conn.close()
        messagebox.showinfo("Success", "SMTP settings saved!")

    def load_smtp_settings(self):
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT server, port, email, password, encryption FROM smtp_settings")
        settings = cursor.fetchone()
        conn.close()

        if settings:
            self.server_entry.delete(0, tk.END)
            self.server_entry.insert(0, settings[0])
            self.port_entry.delete(0, tk.END)
            self.port_entry.insert(0, settings[1])
            self.email_entry.delete(0, tk.END)
            self.email_entry.insert(0, settings[2])
            self.password_entry.delete(0, tk.END)
            self.password_entry.insert(0, settings[3])
            self.encryption_var.set(settings[4])

    # ======================= LOAD SCHEDULED EMAILS =========================
    def load_scheduled_emails(self):
        """Loads scheduled emails from DB into the Treeview, including last/next send."""
        self.email_list.delete(*self.email_list.get_children())

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                id, subject, recipients, mode, frequency, interval_minutes,
                schedule_time, last_sent
            FROM emails
        """)
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            (
                email_id, subject, recipients, mode,
                frequency, interval_minutes, schedule_time, last_sent
            ) = row

            # Convert last_sent to a display string
            if last_sent:
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent)
                    last_sent_str = last_sent_dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    last_sent_str = "Invalid"
            else:
                last_sent_str = ""

            # Build freq_or_int column
            if mode == "Interval":
                freq_or_int = f"Every {interval_minutes} min" if interval_minutes else "N/A"
            else:
                freq_or_int = frequency

            # Compute an estimated next send time
            next_send_str = self.get_next_send_time(
                mode, frequency, interval_minutes, schedule_time, last_sent
            )

            display_time = schedule_time if schedule_time else ""

            self.email_list.insert(
                "",
                "end",
                values=(
                    email_id,
                    subject,
                    recipients,
                    mode,
                    freq_or_int,
                    display_time,
                    last_sent_str,
                    next_send_str
                )
            )

    def get_next_send_time(self, mode, frequency, interval_minutes, schedule_time, last_sent):
        """
        Estimate the next time this email will be sent, based on simplified scheduling logic.
        """
        now = datetime.now()

        # Convert last_sent
        last_sent_dt = None
        if last_sent:
            try:
                last_sent_dt = datetime.fromisoformat(last_sent)
            except ValueError:
                pass

        # For "Interval" mode
        if mode == "Interval":
            if interval_minutes and interval_minutes > 0:
                if not last_sent_dt:
                    return "Now"
                else:
                    next_time = last_sent_dt + timedelta(minutes=interval_minutes)
                    return next_time.strftime("%Y-%m-%d %H:%M")
            else:
                return "N/A"

        # For "Time" mode
        if not schedule_time:
            return "N/A"

        try:
            sched_hour, sched_min = map(int, schedule_time.split(":"))
        except:
            return "N/A"  # invalid format

        scheduled_today = now.replace(hour=sched_hour, minute=sched_min, second=0, microsecond=0)

        if frequency == "Once":
            if not last_sent_dt:
                # Not sent yet, so either today if not passed, otherwise "No future"
                if now <= scheduled_today:
                    return scheduled_today.strftime("%Y-%m-%d %H:%M")
                else:
                    return "No future"
            else:
                return "No future"

        elif frequency == "Daily":
            if now <= scheduled_today:
                return scheduled_today.strftime("%Y-%m-%d %H:%M")
            else:
                tomorrow = scheduled_today + timedelta(days=1)
                return tomorrow.strftime("%Y-%m-%d %H:%M")

        elif frequency == "Weekly":
            if last_sent_dt:
                next_week = last_sent_dt + timedelta(days=7)
                return next_week.strftime("%Y-%m-%d %H:%M")
            else:
                if now <= scheduled_today:
                    return scheduled_today.strftime("%Y-%m-%d %H:%M")
                else:
                    next_week = now + timedelta(days=7)
                    return next_week.strftime("%Y-%m-%d %H:%M")

        elif frequency == "Monthly":
            if last_sent_dt:
                next_month = last_sent_dt + timedelta(days=30)
                return next_month.strftime("%Y-%m-%d %H:%M")
            else:
                if now <= scheduled_today:
                    return scheduled_today.strftime("%Y-%m-%d %H:%M")
                else:
                    next_month = now + timedelta(days=30)
                    return next_month.strftime("%Y-%m-%d %H:%M")

        return "N/A"  # fallback

    # ======================= WINDOW CLOSE HANDLER =========================
    def on_closing(self):
        """Stop the scheduling thread and close the app."""
        self.stop_scheduling = True
        self.root.destroy()

# ======================= MAIN =========================
if __name__ == "__main__":
    setup_database()
    root = tk.Tk()
    app = EmailSchedulerGUI(root)
    root.mainloop()
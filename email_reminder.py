import smtplib
import sqlite3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

GMAIL_ADDRESS = "kiptoroeliakhim@gmail.com"
GMAIL_APP_PASSWORD = "fxyhplwvydctcdvr"

def get_db():
    conn = sqlite3.connect('dpms.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_upcoming_events():
    db = get_db()
    today = datetime.today().strftime('%Y-%m-%d')
    next_week = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
    events = db.execute(
        'SELECT * FROM events WHERE event_date BETWEEN ? AND ?',
        [today, next_week]
    ).fetchall()
    db.close()
    return events

def get_active_parishioners():
    db = get_db()
    parishioners = db.execute(
        "SELECT * FROM Parishioners WHERE status = 'Active' AND email IS NOT NULL AND email != ''"
    ).fetchall()
    db.close()
    return parishioners

def send_reminder(to_email, to_name, events):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = 'DPMS - Upcoming Parish Events This Week'
    msg['From'] = GMAIL_ADDRESS
    msg['To'] = to_email

    event_list = ""
    for e in events:
        event_list += f"""
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{e['title']}</td>
            <td style="padding:8px;border:1px solid #ddd;">{e['event_date']}</td>
            <td style="padding:8px;border:1px solid #ddd;">{e['location']}</td>
        </tr>
        """

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width:600px; margin:auto; padding:20px; border:1px solid #ddd; border-radius:8px;">
            <h2 style="color:#1a1a2e;">⛪ Parish Event Reminder</h2>
            <p>Dear <strong>{to_name}</strong>,</p>
            <p>Here are the upcoming parish events this week:</p>
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background:#1a1a2e; color:white;">
                        <th style="padding:8px;">Event</th>
                        <th style="padding:8px;">Date</th>
                        <th style="padding:8px;">Location</th>
                    </tr>
                </thead>
                <tbody>
                    {event_list}
                </tbody>
            </table>
            <br>
            <p>God bless you and your family.</p>
            <p style="color:#e94560;"><strong>DPMS - Digital Parish Management System</strong></p>
        </div>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, 'html'))

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        print(f"✅ Email sent to {to_name} ({to_email})")
    except Exception as e:
        print(f"❌ Failed to send to {to_name}: {e}")

def run_reminders():
    print("🔍 Checking for upcoming events...")
    events = get_upcoming_events()

    if not events:
        print("📭 No upcoming events in the next 7 days.")
        return

    print(f"📅 Found {len(events)} upcoming event(s)")
    parishioners = get_active_parishioners()
    print(f"👥 Sending to {len(parishioners)} active parishioner(s)...")

    for p in parishioners:
        send_reminder(p['email'], p['full_name'], events)

    print("✅ All reminders sent!")

if __name__ == '__main__':
    run_reminders()
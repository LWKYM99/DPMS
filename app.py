from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def init_db():
    conn = sqlite3.connect('dpms.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS Parishioners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT NOT NULL,
        phone TEXT,
        email TEXT,
        gender TEXT,
        date_of_birth TEXT,
        join_date TEXT,
        status TEXT NOT NULL DEFAULT 'Active')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        event_date TEXT NOT NULL,
        location TEXT,
        description TEXT,
        created_at TEXT DEFAULT (date('now')))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parishioner_id INTEGER,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        contribution_date TEXT NOT NULL,
        notes TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS sacraments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parishioner_id INTEGER,
        sacrament_type TEXT NOT NULL,
        date_received TEXT,
        officiant TEXT,
        notes TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT (date('now')),
        audience TEXT DEFAULT 'All')''')
    conn.execute('''CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parishioner_id INTEGER,
        event_id INTEGER,
        attended TEXT DEFAULT 'Yes')''')
    conn.commit()
    conn.close()

app = Flask(__name__)
init_db()

def get_db():
    conn = sqlite3.connect('dpms.db')
    conn.row_factory = sqlite3.Row
    return conn

def send_email(to, subject, body):
    try:
        sender = os.environ.get('MAIL_USERNAME')
        password = os.environ.get('MAIL_PASSWORD')
        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender, password)
        server.sendmail(sender, to, msg.as_string())
        server.quit()
    except Exception as e:
        print(f"Email error: {e}")

@app.route('/')
def home():
    db = get_db()
    parishioners = db.execute('SELECT * FROM Parishioners').fetchall()
    events = db.execute('SELECT * FROM events').fetchall()
    contributions = db.execute('SELECT * FROM contributions').fetchall()
    sacraments = db.execute('SELECT * FROM sacraments').fetchall()
    db.close()
    return render_template('home.html',
        parishioners=parishioners,
        events=events,
        contributions=contributions,
        sacraments=sacraments)

# ── Parishioners ──────────────────────────────────────────
@app.route('/parishioners')
def parishioners():
    db = get_db()
    data = db.execute('SELECT * FROM Parishioners').fetchall()
    db.close()
    return render_template('parishioners.html', parishioners=data)

@app.route('/parishioners/add', methods=['GET', 'POST'])
def add_parishioner():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO Parishioners (full_name, phone, email, gender, date_of_birth, join_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            [request.form['full_name'], request.form['phone'],
             request.form['email'], request.form['gender'],
             request.form['date_of_birth'], request.form['join_date'],
             request.form['status']])
        db.commit()
        if request.form['email']:
            send_email(
                request.form['email'],
                'Welcome to Our Parish!',
                f"<h2>Welcome, {request.form['full_name']}!</h2><p>You have been successfully registered in our parish management system.</p><p>God bless you!</p>"
            )
        db.close()
        return redirect(url_for('parishioners'))
    return render_template('add_parishioner.html')

@app.route('/parishioners/edit/<int:id>', methods=['GET', 'POST'])
def edit_parishioner(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE Parishioners SET full_name=?, phone=?, email=?, gender=?, date_of_birth=?, join_date=?, status=? WHERE id=?',
            [request.form['full_name'], request.form['phone'],
             request.form['email'], request.form['gender'],
             request.form['date_of_birth'], request.form['join_date'],
             request.form['status'], id])
        db.commit()
        db.close()
        return redirect(url_for('parishioners'))
    parishioner = db.execute('SELECT * FROM Parishioners WHERE id=?', [id]).fetchone()
    db.close()
    return render_template('edit_parishioner.html', p=parishioner)

@app.route('/parishioners/delete/<int:id>')
def delete_parishioner(id):
    db = get_db()
    db.execute('DELETE FROM Parishioners WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('parishioners'))

# ── Events ────────────────────────────────────────────────
@app.route('/events')
def events():
    db = get_db()
    data = db.execute('SELECT * FROM events').fetchall()
    db.close()
    return render_template('events.html', events=data)

@app.route('/events/add', methods=['GET', 'POST'])
def add_event():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO events (title, event_date, location, description) VALUES (?, ?, ?, ?)',
            [request.form['title'], request.form['event_date'],
             request.form['location'], request.form['description']])
        db.commit()
        parishioners = db.execute('SELECT email, full_name FROM Parishioners WHERE email IS NOT NULL AND email != ""').fetchall()
        for p in parishioners:
            send_email(
                p['email'],
                f"New Event: {request.form['title']}",
                f"<h2>New Event Announced!</h2><p>Dear {p['full_name']},</p><p><strong>{request.form['title']}</strong> is scheduled for <strong>{request.form['event_date']}</strong> at {request.form['location']}.</p><p>{request.form['description']}</p>"
            )
        db.close()
        return redirect(url_for('events'))
    return render_template('add_event.html')

@app.route('/events/edit/<int:id>', methods=['GET', 'POST'])
def edit_event(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE events SET title=?, event_date=?, location=?, description=? WHERE id=?',
            [request.form['title'], request.form['event_date'],
             request.form['location'], request.form['description'], id])
        db.commit()
        db.close()
        return redirect(url_for('events'))
    event = db.execute('SELECT * FROM events WHERE id=?', [id]).fetchone()
    db.close()
    return render_template('edit_event.html', e=event)

@app.route('/events/delete/<int:id>')
def delete_event(id):
    db = get_db()
    db.execute('DELETE FROM events WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('events'))

# ── Contributions ─────────────────────────────────────────
@app.route('/contributions')
def contributions():
    db = get_db()
    data = db.execute('''SELECT c.*, p.full_name 
                        FROM contributions c 
                        JOIN Parishioners p ON c.parishioner_id = p.id''').fetchall()
    db.close()
    return render_template('contributions.html', contributions=data)

@app.route('/contributions/add', methods=['GET', 'POST'])
def add_contribution():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO contributions (parishioner_id, amount, category, contribution_date, notes) VALUES (?, ?, ?, ?, ?)',
            [request.form['parishioner_id'], request.form['amount'],
             request.form['category'], request.form['contribution_date'],
             request.form['notes']])
        db.commit()
        parishioner = db.execute('SELECT * FROM Parishioners WHERE id=?', [request.form['parishioner_id']]).fetchone()
        if parishioner and parishioner['email']:
            send_email(
                parishioner['email'],
                'Contribution Receipt',
                f"<h2>Contribution Received</h2><p>Dear {parishioner['full_name']},</p><p>Thank you for your contribution of <strong>KSh {request.form['amount']}</strong> ({request.form['category']}) on {request.form['contribution_date']}.</p><p>God bless you!</p>"
            )
        db.close()
        return redirect(url_for('contributions'))
    db = get_db()
    parishioners = db.execute('SELECT id, full_name FROM Parishioners').fetchall()
    db.close()
    return render_template('add_contribution.html', parishioners=parishioners)

@app.route('/contributions/edit/<int:id>', methods=['GET', 'POST'])
def edit_contribution(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE contributions SET parishioner_id=?, amount=?, category=?, contribution_date=?, notes=? WHERE id=?',
            [request.form['parishioner_id'], request.form['amount'],
             request.form['category'], request.form['contribution_date'],
             request.form['notes'], id])
        db.commit()
        db.close()
        return redirect(url_for('contributions'))
    contribution = db.execute('SELECT * FROM contributions WHERE id=?', [id]).fetchone()
    parishioners = db.execute('SELECT id, full_name FROM Parishioners').fetchall()
    db.close()
    return render_template('edit_contribution.html', c=contribution, parishioners=parishioners)

@app.route('/contributions/delete/<int:id>')
def delete_contribution(id):
    db = get_db()
    db.execute('DELETE FROM contributions WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('contributions'))

# ── Sacraments ────────────────────────────────────────────
@app.route('/sacraments')
def sacraments():
    db = get_db()
    data = db.execute('''SELECT s.*, p.full_name 
                        FROM sacraments s 
                        JOIN Parishioners p ON s.parishioner_id = p.id''').fetchall()
    db.close()
    return render_template('sacraments.html', sacraments=data)

@app.route('/sacraments/add', methods=['GET', 'POST'])
def add_sacrament():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO sacraments (parishioner_id, sacrament_type, date_received, officiant, notes) VALUES (?, ?, ?, ?, ?)',
            [request.form['parishioner_id'], request.form['sacrament_type'],
             request.form['date_received'], request.form['officiant'],
             request.form['notes']])
        db.commit()
        parishioner = db.execute('SELECT * FROM Parishioners WHERE id=?', [request.form['parishioner_id']]).fetchone()
        if parishioner and parishioner['email']:
            send_email(
                parishioner['email'],
                f"Sacrament Record: {request.form['sacrament_type']}",
                f"<h2>Sacramental Record Added</h2><p>Dear {parishioner['full_name']},</p><p>Your <strong>{request.form['sacrament_type']}</strong> record has been recorded on {request.form['date_received']}.</p><p>Officiant: {request.form['officiant']}</p>"
            )
        db.close()
        return redirect(url_for('sacraments'))
    db = get_db()
    parishioners = db.execute('SELECT id, full_name FROM Parishioners').fetchall()
    db.close()
    return render_template('add_sacrament.html', parishioners=parishioners)

@app.route('/sacraments/edit/<int:id>', methods=['GET', 'POST'])
def edit_sacrament(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE sacraments SET parishioner_id=?, sacrament_type=?, date_received=?, officiant=?, notes=? WHERE id=?',
            [request.form['parishioner_id'], request.form['sacrament_type'],
             request.form['date_received'], request.form['officiant'],
             request.form['notes'], id])
        db.commit()
        db.close()
        return redirect(url_for('sacraments'))
    sacrament = db.execute('SELECT * FROM sacraments WHERE id=?', [id]).fetchone()
    parishioners = db.execute('SELECT id, full_name FROM Parishioners').fetchall()
    db.close()
    return render_template('edit_sacrament.html', s=sacrament, parishioners=parishioners)

@app.route('/sacraments/delete/<int:id>')
def delete_sacrament(id):
    db = get_db()
    db.execute('DELETE FROM sacraments WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('sacraments'))

# ── Announcements ─────────────────────────────────────────
@app.route('/announcements')
def announcements():
    db = get_db()
    data = db.execute('SELECT * FROM announcements').fetchall()
    db.close()
    return render_template('announcements.html', announcements=data)

@app.route('/announcements/add', methods=['GET', 'POST'])
def add_announcement():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO announcements (title, message, audience) VALUES (?, ?, ?)',
            [request.form['title'], request.form['message'],
             request.form['audience']])
        db.commit()
        parishioners = db.execute('SELECT email, full_name FROM Parishioners WHERE email IS NOT NULL AND email != ""').fetchall()
        for p in parishioners:
            send_email(
                p['email'],
                f"Parish Announcement: {request.form['title']}",
                f"<h2>{request.form['title']}</h2><p>Dear {p['full_name']},</p><p>{request.form['message']}</p><p><small>Audience: {request.form['audience']}</small></p>"
            )
        db.close()
        return redirect(url_for('announcements'))
    return render_template('add_announcement.html')

@app.route('/announcements/edit/<int:id>', methods=['GET', 'POST'])
def edit_announcement(id):
    db = get_db()
    if request.method == 'POST':
        db.execute('UPDATE announcements SET title=?, message=?, audience=? WHERE id=?',
            [request.form['title'], request.form['message'],
             request.form['audience'], id])
        db.commit()
        db.close()
        return redirect(url_for('announcements'))
    announcement = db.execute('SELECT * FROM announcements WHERE id=?', [id]).fetchone()
    db.close()
    return render_template('edit_announcement.html', a=announcement)

@app.route('/announcements/delete/<int:id>')
def delete_announcement(id):
    db = get_db()
    db.execute('DELETE FROM announcements WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('announcements'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
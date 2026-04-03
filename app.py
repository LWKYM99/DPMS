from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os
import urllib.request
import urllib.parse
import json
import base64
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'admin')''')
    existing = conn.execute('SELECT * FROM users WHERE username = "admin"').fetchone()
    if not existing:
        hashed = generate_password_hash('admin123')
        conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)',
            ['admin', hashed, 'admin'])
    conn.commit()
    conn.close()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dpms-secret-key-2024')
init_db()

def get_db():
    conn = sqlite3.connect('dpms.db')
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def send_sms(to, message):
    try:
        account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        from_number = os.environ.get('TWILIO_PHONE')
        to = to.strip()
        if to.startswith('0'):
            to = '+254' + to[1:]
        elif not to.startswith('+'):
            to = '+254' + to
        data = urllib.parse.urlencode({
            'From': from_number,
            'To': to,
            'Body': message
        }).encode('utf-8')
        url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json'
        req = urllib.request.Request(url, data=data, method='POST')
        credentials = base64.b64encode(f'{account_sid}:{auth_token}'.encode()).decode()
        req.add_header('Authorization', f'Basic {credentials}')
        urllib.request.urlopen(req)
        print(f"SMS sent to {to}")
    except Exception as e:
        print(f"SMS error: {e}")

# ── Auth ──────────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', [username]).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('home'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form['current_password']
        new = request.form['new_password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id=?', [session['user_id']]).fetchone()
        if check_password_hash(user['password'], current):
            db.execute('UPDATE users SET password=? WHERE id=?',
                [generate_password_hash(new), session['user_id']])
            db.commit()
            db.close()
            flash('Password changed successfully!')
            return redirect(url_for('home'))
        else:
            db.close()
            flash('Current password is incorrect!')
    return render_template('change_password.html')

# ── Home ──────────────────────────────────────────────────
@app.route('/')
@login_required
def home():
    db = get_db()
    parishioners = db.execute('SELECT * FROM Parishioners').fetchall()
    events = db.execute('SELECT * FROM events').fetchall()
    contributions = db.execute('SELECT * FROM contributions').fetchall()
    sacraments = db.execute('SELECT * FROM sacraments').fetchall()

    contrib_rows = db.execute('SELECT category, SUM(amount) FROM contributions GROUP BY category').fetchall()
    contrib_categories = [r[0] for r in contrib_rows]
    contrib_amounts = [r[1] for r in contrib_rows]

    sacrament_rows = db.execute('SELECT sacrament_type, COUNT(*) FROM sacraments GROUP BY sacrament_type').fetchall()
    sacrament_types = [r[0] for r in sacrament_rows]
    sacrament_counts = [r[1] for r in sacrament_rows]

    db.close()
    return render_template('home.html',
        parishioners=parishioners,
        events=events,
        contributions=contributions,
        sacraments=sacraments,
        contrib_categories=contrib_categories,
        contrib_amounts=contrib_amounts,
        sacrament_types=sacrament_types,
        sacrament_counts=sacrament_counts)

# ── Parishioners ──────────────────────────────────────────
@app.route('/parishioners')
@login_required
def parishioners():
    db = get_db()
    data = db.execute('SELECT * FROM Parishioners').fetchall()
    db.close()
    return render_template('parishioners.html', parishioners=data)

@app.route('/parishioners/add', methods=['GET', 'POST'])
@login_required
def add_parishioner():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO Parishioners (full_name, phone, email, gender, date_of_birth, join_date, status) VALUES (?, ?, ?, ?, ?, ?, ?)',
            [request.form['full_name'], request.form['phone'],
             request.form['email'], request.form['gender'],
             request.form['date_of_birth'], request.form['join_date'],
             request.form['status']])
        db.commit()
        if request.form['phone']:
            send_sms(request.form['phone'],
                f"Welcome to our Parish, {request.form['full_name']}! You have been successfully registered. God bless you!")
        db.close()
        return redirect(url_for('parishioners'))
    return render_template('add_parishioner.html')

@app.route('/parishioners/edit/<int:id>', methods=['GET', 'POST'])
@login_required
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
@login_required
def delete_parishioner(id):
    db = get_db()
    db.execute('DELETE FROM Parishioners WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('parishioners'))

# ── Events ────────────────────────────────────────────────
@app.route('/events')
@login_required
def events():
    db = get_db()
    data = db.execute('SELECT * FROM events').fetchall()
    db.close()
    return render_template('events.html', events=data)

@app.route('/events/add', methods=['GET', 'POST'])
@login_required
def add_event():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO events (title, event_date, location, description) VALUES (?, ?, ?, ?)',
            [request.form['title'], request.form['event_date'],
             request.form['location'], request.form['description']])
        db.commit()
        parishioners = db.execute('SELECT phone, full_name FROM Parishioners WHERE phone IS NOT NULL AND phone != ""').fetchall()
        for p in parishioners:
            send_sms(p['phone'],
                f"New Event: {request.form['title']} on {request.form['event_date']} at {request.form['location']}.")
        db.close()
        return redirect(url_for('events'))
    return render_template('add_event.html')

@app.route('/events/edit/<int:id>', methods=['GET', 'POST'])
@login_required
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
@login_required
def delete_event(id):
    db = get_db()
    db.execute('DELETE FROM events WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('events'))

# ── Contributions ─────────────────────────────────────────
@app.route('/contributions')
@login_required
def contributions():
    db = get_db()
    data = db.execute('''SELECT c.*, p.full_name 
                        FROM contributions c 
                        JOIN Parishioners p ON c.parishioner_id = p.id''').fetchall()
    db.close()
    return render_template('contributions.html', contributions=data)

@app.route('/contributions/add', methods=['GET', 'POST'])
@login_required
def add_contribution():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO contributions (parishioner_id, amount, category, contribution_date, notes) VALUES (?, ?, ?, ?, ?)',
            [request.form['parishioner_id'], request.form['amount'],
             request.form['category'], request.form['contribution_date'],
             request.form['notes']])
        db.commit()
        parishioner = db.execute('SELECT * FROM Parishioners WHERE id=?', [request.form['parishioner_id']]).fetchone()
        if parishioner and parishioner['phone']:
            send_sms(parishioner['phone'],
                f"Dear {parishioner['full_name']}, your contribution of KSh {request.form['amount']} ({request.form['category']}) on {request.form['contribution_date']} has been received. Thank you!")
        db.close()
        return redirect(url_for('contributions'))
    db = get_db()
    parishioners = db.execute('SELECT id, full_name FROM Parishioners').fetchall()
    db.close()
    return render_template('add_contribution.html', parishioners=parishioners)

@app.route('/contributions/edit/<int:id>', methods=['GET', 'POST'])
@login_required
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
@login_required
def delete_contribution(id):
    db = get_db()
    db.execute('DELETE FROM contributions WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('contributions'))

# ── Sacraments ────────────────────────────────────────────
@app.route('/sacraments')
@login_required
def sacraments():
    db = get_db()
    data = db.execute('''SELECT s.*, p.full_name 
                        FROM sacraments s 
                        JOIN Parishioners p ON s.parishioner_id = p.id''').fetchall()
    db.close()
    return render_template('sacraments.html', sacraments=data)

@app.route('/sacraments/add', methods=['GET', 'POST'])
@login_required
def add_sacrament():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO sacraments (parishioner_id, sacrament_type, date_received, officiant, notes) VALUES (?, ?, ?, ?, ?)',
            [request.form['parishioner_id'], request.form['sacrament_type'],
             request.form['date_received'], request.form['officiant'],
             request.form['notes']])
        db.commit()
        parishioner = db.execute('SELECT * FROM Parishioners WHERE id=?', [request.form['parishioner_id']]).fetchone()
        if parishioner and parishioner['phone']:
            send_sms(parishioner['phone'],
                f"Dear {parishioner['full_name']}, your {request.form['sacrament_type']} record has been added on {request.form['date_received']}.")
        db.close()
        return redirect(url_for('sacraments'))
    db = get_db()
    parishioners = db.execute('SELECT id, full_name FROM Parishioners').fetchall()
    db.close()
    return render_template('add_sacrament.html', parishioners=parishioners)

@app.route('/sacraments/edit/<int:id>', methods=['GET', 'POST'])
@login_required
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
@login_required
def delete_sacrament(id):
    db = get_db()
    db.execute('DELETE FROM sacraments WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('sacraments'))

# ── Announcements ─────────────────────────────────────────
@app.route('/announcements')
@login_required
def announcements():
    db = get_db()
    data = db.execute('SELECT * FROM announcements').fetchall()
    db.close()
    return render_template('announcements.html', announcements=data)

@app.route('/announcements/add', methods=['GET', 'POST'])
@login_required
def add_announcement():
    if request.method == 'POST':
        db = get_db()
        db.execute('INSERT INTO announcements (title, message, audience) VALUES (?, ?, ?)',
            [request.form['title'], request.form['message'],
             request.form['audience']])
        db.commit()
        parishioners = db.execute('SELECT phone, full_name FROM Parishioners WHERE phone IS NOT NULL AND phone != ""').fetchall()
        for p in parishioners:
            send_sms(p['phone'],
                f"Parish Announcement: {request.form['title']} - {request.form['message']}")
        db.close()
        return redirect(url_for('announcements'))
    return render_template('add_announcement.html')

@app.route('/announcements/edit/<int:id>', methods=['GET', 'POST'])
@login_required
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
@login_required
def delete_announcement(id):
    db = get_db()
    db.execute('DELETE FROM announcements WHERE id=?', [id])
    db.commit()
    db.close()
    return redirect(url_for('announcements'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
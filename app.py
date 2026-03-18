from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect('dpms.db')
    conn.row_factory = sqlite3.Row
    return conn

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
        db.close()
        return redirect(url_for('parishioners'))
    return render_template('add_parishioner.html')

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
        db.close()
        return redirect(url_for('events'))
    return render_template('add_event.html')

@app.route('/contributions')
def contributions():
    db = get_db()
    data = db.execute('''SELECT c.*, p.full_name 
                        FROM contributions c 
                        JOIN Parishioners p ON c.parishioner_id = p.id''').fetchall()
    db.close()
    return render_template('contributions.html', contributions=data)

@app.route('/sacraments')
def sacraments():
    db = get_db()
    data = db.execute('''SELECT s.*, p.full_name 
                        FROM sacraments s 
                        JOIN Parishioners p ON s.parishioner_id = p.id''').fetchall()
    db.close()
    return render_template('sacraments.html', sacraments=data)

@app.route('/announcements')
def announcements():
    db = get_db()
    data = db.execute('SELECT * FROM announcements').fetchall()
    db.close()
    return render_template('announcements.html', announcements=data)

if __name__ == '__main__':
    app.run(debug=True)
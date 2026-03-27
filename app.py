from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import psycopg2
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# PostgreSQL Connection
DATABASE_URL = os.environ.get("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# Initialize Tables
def init_db():
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            wallet NUMERIC NOT NULL DEFAULT 0
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS counter (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            value INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()
    cur.close()

init_db()

# ---------------- Routes ----------------
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = conn.cursor()
    # Counter value
    cur.execute("SELECT value FROM counter WHERE user_id=%s;", (user_id,))
    result = cur.fetchone()
    value = result[0] if result else 0
    # Wallet value
    cur.execute("SELECT wallet FROM users WHERE id=%s;", (user_id,))
    wallet = cur.fetchone()[0]
    cur.close()
    # Games menu
    games = ["Tic-Tac-Toe", "Snake", "Minesweeper", "Puzzle"]
    return render_template('dashboard.html', value=value, wallet=wallet, games=games)

@app.route('/increment', methods=['POST'])
def increment():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id = session['user_id']
    cur = conn.cursor()
    cur.execute("SELECT value FROM counter WHERE user_id=%s;", (user_id,))
    result = cur.fetchone()
    if result:
        new_value = result[0] + 1
        cur.execute("UPDATE counter SET value=%s WHERE user_id=%s;", (new_value, user_id))
    else:
        new_value = 1
        cur.execute("INSERT INTO counter (user_id, value) VALUES (%s,%s);", (user_id, new_value))
    conn.commit()
    cur.close()
    return jsonify({"value": new_value})

@app.route('/wallet/add', methods=['POST'])
def wallet_add():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    amount = float(request.json.get("amount", 0))
    user_id = session['user_id']
    cur = conn.cursor()
    cur.execute("UPDATE users SET wallet = wallet + %s WHERE id=%s RETURNING wallet;", (amount, user_id))
    new_wallet = cur.fetchone()[0]
    conn.commit()
    cur.close()
    return jsonify({"wallet": float(new_wallet)})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Registration and Login (unchanged)
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username,password) VALUES (%s,%s) RETURNING id;", (username,password))
            user_id = cur.fetchone()[0]
            conn.commit()
            session['user_id'] = user_id
            session['username'] = username
            return redirect(url_for('home'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            flash("Username already exists!", "error")
        finally:
            cur.close()
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE username=%s;", (username,))
        user = cur.fetchone()
        cur.close()
        if user and user[1] == password:
            session['user_id'] = user[0]
            session['username'] = username
            return redirect(url_for('home'))
        else:
            flash("Invalid credentials!", "error")
    return render_template('login.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

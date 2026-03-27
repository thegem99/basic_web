from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

# DATABASE URL from Railway
DATABASE_URL = os.environ.get('DATABASE_URL')  # e.g., postgres://user:pass@host:port/db
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# Initialize tables safely
def init_db():
    cur = conn.cursor()
    try:
        # Users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                wallet NUMERIC NOT NULL DEFAULT 0
            );
        """)
        # Counter table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS counter (
                user_id INTEGER PRIMARY KEY REFERENCES users(id),
                value INTEGER NOT NULL DEFAULT 0
            );
        """)
        conn.commit()
    except Exception as e:
        print("DB Init Error:", e)
        conn.rollback()
    finally:
        cur.close()

init_db()

# HOME / COUNTER PAGE
@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    username = session['username']
    cur = conn.cursor()
    counter_value = 0
    wallet = 0
    try:
        cur.execute("SELECT value FROM counter WHERE user_id=%s;", (user_id,))
        result = cur.fetchone()
        counter_value = result[0] if result else 0

        cur.execute("SELECT wallet FROM users WHERE id=%s;", (user_id,))
        wallet_result = cur.fetchone()
        wallet = wallet_result[0] if wallet_result else 0
    except Exception as e:
        conn.rollback()
        print("Home Error:", e)
    finally:
        cur.close()

    games = ["Tic Tac Toe", "Snake", "Quiz", "Memory Game"]  # example menu
    return render_template("index.html", username=username, counter=counter_value, wallet=wallet, games=games)

# INCREMENT COUNTER (AJAX)
@app.route('/increment', methods=['POST'])
def increment():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    user_id = session['user_id']
    cur = conn.cursor()
    try:
        cur.execute("SELECT value FROM counter WHERE user_id=%s;", (user_id,))
        result = cur.fetchone()
        if result:
            new_value = result[0] + 1
            cur.execute("UPDATE counter SET value=%s WHERE user_id=%s;", (new_value, user_id))
        else:
            new_value = 1
            cur.execute("INSERT INTO counter (user_id, value) VALUES (%s,%s);", (user_id, new_value))
        conn.commit()
        return jsonify({"value": new_value})
    except Exception as e:
        conn.rollback()
        print("Increment Error:", e)
        return jsonify({"error": "Something went wrong"}), 500
    finally:
        cur.close()

# REGISTER
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users (username, password) VALUES (%s,%s) RETURNING id;", (username,password))
            user_id = cur.fetchone()[0]
            conn.commit()
            session['user_id'] = user_id
            session['username'] = username
            return redirect(url_for('home'))
        except Exception as e:
            conn.rollback()
            print("Register Error:", e)
            return "Error: Username may already exist."
        finally:
            cur.close()
    return render_template("register.html")

# LOGIN
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cur = conn.cursor()
        try:
            cur.execute("SELECT id, password FROM users WHERE username=%s;", (username,))
            result = cur.fetchone()
            if result and result[1] == password:
                session['user_id'] = result[0]
                session['username'] = username
                return redirect(url_for('home'))
            else:
                return "Invalid credentials."
        except Exception as e:
            conn.rollback()
            print("Login Error:", e)
            return "Login error."
        finally:
            cur.close()
    return render_template("login.html")

# LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

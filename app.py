import os
from flask import Flask, render_template, redirect, request, session, url_for, flash
import psycopg2
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")  # Use a real secret in production

DATABASE_URL = os.environ.get("DATABASE_URL")

# ------------------- Database -------------------
def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );
    """)

    # Counter table (one counter per user)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS counter (
            user_id INTEGER PRIMARY KEY REFERENCES users(id),
            value INTEGER NOT NULL DEFAULT 0
        );
    """)

    conn.commit()
    cur.close()
    conn.close()

# Auto-init DB on first request (works with Gunicorn on Railway)
@app.before_first_request
def setup():
    init_db()

# ------------------- Routes -------------------
@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM counter WHERE user_id=%s;", (user_id,))
    row = cur.fetchone()
    value = row[0] if row else 0
    cur.close()
    conn.close()

    return render_template("counter.html", value=value)

@app.route("/increment")
def increment():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_connection()
    cur = conn.cursor()
    # Insert row if missing, otherwise increment
    cur.execute("""
        INSERT INTO counter (user_id, value)
        VALUES (%s, 1)
        ON CONFLICT (user_id) DO UPDATE SET value = counter.value + 1;
    """, (user_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("home"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed = generate_password_hash(password)

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO users (username, password) VALUES (%s, %s) RETURNING id;", (username, hashed))
            user_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for("login"))
        except psycopg2.errors.UniqueViolation:
            flash("Username already exists.", "error")
            conn.rollback()
            cur.close()
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, password FROM users WHERE username=%s;", (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["username"] = username
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials", "error")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ------------------- Run -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

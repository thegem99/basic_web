import os
from flask import Flask, render_template, redirect
import psycopg2

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS counter (
            id SERIAL PRIMARY KEY,
            value INTEGER NOT NULL
        );
    """)

    # Ensure one row exists
    cur.execute("SELECT * FROM counter WHERE id=1;")
    if cur.fetchone() is None:
        cur.execute("INSERT INTO counter (id, value) VALUES (1, 0);")

    conn.commit()
    cur.close()
    conn.close()


@app.route("/")
def index():
    # Ensure DB is initialized
    init_db()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM counter WHERE id=1;")
    value = cur.fetchone()[0]
    cur.close()
    conn.close()

    return render_template("index.html", value=value)


@app.route("/increment")
def increment():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE counter SET value = value + 1 WHERE id=1;")
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/")


# For local testing only
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

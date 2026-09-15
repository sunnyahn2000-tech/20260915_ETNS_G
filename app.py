import os
from datetime import datetime

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, request, url_for

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS todos (
                    id SERIAL PRIMARY KEY,
                    task TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE,
                    created_at TEXT NOT NULL
                )
                """
            )
        conn.commit()
    finally:
        conn.close()


@app.route("/")
def index():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM todos ORDER BY done ASC, id DESC")
        todos = cur.fetchall()
    total = len(todos)
    done_count = sum(1 for t in todos if t["done"])
    return render_template(
        "index.html", todos=todos, total=total, done_count=done_count
    )


@app.route("/add", methods=["POST"])
def add():
    task = request.form.get("task", "").strip()
    if task:
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO todos (task, done, created_at) VALUES (%s, FALSE, %s)",
                (task, datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
        db.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
def toggle(todo_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE todos SET done = NOT done WHERE id = %s", (todo_id,)
        )
    db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM todos WHERE id = %s", (todo_id,))
    db.commit()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

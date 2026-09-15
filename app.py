import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, g, redirect, render_template, request, url_for

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "todo.db"

app = Flask(__name__)


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )


@app.route("/")
def index():
    db = get_db()
    todos = db.execute(
        "SELECT * FROM todos ORDER BY done ASC, id DESC"
    ).fetchall()
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
        db.execute(
            "INSERT INTO todos (task, done, created_at) VALUES (?, 0, ?)",
            (task, datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        db.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
def toggle(todo_id):
    db = get_db()
    db.execute(
        "UPDATE todos SET done = 1 - done WHERE id = ?", (todo_id,)
    )
    db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    db = get_db()
    db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    db.commit()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

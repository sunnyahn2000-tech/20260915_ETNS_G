import os
from datetime import datetime
from functools import wraps

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]

app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]


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
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
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
            cur.execute(
                "ALTER TABLE todos ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)"
            )
        conn.commit()
    finally:
        conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None
        if not username or not password:
            error = "아이디와 비밀번호를 모두 입력해주세요."
        elif len(password) < 4:
            error = "비밀번호는 4자 이상이어야 합니다."

        if error is None:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone():
                    error = "이미 사용 중인 아이디입니다."

        if error is None:
            db = get_db()
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (username, password_hash, created_at) VALUES (%s, %s, %s)",
                    (username, generate_password_hash(password), datetime.now().strftime("%Y-%m-%d %H:%M")),
                )
            db.commit()
            return redirect(url_for("login"))

        return render_template("register.html", error=error, username=username)

    return render_template("register.html", error=None, username="")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="아이디 또는 비밀번호가 올바르지 않습니다.", username=username)

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect(url_for("index"))

    return render_template("login.html", error=None, username="")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def index():
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM todos WHERE user_id = %s ORDER BY done ASC, id DESC",
            (session["user_id"],),
        )
        todos = cur.fetchall()
    total = len(todos)
    done_count = sum(1 for t in todos if t["done"])
    return render_template(
        "index.html", todos=todos, total=total, done_count=done_count, username=session["username"]
    )


@app.route("/add", methods=["POST"])
@login_required
def add():
    task = request.form.get("task", "").strip()
    if task:
        db = get_db()
        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO todos (task, done, created_at, user_id) VALUES (%s, FALSE, %s, %s)",
                (task, datetime.now().strftime("%Y-%m-%d %H:%M"), session["user_id"]),
            )
        db.commit()
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
@login_required
def toggle(todo_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "UPDATE todos SET done = NOT done WHERE id = %s AND user_id = %s",
            (todo_id, session["user_id"]),
        )
    db.commit()
    return redirect(url_for("index"))


@app.route("/delete/<int:todo_id>", methods=["POST"])
@login_required
def delete(todo_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM todos WHERE id = %s AND user_id = %s",
            (todo_id, session["user_id"]),
        )
    db.commit()
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

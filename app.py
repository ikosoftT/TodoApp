import os

import psycopg
from flask import Flask, jsonify, render_template, request
from psycopg.rows import dict_row


app = Flask(__name__)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    return database_url


def get_connection():
    return psycopg.connect(
        get_database_url(),
        connect_timeout=10,
        row_factory=dict_row,
    )


def ensure_schema(connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL CHECK (char_length(text) BETWEEN 1 AND 500),
            completed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at BIGINT NOT NULL
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS todos_created_at_idx ON todos (created_at DESC)"
    )


def validate_tasks(value):
    if not isinstance(value, list) or len(value) > 1000:
        return None

    tasks = []
    seen_ids = set()
    for task in value:
        if not isinstance(task, dict):
            return None

        task_id = task.get("id")
        text = task.get("text")
        completed = task.get("completed")
        created_at = task.get("createdAt")

        if (
            not isinstance(task_id, str)
            or not task_id
            or len(task_id) > 100
            or task_id in seen_ids
            or not isinstance(text, str)
            or not text.strip()
            or len(text.strip()) > 500
            or not isinstance(completed, bool)
            or not isinstance(created_at, int)
            or isinstance(created_at, bool)
        ):
            return None

        seen_ids.add(task_id)
        tasks.append((task_id, text.strip(), completed, created_at))

    return tasks


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/todos", methods=["GET"])
def get_tasks():
    try:
        with get_connection() as connection:
            ensure_schema(connection)
            rows = connection.execute(
                "SELECT id, text, completed, created_at FROM todos "
                "ORDER BY created_at DESC"
            ).fetchall()
    except (psycopg.Error, RuntimeError):
        app.logger.exception("Could not load todos")
        return jsonify({"error": "Database is unavailable"}), 503

    return jsonify(
        [
            {
                "id": row["id"],
                "text": row["text"],
                "completed": row["completed"],
                "createdAt": row["created_at"],
            }
            for row in rows
        ]
    )


@app.route("/api/todos", methods=["POST"])
def save_tasks():
    tasks = validate_tasks(request.get_json(silent=True))
    if tasks is None:
        return jsonify({"error": "Invalid todo list"}), 400

    try:
        with get_connection() as connection:
            ensure_schema(connection)

            if tasks:
                connection.executemany(
                    """
                    INSERT INTO todos (id, text, completed, created_at)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text,
                        completed = EXCLUDED.completed,
                        created_at = EXCLUDED.created_at
                    """,
                    tasks,
                )
                connection.execute(
                    "DELETE FROM todos WHERE NOT (id = ANY(%s))",
                    ([task[0] for task in tasks],),
                )
            else:
                connection.execute("DELETE FROM todos")
    except (psycopg.Error, RuntimeError):
        app.logger.exception("Could not save todos")
        return jsonify({"error": "Database is unavailable"}), 503

    return jsonify({"status": "success"})


if __name__ == "__main__":
    app.run(debug=True)

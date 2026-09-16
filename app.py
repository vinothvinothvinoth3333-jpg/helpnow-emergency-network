import re
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = "helpnow-development-key"
DATABASE_PATH = Path(__file__).parent / "database" / "helpnow.db"


def get_connection():
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def ensure_database():
    """Create the schema and an anonymous user before the app serves requests."""
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                phone TEXT,
                role TEXT DEFAULT 'user',
                verified INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS emergency_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                description TEXT,
                latitude REAL,
                longitude REAL,
                live_location INTEGER DEFAULT 0,
                location_updated_at TIMESTAMP,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'normal',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS helpers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service_type TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                verified INTEGER DEFAULT 0,
                available INTEGER DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emergency_id INTEGER NOT NULL,
                helper_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (emergency_id) REFERENCES emergency_reports(id),
                FOREIGN KEY (helper_id) REFERENCES helpers(id)
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                emergency_id INTEGER,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (emergency_id) REFERENCES emergency_reports(id)
            );
            INSERT OR IGNORE INTO users (name, email, password)
            VALUES ('Guest', 'guest@helpnow.local', '');
            INSERT OR IGNORE INTO users (name, email, password, role, verified)
            VALUES ('HelpNow Owner', 'owner', '', 'owner', 1);
            """
        )
        owner = connection.execute(
            "SELECT id, password FROM users WHERE email = ? AND role = 'owner'",
            ("owner",),
        ).fetchone()
        if owner and not owner["password"]:
            connection.execute(
                "UPDATE users SET password = ? WHERE id = ?",
                (generate_password_hash("helpnow123"), owner["id"]),
            )
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(emergency_reports)")
        }
        if "recipient_phone" not in columns:
            connection.execute(
                "ALTER TABLE emergency_reports ADD COLUMN recipient_phone TEXT"
            )
        if "live_location" not in columns:
            connection.execute(
                "ALTER TABLE emergency_reports ADD COLUMN live_location INTEGER DEFAULT 0"
            )
        if "location_updated_at" not in columns:
            connection.execute(
                "ALTER TABLE emergency_reports ADD COLUMN location_updated_at TIMESTAMP"
            )


ensure_database()


def normalize_contact_number(phone):
    phone = phone.strip().replace(" ", "").replace("-", "")
    if not phone:
        return None
    if phone.startswith("0"):
        phone = "+94" + phone[1:]
    elif phone.startswith("94"):
        phone = "+" + phone
    if not re.fullmatch(r"\+947\d{8}", phone):
        raise ValueError("Enter a valid Sri Lankan mobile number.")
    return phone


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/report", methods=["GET", "POST"])
def report():
    if request.method == "POST":
        emergency_type = request.form.get("emergency_type", "").strip()
        description = request.form.get("description", "").strip()
        contact_number = request.form.get("contact_number", "")

        if not emergency_type or not description:
            return render_template(
                "report.html",
                error="Emergency type and description are required.",
            ), 400

        try:
            contact_number = normalize_contact_number(contact_number)
        except ValueError as error:
            return render_template("report.html", error=str(error)), 400

        def coordinate(name):
            value = request.form.get(name, "").strip()
            return float(value) if value else None

        try:
            latitude = coordinate("latitude")
            longitude = coordinate("longitude")
        except ValueError:
            return render_template(
                "report.html",
                error="Latitude and longitude must be valid numbers.",
            ), 400

        live_location = 1 if request.form.get("share_live_location") == "on" else 0

        with get_connection() as connection:
            guest = connection.execute(
                "SELECT id FROM users WHERE email = ?",
                ("guest@helpnow.local",),
            ).fetchone()
            report_cursor = connection.execute(
                """
                INSERT INTO emergency_reports
                    (user_id, type, description, latitude, longitude, live_location,
                     location_updated_at, recipient_phone)
                VALUES (?, ?, ?, ?, ?, ?, CASE WHEN ? = 1 THEN CURRENT_TIMESTAMP ELSE NULL END, ?)
                """,
                (
                    guest["id"],
                    emergency_type,
                    description,
                    latitude,
                    longitude,
                    live_location,
                    live_location,
                    contact_number,
                ),
            )
            report_id = report_cursor.lastrowid
            connection.execute(
                """
                INSERT INTO notifications (user_id, emergency_id, message)
                VALUES (?, ?, ?)
                """,
                (
                    guest["id"],
                    report_id,
                    "HelpNow received your emergency report. We are looking for a nearby helper.",
                ),
            )
            owner = connection.execute(
                "SELECT id FROM users WHERE email = ?",
                ("owner",),
            ).fetchone()
            connection.execute(
                """
                INSERT INTO notifications (user_id, emergency_id, message)
                VALUES (?, ?, ?)
                """,
                (
                    owner["id"],
                    report_id,
                    f"New {emergency_type} emergency reported. Immediate assistance may be needed.",
                ),
            )

        return redirect(url_for("report", submitted=report_id, live=live_location))

    return render_template("report.html")


@app.route("/api/reports/<int:report_id>/location", methods=["POST"])
def update_report_location(report_id):
    data = request.get_json(silent=True) or {}
    try:
        latitude = float(data["latitude"])
        longitude = float(data["longitude"])
    except (KeyError, TypeError, ValueError):
        return jsonify(error="Valid latitude and longitude are required."), 400

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return jsonify(error="Coordinates are outside valid ranges."), 400

    with get_connection() as connection:
        result = connection.execute(
            """
            UPDATE emergency_reports
            SET latitude = ?, longitude = ?, live_location = 1,
                location_updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (latitude, longitude, report_id),
        )
        if result.rowcount == 0:
            return jsonify(error="Emergency report not found."), 404

    return jsonify(latitude=latitude, longitude=longitude)


@app.route("/api/reports/<int:report_id>/location/stop", methods=["POST"])
def stop_report_location(report_id):
    with get_connection() as connection:
        result = connection.execute(
            "UPDATE emergency_reports SET live_location = 0 WHERE id = ?",
            (report_id,),
        )
        if result.rowcount == 0:
            return jsonify(error="Emergency report not found."), 404

    return jsonify(stopped=True)


@app.route("/api/owner/reports")
def owner_report_locations():
    if session.get("owner_id") is None:
        return jsonify(error="Owner login required."), 401

    with get_connection() as connection:
        reports = connection.execute(
            """
            SELECT id, latitude, longitude, live_location, location_updated_at
            FROM emergency_reports
            ORDER BY id DESC
            """
        ).fetchall()

    return jsonify(
        reports=[
            {
                "id": report["id"],
                "latitude": report["latitude"],
                "longitude": report["longitude"],
                "live_location": bool(report["live_location"]),
                "location_updated_at": report["location_updated_at"],
            }
            for report in reports
        ]
    )


@app.route("/status/<int:report_id>")
def report_status(report_id):
    with get_connection() as connection:
        report_record = connection.execute(
            "SELECT * FROM emergency_reports WHERE id = ?",
            (report_id,),
        ).fetchone()
        notification = connection.execute(
            """
            SELECT notifications.message, notifications.created_at FROM notifications
            WHERE emergency_id = ?
            ORDER BY id DESC LIMIT 1
            """,
            (report_id,),
        ).fetchone()

    if report_record is None:
        return "Emergency report not found", 404

    return render_template(
        "status.html",
        report=report_record,
        notification=notification,
    )


@app.route("/owner")
def owner_dashboard():
    if session.get("owner_id") is None:
        return redirect(url_for("login", next="owner_dashboard"))

    with get_connection() as connection:
        reports = connection.execute(
            """
            SELECT emergency_reports.*, users.name AS reporter_name
            FROM emergency_reports
            JOIN users ON users.id = emergency_reports.user_id
            ORDER BY emergency_reports.id DESC
            """
        ).fetchall()
        notifications = connection.execute(
            """
            SELECT notifications.message, notifications.created_at
            FROM notifications
            JOIN users ON users.id = notifications.user_id
            WHERE users.email = ?
            ORDER BY notifications.id DESC
            LIMIT 20
            """,
            ("owner",),
        ).fetchall()

    return render_template(
        "owner.html",
        reports=reports,
        notifications=notifications,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_connection() as connection:
            owner = connection.execute(
                "SELECT id, password FROM users WHERE email = ? AND role = 'owner'",
                (username,),
            ).fetchone()

        if owner and check_password_hash(owner["password"], password):
            session["owner_id"] = owner["id"]
            destination = request.args.get("next", "owner_dashboard")
            return redirect(url_for(destination))

        return render_template("login.html", error="Invalid owner username or password."), 401

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("owner_id", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)
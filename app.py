import os
import re
import sqlite3
import uuid
import secrets
import shutil
import smtplib
import os
import json
import hmac
import hashlib
import base64
import urllib.request
import urllib.error
from email.message import EmailMessage
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from datetime import datetime
from functools import wraps
from flask import jsonify
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
    jsonify
)

from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = "smart-hostel-csp-secret-key-2026"

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

DATABASE = os.path.join(BASE_DIR, "database.db")

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "static",
    "uploads"
)

COMPLAINT_PHOTO_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    "complaint_photos"
)

RESOLUTION_PHOTO_FOLDER = os.path.join(
    UPLOAD_FOLDER,
    "resolution_photos"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "gif",
    "webp"
}


# ============================================================
# CREATE REQUIRED FOLDERS
# ============================================================

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(COMPLAINT_PHOTO_FOLDER, exist_ok=True)
os.makedirs(RESOLUTION_PHOTO_FOLDER, exist_ok=True)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_db():
    """
    Create SQLite connection with settings that reduce
    database locked errors.
    """

    conn = sqlite3.connect(
        DATABASE,
        timeout=30,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
    except sqlite3.Error:
        pass

    return conn


# ============================================================
# DATABASE HELPERS
# ============================================================

def column_exists(conn, table_name, column_name):

    columns = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return any(
        row["name"] == column_name
        for row in columns
    )


def add_column_if_missing(
    conn,
    table_name,
    column_name,
    column_definition
):

    if not column_exists(
        conn,
        table_name,
        column_name
    ):
        conn.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

def init_db():

    conn = get_db()

    # --------------------------------------------------------
    # USERS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            hostel_type TEXT,
            email TEXT,
            account_status TEXT NOT NULL DEFAULT 'approved'
        )
    """)

    # Existing database migration
    add_column_if_missing(
        conn,
        "users",
        "roll_number",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "users",
        "username",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "users",
        "password",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "users",
        "name",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "users",
        "role",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "users",
        "hostel_type",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "users",
        "account_status",
        "TEXT NOT NULL DEFAULT 'approved'"
    )

    add_column_if_missing(conn, "users", "email", "TEXT")

    # --------------------------------------------------------
    # STAFF
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            phone TEXT,
            department TEXT,
            hostel_type TEXT,
            FOREIGN KEY(user_id)
                REFERENCES users(id)
        )
    """)

    add_column_if_missing(
        conn,
        "staff",
        "user_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "staff",
        "name",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "staff",
        "phone",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "staff",
        "department",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "staff",
        "hostel_type",
        "TEXT"
    )

    # --------------------------------------------------------
    # COMPLAINTS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id TEXT UNIQUE,
            student_id INTEGER,
            hostel_type TEXT,
            room_number TEXT,
            category TEXT,
            description TEXT,
            photo TEXT,
            status TEXT DEFAULT 'Submitted',
            assigned_staff_id INTEGER,
            created_at TEXT,
            resolved_at TEXT,
            FOREIGN KEY(student_id)
                REFERENCES users(id),
            FOREIGN KEY(assigned_staff_id)
                REFERENCES staff(id)
        )
    """)

    add_column_if_missing(
        conn,
        "complaints",
        "complaint_id",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "student_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "hostel_type",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "room_number",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "category",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "description",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "photo",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "status",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "assigned_staff_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "created_at",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "resolved_at",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "resolution_photo",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "feedback_rating",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "feedback_comment",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaints",
        "feedback_at",
        "TEXT"
    )

    # --------------------------------------------------------
    # NOTIFICATIONS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            complaint_id INTEGER,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(complaint_id) REFERENCES complaints(id)
        )
    """)

    # --------------------------------------------------------
    # COMPLAINT UPDATES
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS complaint_updates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id INTEGER,
            status TEXT,
            note TEXT,
            updated_by INTEGER,
            updated_at TEXT,
            FOREIGN KEY(complaint_id)
                REFERENCES complaints(id),
            FOREIGN KEY(updated_by)
                REFERENCES users(id)
        )
    """)

    add_column_if_missing(
        conn,
        "complaint_updates",
        "complaint_id",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "complaint_updates",
        "status",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaint_updates",
        "note",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "complaint_updates",
        "updated_by",
        "INTEGER"
    )

    add_column_if_missing(
        conn,
        "complaint_updates",
        "updated_at",
        "TEXT"
    )

    # --------------------------------------------------------
    # GEC HOSTEL ROOM, ALLOCATION AND FEE MANAGEMENT (additive)
    # --------------------------------------------------------
    add_column_if_missing(conn, "users", "room_preference", "TEXT")
    add_column_if_missing(conn, "users", "room_type", "TEXT")
    add_column_if_missing(conn, "users", "room_number", "TEXT")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS hostel_floors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostel_type TEXT NOT NULL,
            floor_number INTEGER NOT NULL,
            created_by INTEGER,
            created_at TEXT,
            UNIQUE(hostel_type, floor_number),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hostel_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hostel_type TEXT NOT NULL,
            floor_id INTEGER NOT NULL,
            room_number TEXT NOT NULL,
            room_type TEXT NOT NULL CHECK(room_type IN ('Attached', 'Non-Attached')),
            capacity INTEGER NOT NULL,
            semester_rent REAL NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by INTEGER,
            created_at TEXT,
            UNIQUE(hostel_type, floor_id, room_number),
            FOREIGN KEY(floor_id) REFERENCES hostel_floors(id),
            FOREIGN KEY(created_by) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS room_allocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            room_id INTEGER NOT NULL,
            allocated_by INTEGER,
            allocated_at TEXT NOT NULL,
            vacated_at TEXT,
            status TEXT NOT NULL DEFAULT 'Active',
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(room_id) REFERENCES hostel_rooms(id),
            FOREIGN KEY(allocated_by) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hostel_fee_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            room_id INTEGER,
            semester TEXT NOT NULL,
            amount_due REAL NOT NULL,
            amount_paid REAL NOT NULL DEFAULT 0,
            payment_date TEXT,
            reference_number TEXT,
            note TEXT,
            recorded_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(room_id) REFERENCES hostel_rooms(id),
            FOREIGN KEY(recorded_by) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS mess_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            payment_option TEXT NOT NULL CHECK(payment_option IN ('Daily','Monthly','Other')),
            period_label TEXT NOT NULL,
            amount_due REAL NOT NULL,
            amount_paid REAL NOT NULL DEFAULT 0,
            payment_date TEXT,
            reference_number TEXT,
            note TEXT,
            recorded_by INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id),
            FOREIGN KEY(recorded_by) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS fee_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            fee_type TEXT NOT NULL CHECK(fee_type IN ('Hostel','Mess')),
            fee_record_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL CHECK(payment_method IN ('Online','Offline')),
            payment_id TEXT NOT NULL UNIQUE,
            status TEXT NOT NULL DEFAULT 'Paid',
            gateway_method TEXT DEFAULT 'UPI',
            created_at TEXT NOT NULL,
            FOREIGN KEY(student_id) REFERENCES users(id)
        )
    """)

    # Existing database migration: store how a fee record was settled.
    add_column_if_missing(conn, "hostel_fee_payments", "payment_method", "TEXT DEFAULT 'Offline'")
    add_column_if_missing(conn, "mess_payments", "payment_method", "TEXT DEFAULT 'Offline'")
    add_column_if_missing(conn, "fee_transactions", "gateway_method", "TEXT DEFAULT 'UPI'")
    add_column_if_missing(conn, "room_allocations", "semester", "TEXT DEFAULT '1st Semester'")

    # Create the five configured floors for each hostel if absent.
    # Room records are added by admin/warden because room types vary.
    for hostel_name in ("Boys", "Girls"):
        for floor_no in range(1, 6):
            conn.execute(
                "INSERT OR IGNORE INTO hostel_floors(hostel_type,floor_number,created_at) VALUES(?,?,?)",
                (hostel_name, floor_no, datetime.now().isoformat(timespec="seconds"))
            )

    conn.commit()
    conn.close()


# ============================================================
# DEMO USERS
# ============================================================

def ensure_demo_users():

    demo_users = [

        {
            "username": "boyswarden",
            "password": "boys123",
            "name": "Boys Warden",
            "role": "warden",
            "hostel_type": "Boys",
            "roll_number": None
        },

        {
            "username": "girlswarden",
            "password": "girls123",
            "name": "Girls Warden",
            "role": "warden",
            "hostel_type": "Girls",
            "roll_number": None
        },

        {
            "username": "admin",
            "password": "admin123",
            "name": "Hostel Admin",
            "role": "admin",
            "hostel_type": None,
            "roll_number": None
        },

        {
            "username": "24CSE1001",
            "password": "student123",
            "name": "Demo Student",
            "role": "student",
            "hostel_type": "Boys",
            "roll_number": "24CSE1001"
        }
    ]

    conn = get_db()

    for user in demo_users:

        existing = conn.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, (
            user["username"],
        )).fetchone()

        if existing:
            continue

        password_hash = generate_password_hash(
            user["password"]
        )

        try:

            conn.execute("""
                INSERT INTO users (
                    roll_number,
                    username,
                    password,
                    name,
                    role,
                    hostel_type,
                    email
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user["roll_number"],
                user["username"],
                password_hash,
                user["name"],
                user["role"],
                user["hostel_type"],
                user.get("email")
            ))

        except sqlite3.IntegrityError:

            # If roll number already exists,
            # don't crash the application.
            continue

    conn.commit()
    conn.close()


# ============================================================
# DEMO STAFF
# ============================================================

def ensure_demo_staff():

    staff_list = [

        # ---------------- BOYS ----------------

        {
            "username": "boys_electrical",
            "password": "staff123",
            "name": "Ravi Kumar",
            "phone": "9876543210",
            "department": "Electrical",
            "hostel_type": "Boys"
        },

        {
            "username": "boys_plumber",
            "password": "staff123",
            "name": "Suresh Kumar",
            "phone": "9876543211",
            "department": "Plumbing",
            "hostel_type": "Boys"
        },

        {
            "username": "boys_cleaning",
            "password": "staff123",
            "name": "Ramesh",
            "phone": "9876543212",
            "department": "Cleaning",
            "hostel_type": "Boys"
        },

        {
            "username": "boys_wifi",
            "password": "staff123",
            "name": "Kiran",
            "phone": "9876543213",
            "department": "Wi-Fi/Network",
            "hostel_type": "Boys"
        },

        {
            "username": "boys_washroom",
            "password": "staff123",
            "name": "Boys Washroom Maintenance",
            "phone": "9876543214",
            "department": "Washroom Maintenance",
            "hostel_type": "Boys"
        },
        {
            "username": "boys_mess",
            "password": "staff123",
            "name": "Boys Mess Staff",
            "phone": "9876543215",
            "department": "Mess / Food",
            "hostel_type": "Boys"
        },
        {
            "username": "boys_water",
            "password": "staff123",
            "name": "Boys Water Supply",
            "phone": "9876543216",
            "department": "Water Supply",
            "hostel_type": "Boys"
        },
        {
            "username": "boys_roommaintenance",
            "password": "staff123",
            "name": "Boys Room Maintenance",
            "phone": "9876543217",
            "department": "Room Maintenance",
            "hostel_type": "Boys"
        },

        # ---------------- GIRLS ----------------

        {
            "username": "girls_electrical",
            "password": "staff123",
            "name": "Priya",
            "phone": "9876543220",
            "department": "Electrical",
            "hostel_type": "Girls"
        },

        {
            "username": "girls_plumber",
            "password": "staff123",
            "name": "Anitha",
            "phone": "9876543221",
            "department": "Plumbing",
            "hostel_type": "Girls"
        },

        {
            "username": "girls_cleaning",
            "password": "staff123",
            "name": "Lakshmi",
            "phone": "9876543222",
            "department": "Cleaning",
            "hostel_type": "Girls"
        },

        {
            "username": "girls_wifi",
            "password": "staff123",
            "name": "Swathi",
            "phone": "9876543223",
            "department": "Wi-Fi/Network",
            "hostel_type": "Girls"
        },
        {
            "username": "girls_washroom",
            "password": "staff123",
            "name": "Girls Washroom Maintenance",
            "phone": "9876543224",
            "department": "Washroom Maintenance",
            "hostel_type": "Girls"
        },
        {
            "username": "girls_mess",
            "password": "staff123",
            "name": "Girls Mess Staff",
            "phone": "9876543225",
            "department": "Mess / Food",
            "hostel_type": "Girls"
        },
        {
            "username": "girls_water",
            "password": "staff123",
            "name": "Girls Water Supply",
            "phone": "9876543226",
            "department": "Water Supply",
            "hostel_type": "Girls"
        },
        {
            "username": "girls_roommaintenance",
            "password": "staff123",
            "name": "Girls Room Maintenance",
            "phone": "9876543227",
            "department": "Room Maintenance",
            "hostel_type": "Girls"
        }
    ]

    conn = get_db()

    for person in staff_list:

        # Find user by username
        user = conn.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, (
            person["username"],
        )).fetchone()

        # Create user if missing
        if not user:

            password_hash = generate_password_hash(
                person["password"]
            )

            try:

                cursor = conn.execute("""
                    INSERT INTO users (
                        roll_number,
                        username,
                        password,
                        name,
                        role,
                        hostel_type
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    None,
                    person["username"],
                    password_hash,
                    person["name"],
                    "staff",
                    person["hostel_type"]
                ))

                user_id = cursor.lastrowid

            except sqlite3.IntegrityError:

                user = conn.execute("""
                    SELECT id
                    FROM users
                    WHERE username = ?
                """, (
                    person["username"],
                )).fetchone()

                if not user:
                    continue

                user_id = user["id"]

        else:

            user_id = user["id"]

            # Make sure staff user has correct role/hostel
            conn.execute("""
                UPDATE users
                SET role = 'staff',
                    hostel_type = ?,
                    name = ?
                WHERE id = ?
            """, (
                person["hostel_type"],
                person["name"],
                user_id
            ))

        # Check staff table
        existing_staff = conn.execute("""
            SELECT id
            FROM staff
            WHERE user_id = ?
        """, (
            user_id,
        )).fetchone()

        if existing_staff:

            # Update existing staff
            conn.execute("""
                UPDATE staff
                SET name = ?,
                    phone = ?,
                    department = ?,
                    hostel_type = ?
                WHERE user_id = ?
            """, (
                person["name"],
                person["phone"],
                person["department"],
                person["hostel_type"],
                user_id
            ))

        else:

            conn.execute("""
                INSERT INTO staff (
                    user_id,
                    name,
                    phone,
                    department,
                    hostel_type
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                user_id,
                person["name"],
                person["phone"],
                person["department"],
                person["hostel_type"]
            ))

    conn.commit()
    conn.close()


# ============================================================
# NOTIFICATION HELPERS
# ============================================================

def create_notification(conn, user_id, message, complaint_id=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        INSERT INTO notifications (user_id, complaint_id, message, is_read, created_at)
        VALUES (?, ?, ?, 0, ?)
    """, (user_id, complaint_id, message, now))


def create_hostel_warden_notifications(conn, hostel_type, message, complaint_id=None):
    wardens = conn.execute("""
        SELECT id FROM users
        WHERE role = 'warden' AND hostel_type = ?
    """, (hostel_type,)).fetchall()
    for warden in wardens:
        create_notification(conn, warden["id"], message, complaint_id)


@app.context_processor
def inject_notifications():
    if "user_id" not in session:
        return {"nav_notifications": [], "nav_unread_count": 0}

    try:
        conn = get_db()
        nav_notifications = conn.execute("""
            SELECT n.*, c.complaint_id AS complaint_code
            FROM notifications n
            LEFT JOIN complaints c ON n.complaint_id = c.id
            WHERE n.user_id = ?
            ORDER BY n.id DESC
            LIMIT 5
        """, (session["user_id"],)).fetchall()
        nav_unread_count = conn.execute("""
            SELECT COUNT(*) AS count
            FROM notifications
            WHERE user_id = ? AND is_read = 0
        """, (session["user_id"],)).fetchone()["count"]
        conn.close()
        return {"nav_notifications": nav_notifications, "nav_unread_count": nav_unread_count}
    except sqlite3.Error:
        return {"nav_notifications": [], "nav_unread_count": 0}


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def current_user():

    if "user_id" not in session:
        return None

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    conn.close()

    return user


def login_required():

    return "user_id" in session


def role_required(*roles):

    if "user_id" not in session:
        return False

    return session.get("role") in roles


# ============================================================
# HOME
# ============================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        identifier = request.form.get(
            "identifier",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not identifier or not password:

            flash(
                "Please enter username/roll number and password.",
                "error"
            )

            return redirect(
                url_for("login")
            )

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE username = ?
               OR roll_number = ?
            LIMIT 1
        """, (
            identifier,
            identifier
        )).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            if user["role"] in ("warden", "staff") and user["account_status"] != "approved":
                flash("Your account is awaiting admin approval.", "error")
                return redirect(url_for("login"))

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            session["hostel_type"] = user["hostel_type"]

            flash(
                f"Welcome, {user['name']}!",
                "success"
            )

            if user["role"] == "student":
                return redirect(
                    url_for("student_dashboard")
                )

            if user["role"] == "warden":
                return redirect(
                    url_for("warden_dashboard")
                )

            if user["role"] == "staff":
                return redirect(
                    url_for("staff_dashboard")
                )

            if user["role"] == "admin":
                return redirect(
                    url_for("admin_dashboard")
                )

        flash(
            "Invalid username/roll number or password.",
            "error"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# REGISTER STUDENT
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        roll_number = request.form.get(
            "roll_number",
            ""
        ).strip().upper()

        hostel_type = request.form.get(
            "hostel_type",
            ""
        ).strip().title()
        email = request.form.get("email", "").strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        # ----------------------------------------
        # REQUIRED FIELDS
        # ----------------------------------------

        if not name:
            flash(
                "Please enter your name.",
                "error"
            )
            return redirect(
                url_for("register")
            )

        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email address for password recovery.", "error")
            return redirect(url_for("register"))

        # ----------------------------------------
        # ROLL NUMBER
        # ----------------------------------------

        roll_pattern = (
            r"^(?=.*[A-Za-z])"
            r"(?=.*[0-9])"
            r"[A-Za-z0-9]{5,15}$"
        )

        if not re.match(
            roll_pattern,
            roll_number
        ):

            flash(
                "Invalid roll number. Use 5-15 letters and numbers only.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # ----------------------------------------
        # HOSTEL
        # ----------------------------------------

        if hostel_type not in [
            "Boys",
            "Girls"
        ]:

            flash(
                "Invalid hostel selection. Please select Boys Hostel or Girls Hostel.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # ----------------------------------------
        # PASSWORD
        # ----------------------------------------

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        conn = get_db()

        # ----------------------------------------
        # CHECK ROLL NUMBER
        # ----------------------------------------

        existing_roll = conn.execute("""
            SELECT id
            FROM users
            WHERE roll_number = ?
        """, (
            roll_number,
        )).fetchone()

        if existing_roll:

            conn.close()

            flash(
                "This roll number is already registered.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        # Username = roll number
        username = roll_number

        existing_username = conn.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, (
            username,
        )).fetchone()

        if existing_username:

            conn.close()

            flash(
                "This username already exists.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        password_hash = generate_password_hash(
            password
        )

        try:

            conn.execute("""
                INSERT INTO users (
                    roll_number,
                    username,
                    password,
                    name,
                    role,
                    hostel_type,
                    email,
                    room_preference
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                roll_number,
                username,
                password_hash,
                name,
                "student",
                hostel_type,
                email,
                request.form.get("room_preference", "").strip()
            ))

            conn.commit()
            conn.close()

        except sqlite3.IntegrityError:

            conn.rollback()
            conn.close()

            flash(
                "Registration failed. Roll number or username already exists.",
                "error"
            )

            return redirect(
                url_for("register")
            )

        flash(
            "Registration successful! Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# WARDEN AND STAFF SELF-REGISTRATION (ADMIN APPROVAL REQUIRED)
# ============================================================

@app.route("/register/warden", methods=["GET", "POST"])
def register_warden():
    return register_employee("warden")


@app.route("/register/staff", methods=["GET", "POST"])
def register_staff():
    return register_employee("staff")


def register_employee(role):
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        username = request.form.get("username", "").strip().lower()
        hostel_type = request.form.get("hostel_type", "").strip().title()
        department = request.form.get("department", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not username or not password or not email:
            flash("Please complete all required fields, including email.", "error")
            return redirect(url_for("register_warden" if role == "warden" else "register_staff"))
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Please enter a valid email address for password recovery.", "error")
            return redirect(url_for("register_warden" if role == "warden" else "register_staff"))
        if not re.fullmatch(r"[a-zA-Z0-9_.-]{4,30}", username):
            flash("Username must be 4-30 characters (letters, numbers, dot, underscore or hyphen).", "error")
            return redirect(url_for("register_warden" if role == "warden" else "register_staff"))
        if hostel_type not in ("Boys", "Girls"):
            flash("Please select Boys or Girls Hostel.", "error")
            return redirect(url_for("register_warden" if role == "warden" else "register_staff"))
        if role == "staff" and department not in ("Electrical", "Plumbing", "Cleaning", "Wi-Fi / Network"):
            flash("Please select a valid department.", "error")
            return redirect(url_for("register_staff"))
        if len(password) < 6 or password != confirm_password:
            flash("Passwords must match and contain at least 6 characters.", "error")
            return redirect(url_for("register_warden" if role == "warden" else "register_staff"))

        conn = get_db()
        if conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone():
            conn.close()
            flash("That username is already taken.", "error")
            return redirect(url_for("register_warden" if role == "warden" else "register_staff"))
        try:
            cur = conn.execute("""INSERT INTO users
                (roll_number, username, password, name, role, hostel_type, email, account_status)
                VALUES (NULL, ?, ?, ?, ?, ?, ?, 'pending')""",
                (username, generate_password_hash(password), name, role, hostel_type, email))
            user_id = cur.lastrowid
            if role == "staff":
                conn.execute("""INSERT INTO staff (user_id, name, phone, department, hostel_type)
                    VALUES (?, ?, ?, ?, ?)""", (user_id, name, phone, department, hostel_type))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.rollback()
            conn.close()
            flash("Registration could not be completed. Please try another username.", "error")
            return redirect(url_for("register_warden" if role == "warden" else "register_staff"))
        conn.close()
        flash("Registration submitted. You can log in after an admin approves your account.", "success")
        return redirect(url_for("login"))
    return render_template("register_employee.html", role=role)


@app.route("/admin/registrations")
def admin_registrations():
    if not role_required("admin"):
        return redirect(url_for("login"))
    conn = get_db()
    pending = conn.execute("SELECT id, name, username, role, hostel_type FROM users WHERE role IN ('warden','staff') AND account_status='pending' ORDER BY id").fetchall()
    conn.close()
    return render_template("admin/registrations.html", pending=pending)


@app.route("/admin/registrations/<int:user_id>/<action>", methods=["POST"])
def admin_registration_action(user_id, action):
    if not role_required("admin"):
        return redirect(url_for("login"))
    if action not in ("approve", "reject"):
        flash("Invalid action.", "error")
        return redirect(url_for("admin_registrations"))
    conn = get_db()
    user = conn.execute("SELECT id, role FROM users WHERE id=? AND role IN ('warden','staff') AND account_status='pending'", (user_id,)).fetchone()
    if not user:
        conn.close()
        flash("Pending registration not found.", "error")
        return redirect(url_for("admin_registrations"))
    if action == "approve":
        conn.execute("UPDATE users SET account_status='approved' WHERE id=?", (user_id,))
        flash("Account approved.", "success")
    else:
        conn.execute("DELETE FROM staff WHERE user_id=?", (user_id,))
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        flash("Registration rejected and removed.", "success")
    conn.commit()
    conn.close()
    return redirect(url_for("admin_registrations"))


# ============================================================
# FORGOT PASSWORD / EMAIL RESET LINK
# Configure SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
# MAIL_FROM and APP_BASE_URL in the deployment environment.
# ============================================================
def password_reset_serializer():
    return URLSafeTimedSerializer(app.secret_key, salt="smart-hostel-password-reset")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Reset a password directly without sending an email."""
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not identifier or not email or not password or not confirm:
            flash("Please fill in all fields.", "error")
            return render_template("forgot_password.html")

        if len(password) < 8:
            flash("New password must contain at least 8 characters.", "error")
            return render_template("forgot_password.html")

        if password != confirm:
            flash("New password and confirm password do not match.", "error")
            return render_template("forgot_password.html")

        conn = get_db()
        user = conn.execute(
            """SELECT id FROM users
               WHERE (lower(username)=lower(?) OR lower(COALESCE(roll_number, ''))=lower(?))
               AND lower(COALESCE(email, ''))=?
               LIMIT 1""",
            (identifier, identifier, email)
        ).fetchone()

        if not user:
            conn.close()
            flash("Username/Roll Number and registered email do not match.", "error")
            return render_template("forgot_password.html")

        conn.execute(
            "UPDATE users SET password=? WHERE id=?",
            (generate_password_hash(password), user["id"])
        )
        conn.commit()
        conn.close()
        flash("Password updated successfully. Please log in with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    try:
        data = password_reset_serializer().loads(token, max_age=1800)
    except SignatureExpired:
        flash("This reset link has expired. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))
    except BadSignature:
        flash("Invalid password reset link. Please request a new one.", "error")
        return redirect(url_for("forgot_password"))
    conn = get_db()
    user = conn.execute("SELECT id, email FROM users WHERE id=? AND lower(email)=?", (data.get("user_id"), data.get("email", "").lower())).fetchone()
    conn.close()
    if not user:
        flash("Account not found. Please request a new reset link.", "error")
        return redirect(url_for("forgot_password"))
    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        else:
            conn = get_db()
            conn.execute("UPDATE users SET password=? WHERE id=?", (generate_password_hash(password), user["id"]))
            conn.commit()
            conn.close()
            flash("Password reset successful. Please log in with your new password.", "success")
            return redirect(url_for("login"))
    return render_template("reset_password.html")


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@app.route("/student/dashboard")
def student_dashboard():

    if not role_required("student"):
        return redirect(url_for("login"))

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    complaints = conn.execute("""
        SELECT *
        FROM complaints
        WHERE student_id = ?
        ORDER BY id DESC
        LIMIT 5
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "student/dashboard.html",
        user=user,
        complaints=complaints
    )


# ============================================================
# STUDENT PROFILE
# ============================================================

@app.route("/student/profile")
def student_profile():

    if not role_required("student"):
        return redirect(url_for("login"))

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    conn.close()

    return render_template(
        "student/profile.html",
        user=user
    )


# ============================================================
# STUDENT RAISE COMPLAINT
# ============================================================

@app.route(
    "/student/raise",
    methods=["GET", "POST"]
)
def raise_complaint():

    if not role_required("student"):
        return redirect(url_for("login"))

    conn = get_db()

    student = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if not student:

        conn.close()
        session.clear()

        flash(
            "Student account not found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    if request.method == "POST":

        room_number = request.form.get(
            "room_number",
            ""
        ).strip()

        category = request.form.get(
            "category",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        # IMPORTANT:
        # Hostel comes directly from registered student account.
        hostel_type = (
            student["hostel_type"] or ""
        ).strip().title()

        # ----------------------------------------
        # HOSTEL VALIDATION
        # ----------------------------------------

        if hostel_type not in [
            "Boys",
            "Girls"
        ]:

            conn.close()

            flash(
                "Invalid hostel selection. Please update your student account.",
                "error"
            )

            return redirect(
                url_for("student_profile")
            )

        # ----------------------------------------
        # ROOM
        # ----------------------------------------

        if not room_number:

            conn.close()

            flash(
                "Please enter room number.",
                "error"
            )

            return redirect(
                url_for("raise_complaint")
            )

        # ----------------------------------------
        # CATEGORY
        # ----------------------------------------

        allowed_categories = [
            "Electrical",
            "Plumbing",
            "Cleaning",
            "Wi-Fi/Network",
            "General Maintenance"
        ]

        if category not in allowed_categories:

            conn.close()

            flash(
                "Please select a valid complaint category.",
                "error"
            )

            return redirect(
                url_for("raise_complaint")
            )

        # ----------------------------------------
        # DESCRIPTION
        # ----------------------------------------

        if not description:

            conn.close()

            flash(
                "Please enter complaint description.",
                "error"
            )

            return redirect(
                url_for("raise_complaint")
            )

        # ----------------------------------------
        # PHOTO
        # ----------------------------------------

        photo_filename = None

        photo = request.files.get(
            "photo"
        )

        if photo and photo.filename:

            if not allowed_file(
                photo.filename
            ):

                conn.close()

                flash(
                    "Invalid photo format.",
                    "error"
                )

                return redirect(
                    url_for("raise_complaint")
                )

            extension = photo.filename.rsplit(
                ".",
                1
            )[1].lower()

            photo_filename = (
                str(uuid.uuid4())
                + "."
                + extension
            )

            safe_name = secure_filename(
                photo_filename
            )

            photo.save(
                os.path.join(
                    COMPLAINT_PHOTO_FOLDER,
                    safe_name
                )
            )

            photo_filename = safe_name

        # ----------------------------------------
        # COMPLAINT ID
        # ----------------------------------------

        now = datetime.now()

        complaint_code = (
            "SH-"
            + now.strftime("%Y%m%d%H%M%S")
            + "-"
            + str(uuid.uuid4())[:4].upper()
        )

        created_at = now.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # ----------------------------------------
        # INSERT
        # ----------------------------------------

        try:

            cursor = conn.execute("""
                INSERT INTO complaints (
                    complaint_id,
                    student_id,
                    hostel_type,
                    room_number,
                    category,
                    description,
                    photo,
                    status,
                    assigned_staff_id,
                    created_at,
                    resolved_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                complaint_code,
                student["id"],
                hostel_type,
                room_number,
                category,
                description,
                photo_filename,
                "Submitted",
                None,
                created_at,
                None
            ))

            complaint_db_id = cursor.lastrowid

            conn.execute("""
                INSERT INTO complaint_updates (
                    complaint_id,
                    status,
                    note,
                    updated_by,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                complaint_db_id,
                "Submitted",
                "Complaint submitted by student.",
                session["user_id"],
                created_at
            ))

            create_hostel_warden_notifications(
                conn,
                hostel_type,
                f"New complaint {complaint_code} received from {student['name']} (Room {room_number}).",
                complaint_db_id
            )

            conn.commit()
            conn.close()

        except sqlite3.Error as e:

            conn.rollback()
            conn.close()

            flash(
                f"Unable to submit complaint: {e}",
                "error"
            )

            return redirect(
                url_for("raise_complaint")
            )

        flash(
            f"Complaint submitted successfully! ID: {complaint_code}",
            "success"
        )

        return redirect(
            url_for(
                "student_complaint_details",
                complaint_id=complaint_db_id
            )
        )

    conn.close()

    return render_template(
        "student/raise_complaint.html",
        user=student
    )


# ============================================================
# STUDENT COMPLAINTS
# ============================================================

@app.route("/student/complaints")
def student_complaints():

    if not role_required("student"):
        return redirect(url_for("login"))

    conn = get_db()

    complaints = conn.execute("""
        SELECT *
        FROM complaints
        WHERE student_id = ?
        ORDER BY id DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "student/my_complaints.html",
        complaints=complaints
    )


# ============================================================
# STUDENT COMPLAINT DETAILS
# ============================================================

@app.route(
    "/student/complaint/<int:complaint_id>"
)
def student_complaint_details(
    complaint_id
):

    if not role_required("student"):
        return redirect(url_for("login"))

    conn = get_db()

    complaint = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number,
            s.name AS staff_name,
            s.department
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        LEFT JOIN staff s
            ON c.assigned_staff_id = s.id
        WHERE c.id = ?
          AND c.student_id = ?
    """, (
        complaint_id,
        session["user_id"]
    )).fetchone()

    if not complaint:

        conn.close()

        flash(
            "Complaint not found.",
            "error"
        )

        return redirect(
            url_for("student_complaints")
        )

    updates = conn.execute("""
        SELECT
            cu.*,
            u.name AS updater_name
        FROM complaint_updates cu
        LEFT JOIN users u
            ON cu.updated_by = u.id
        WHERE cu.complaint_id = ?
        ORDER BY cu.id ASC
    """, (
        complaint_id,
    )).fetchall()

    conn.close()

    return render_template(
        "student/complaint_details.html",
        complaint=complaint,
        updates=updates
    )


# ============================================================
# WARDEN DASHBOARD
# ============================================================

@app.route("/warden/dashboard")
def warden_dashboard():

    if not role_required("warden"):
        return redirect(url_for("login"))

    hostel_type = session.get(
        "hostel_type"
    )

    conn = get_db()

    total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = ?
    """, (
        hostel_type,
    )).fetchone()["count"]

    submitted = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = ?
          AND status = 'Submitted'
    """, (
        hostel_type,
    )).fetchone()["count"]

    in_progress = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = ?
          AND status = 'In Progress'
    """, (
        hostel_type,
    )).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = ?
          AND status = 'Resolved'
    """, (
        hostel_type,
    )).fetchone()["count"]

    recent = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        WHERE c.hostel_type = ?
        ORDER BY c.id DESC
        LIMIT 10
    """, (
        hostel_type,
    )).fetchall()

    conn.close()

    stats = {
        "total": total,
        "submitted": submitted,
        "in_progress": in_progress,
        "resolved": resolved
    }

    return render_template(
        "warden/dashboard.html",
        stats=stats,
        recent=recent,
        hostel_type=hostel_type
    )


# ============================================================
# WARDEN COMPLAINTS
# ============================================================

@app.route("/warden/complaints")
def warden_complaints():

    if not role_required("warden"):
        return redirect(url_for("login"))

    hostel_type = session.get(
        "hostel_type"
    )

    conn = get_db()

    complaints = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        WHERE c.hostel_type = ?
        ORDER BY c.id DESC
    """, (
        hostel_type,
    )).fetchall()

    conn.close()

    return render_template(
        "warden/complaints.html",
        complaints=complaints,
        hostel_type=hostel_type
    )


# ============================================================
# WARDEN COMPLAINT DETAILS
# ============================================================

@app.route(
    "/warden/complaint/<int:complaint_id>"
)
def warden_complaint_details(
    complaint_id
):

    if not role_required("warden"):
        return redirect(url_for("login"))

    hostel_type = session.get(
        "hostel_type"
    )

    conn = get_db()

    complaint = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number,
            s.name AS staff_name,
            s.department
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        LEFT JOIN staff s
            ON c.assigned_staff_id = s.id
        WHERE c.id = ?
          AND c.hostel_type = ?
    """, (
        complaint_id,
        hostel_type
    )).fetchone()

    if not complaint:

        conn.close()

        flash(
            "Complaint not found.",
            "error"
        )

        return redirect(
            url_for("warden_complaints")
        )

    updates = conn.execute("""
        SELECT
            cu.*,
            u.name AS updater_name
        FROM complaint_updates cu
        LEFT JOIN users u
            ON cu.updated_by = u.id
        WHERE cu.complaint_id = ?
        ORDER BY cu.id ASC
    """, (
        complaint_id,
    )).fetchall()

    # THIS IS THE IMPORTANT PART
    # Staff is filtered by the warden's hostel.
    staff = conn.execute("""
        SELECT
            s.id,
            s.name,
            s.phone,
            s.department,
            s.hostel_type,
            u.username
        FROM staff s
        JOIN users u
            ON s.user_id = u.id
        WHERE s.hostel_type = ?
        ORDER BY s.department, s.name
    """, (
        hostel_type,
    )).fetchall()

    conn.close()

    return render_template(
        "warden/complaint_details.html",
        complaint=complaint,
        updates=updates,
        staff=staff
    )


# ============================================================
# ASSIGN STAFF
# ============================================================

@app.route(
    "/warden/complaint/<int:complaint_id>/assign",
    methods=["GET", "POST"]
)
def assign_staff(complaint_id):

    if not role_required("warden"):
        return redirect(url_for("login"))

    hostel_type = session.get(
        "hostel_type"
    )

    conn = get_db()

    complaint = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        WHERE c.id = ?
          AND c.hostel_type = ?
    """, (
        complaint_id,
        hostel_type
    )).fetchone()

    if not complaint:

        conn.close()

        flash(
            "Complaint not found.",
            "error"
        )

        return redirect(
            url_for("warden_complaints")
        )

    staff = conn.execute("""
        SELECT
            s.id,
            s.name,
            s.phone,
            s.department,
            s.hostel_type,
            u.username
        FROM staff s
        JOIN users u
            ON s.user_id = u.id
        WHERE s.hostel_type = ?
        ORDER BY s.department, s.name
    """, (
        hostel_type,
    )).fetchall()

    if request.method == "POST":

        staff_id = request.form.get(
            "staff_id",
            ""
        ).strip()

        note = request.form.get(
            "note",
            ""
        ).strip()

        if not staff_id:

            conn.close()

            flash(
                "Please select maintenance staff.",
                "error"
            )

            return redirect(
                url_for(
                    "assign_staff",
                    complaint_id=complaint_id
                )
            )

        selected_staff = conn.execute("""
            SELECT *
            FROM staff
            WHERE id = ?
              AND hostel_type = ?
        """, (
            staff_id,
            hostel_type
        )).fetchone()

        if not selected_staff:

            conn.close()

            flash(
                "Invalid maintenance staff selection.",
                "error"
            )

            return redirect(
                url_for(
                    "assign_staff",
                    complaint_id=complaint_id
                )
            )

        now = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        try:

            conn.execute("""
                UPDATE complaints
                SET assigned_staff_id = ?,
                    status = 'Assigned'
                WHERE id = ?
            """, (
                staff_id,
                complaint_id
            ))

            history_note = (
                "Assigned to "
                + selected_staff["name"]
                + " ("
                + selected_staff["department"]
                + ")."
            )

            if note:
                history_note += (
                    " Note: "
                    + note
                )

            conn.execute("""
                INSERT INTO complaint_updates (
                    complaint_id,
                    status,
                    note,
                    updated_by,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                complaint_id,
                "Assigned",
                history_note,
                session["user_id"],
                now
            ))

            create_notification(
                conn,
                selected_staff["user_id"],
                f"Complaint {complaint['complaint_id']} has been assigned to you. Please check the complaint details.",
                complaint_id
            )

            conn.commit()
            conn.close()

        except sqlite3.Error as e:

            conn.rollback()
            conn.close()

            flash(
                f"Assignment failed: {e}",
                "error"
            )

            return redirect(
                url_for(
                    "warden_complaint_details",
                    complaint_id=complaint_id
                )
            )

        flash(
            "Maintenance staff assigned successfully!",
            "success"
        )

        return redirect(
            url_for(
                "warden_complaint_details",
                complaint_id=complaint_id
            )
        )

    conn.close()

    return render_template(
        "warden/assign_staff.html",
        complaint=complaint,
        staff=staff
    )


# ============================================================
# STAFF DASHBOARD
# ============================================================

@app.route("/staff/dashboard")
def staff_dashboard():

    if not role_required("staff"):
        return redirect(url_for("login"))

    conn = get_db()

    user = conn.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (
        session["user_id"],
    )).fetchone()

    staff = conn.execute("""
        SELECT *
        FROM staff
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if not staff:

        conn.close()

        flash(
            "Maintenance staff profile not found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    assigned = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE assigned_staff_id = ?
    """, (
        staff["id"],
    )).fetchone()["count"]

    in_progress = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE assigned_staff_id = ?
          AND status = 'In Progress'
    """, (
        staff["id"],
    )).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE assigned_staff_id = ?
          AND status = 'Resolved'
    """, (
        staff["id"],
    )).fetchone()["count"]

    complaints = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        WHERE c.assigned_staff_id = ?
        ORDER BY c.id DESC
        LIMIT 10
    """, (
        staff["id"],
    )).fetchall()

    conn.close()

    stats = {
        "assigned": assigned,
        "in_progress": in_progress,
        "resolved": resolved
    }

    return render_template(
        "staff/dashboard.html",
        user=user,
        staff=staff,
        stats=stats,
        complaints=complaints
    )


# ============================================================
# STAFF ASSIGNED COMPLAINTS
# ============================================================

@app.route("/staff/assigned-complaints")
def staff_assigned_complaints():

    if not role_required("staff"):
        return redirect(url_for("login"))

    conn = get_db()

    staff = conn.execute("""
        SELECT *
        FROM staff
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if not staff:

        conn.close()

        flash(
            "Staff profile not found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    complaints = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        WHERE c.assigned_staff_id = ?
        ORDER BY c.id DESC
    """, (
        staff["id"],
    )).fetchall()

    conn.close()

    return render_template(
        "staff/assigned_complaints.html",
        complaints=complaints,
        staff=staff
    )


# ============================================================
# STAFF COMPLAINT DETAILS
# ============================================================

@app.route(
    "/staff/complaint/<int:complaint_id>"
)
def staff_complaint_details(
    complaint_id
):

    if not role_required("staff"):
        return redirect(url_for("login"))

    conn = get_db()

    staff = conn.execute("""
        SELECT *
        FROM staff
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if not staff:

        conn.close()

        flash(
            "Staff profile not found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    complaint = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        WHERE c.id = ?
          AND c.assigned_staff_id = ?
    """, (
        complaint_id,
        staff["id"]
    )).fetchone()

    if not complaint:

        conn.close()

        flash(
            "Complaint not found or not assigned to you.",
            "error"
        )

        return redirect(
            url_for("staff_assigned_complaints")
        )

    updates = conn.execute("""
        SELECT
            cu.*,
            u.name AS updater_name
        FROM complaint_updates cu
        LEFT JOIN users u
            ON cu.updated_by = u.id
        WHERE cu.complaint_id = ?
        ORDER BY cu.id ASC
    """, (
        complaint_id,
    )).fetchall()

    conn.close()

    return render_template(
        "staff/complaint_details.html",
        complaint=complaint,
        updates=updates,
        staff=staff
    )


# ============================================================
# STAFF UPDATE STATUS
# ============================================================

@app.route(
    "/staff/complaint/<int:complaint_id>/status",
    methods=["POST"]
)
def staff_update_status(
    complaint_id
):

    if not role_required("staff"):
        return redirect(url_for("login"))

    new_status = request.form.get(
        "status",
        ""
    ).strip()

    note = request.form.get(
        "note",
        ""
    ).strip()

    allowed_statuses = [
        "In Progress",
        "Resolved"
    ]

    if new_status not in allowed_statuses:

        flash(
            "Invalid status.",
            "error"
        )

        return redirect(
            url_for(
                "staff_complaint_details",
                complaint_id=complaint_id
            )
        )

    conn = get_db()

    staff = conn.execute("""
        SELECT *
        FROM staff
        WHERE user_id = ?
    """, (
        session["user_id"],
    )).fetchone()

    if not staff:

        conn.close()

        flash(
            "Staff profile not found.",
            "error"
        )

        return redirect(
            url_for("login")
        )

    complaint = conn.execute("""
        SELECT *
        FROM complaints
        WHERE id = ?
          AND assigned_staff_id = ?
    """, (
        complaint_id,
        staff["id"]
    )).fetchone()

    if not complaint:

        conn.close()

        flash(
            "Complaint not found.",
            "error"
        )

        return redirect(
            url_for("staff_assigned_complaints")
        )

    current_status = complaint["status"]

    # ----------------------------------------
    # VALID STATUS FLOW
    # ----------------------------------------

    if current_status == "Assigned":
        valid_transition = (
            new_status == "In Progress"
        )

    elif current_status == "In Progress":
        valid_transition = (
            new_status == "Resolved"
        )

    elif current_status == "Resolved":
        valid_transition = False

    else:
        valid_transition = (
            new_status == "In Progress"
        )

    if not valid_transition:

        conn.close()

        flash(
            f"Invalid status transition: {current_status} → {new_status}",
            "error"
        )

        return redirect(
            url_for(
                "staff_complaint_details",
                complaint_id=complaint_id
            )
        )

    now = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    resolved_at = None
    resolution_photo_filename = None

    # A resolution photo is mandatory when marking a complaint Resolved.
    if new_status == "Resolved":
        resolution_photo = request.files.get("resolution_photo")

        if not resolution_photo or not resolution_photo.filename:
            conn.close()
            flash("Please upload a resolution photo before marking the complaint as Resolved.", "error")
            return redirect(url_for("staff_complaint_details", complaint_id=complaint_id))

        if not allowed_file(resolution_photo.filename):
            conn.close()
            flash("Invalid resolution photo format. Use PNG, JPG, JPEG, GIF or WEBP.", "error")
            return redirect(url_for("staff_complaint_details", complaint_id=complaint_id))

        extension = resolution_photo.filename.rsplit(".", 1)[1].lower()
        resolution_photo_filename = secure_filename(str(uuid.uuid4()) + "." + extension)
        resolution_photo.save(os.path.join(RESOLUTION_PHOTO_FOLDER, resolution_photo_filename))
        resolved_at = now

    try:

        if new_status == "Resolved":
            conn.execute("""
                UPDATE complaints
                SET status = ?,
                    resolved_at = ?,
                    resolution_photo = ?
                WHERE id = ?
            """, (
                new_status,
                resolved_at,
                resolution_photo_filename,
                complaint_id
            ))
        else:
            conn.execute("""
                UPDATE complaints
                SET status = ?,
                    resolved_at = NULL
                WHERE id = ?
            """, (
                new_status,
                complaint_id
            ))

        if note:
            history_note = note
        else:

            if new_status == "In Progress":
                history_note = (
                    "Maintenance work started."
                )
            else:
                history_note = (
                    "Complaint resolved by maintenance staff."
                )

        conn.execute("""
            INSERT INTO complaint_updates (
                complaint_id,
                status,
                note,
                updated_by,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            complaint_id,
            new_status,
            history_note,
            session["user_id"],
            now
        ))

        if new_status == "In Progress":
            message = f"Complaint {complaint['complaint_id']} is now In Progress. Maintenance work has started."
        else:
            message = f"Complaint {complaint['complaint_id']} has been Resolved. You can now view the resolution photo and submit a 1–5 feedback rating."

        create_notification(
            conn,
            complaint["student_id"],
            message,
            complaint_id
        )

        conn.commit()
        conn.close()

    except sqlite3.Error as e:

        conn.rollback()
        conn.close()

        flash(
            f"Unable to update complaint: {e}",
            "error"
        )

        return redirect(
            url_for(
                "staff_complaint_details",
                complaint_id=complaint_id
            )
        )

    flash(
        f"Complaint status updated to {new_status}.",
        "success"
    )

    return redirect(
        url_for(
            "staff_complaint_details",
            complaint_id=complaint_id
        )
    )


# ============================================================
# NOTIFICATIONS
# ============================================================

@app.route("/notifications")
def notifications():
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    items = conn.execute("""
        SELECT n.*, c.complaint_id AS complaint_code
        FROM notifications n
        LEFT JOIN complaints c ON n.complaint_id = c.id
        WHERE n.user_id = ?
        ORDER BY n.id DESC
    """, (session["user_id"],)).fetchall()

    conn.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE user_id = ?
    """, (session["user_id"],))
    conn.commit()
    conn.close()

    return render_template("notifications.html", notifications=items)


@app.route("/notifications/read/<int:notification_id>")
def read_notification(notification_id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    notification = conn.execute("""
        SELECT * FROM notifications
        WHERE id = ? AND user_id = ?
    """, (notification_id, session["user_id"])).fetchone()

    if not notification:
        conn.close()
        flash("Notification not found.", "error")
        return redirect(url_for("notifications"))

    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ?", (notification_id,))
    conn.commit()
    conn.close()

    if notification["complaint_id"]:
        if session.get("role") == "student":
            return redirect(url_for("student_complaint_details", complaint_id=notification["complaint_id"]))
        if session.get("role") == "warden":
            return redirect(url_for("warden_complaint_details", complaint_id=notification["complaint_id"]))
        if session.get("role") == "staff":
            return redirect(url_for("staff_complaint_details", complaint_id=notification["complaint_id"]))
        if session.get("role") == "admin":
            return redirect(url_for("admin_complaints"))

    return redirect(url_for("notifications"))


# ============================================================
# STUDENT FEEDBACK
# ============================================================

@app.route("/student/complaint/<int:complaint_id>/feedback", methods=["POST"])
def submit_feedback(complaint_id):
    if not role_required("student"):
        return redirect(url_for("login"))

    rating_raw = request.form.get("rating", "").strip()
    comment = request.form.get("feedback_comment", "").strip()

    try:
        rating = int(rating_raw)
    except (TypeError, ValueError):
        rating = 0

    if rating not in range(1, 6):
        flash("Please select a feedback rating from 1 to 5.", "error")
        return redirect(url_for("student_complaint_details", complaint_id=complaint_id))

    conn = get_db()
    complaint = conn.execute("""
        SELECT * FROM complaints
        WHERE id = ? AND student_id = ?
    """, (complaint_id, session["user_id"])).fetchone()

    if not complaint:
        conn.close()
        flash("Complaint not found.", "error")
        return redirect(url_for("student_complaints"))

    if complaint["status"] != "Resolved":
        conn.close()
        flash("Feedback is available only after the complaint is resolved.", "error")
        return redirect(url_for("student_complaint_details", complaint_id=complaint_id))

    if complaint["feedback_rating"] is not None:
        conn.close()
        flash("Feedback has already been submitted for this complaint.", "warning")
        return redirect(url_for("student_complaint_details", complaint_id=complaint_id))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("""
        UPDATE complaints
        SET feedback_rating = ?,
            feedback_comment = ?,
            feedback_at = ?
        WHERE id = ? AND student_id = ?
    """, (rating, comment, now, complaint_id, session["user_id"]))

    # Notify the assigned maintenance staff and all admins about the feedback.
    if complaint["assigned_staff_id"]:
        staff_user = conn.execute("""
            SELECT user_id FROM staff WHERE id = ?
        """, (complaint["assigned_staff_id"],)).fetchone()

        if staff_user:
            create_notification(
                conn,
                staff_user["user_id"],
                f"Student submitted {rating}/5 feedback for complaint {complaint['complaint_id']}.",
                complaint_id
            )

    admin_users = conn.execute("""
        SELECT id FROM users WHERE role = 'admin'
    """).fetchall()

    for admin in admin_users:
        create_notification(
            conn,
            admin["id"],
            f"New {rating}/5 student feedback received for complaint {complaint['complaint_id']}.",
            complaint_id
        )

    conn.commit()
    conn.close()

    flash("Thank you! Your feedback has been submitted successfully.", "success")
    return redirect(url_for("student_complaint_details", complaint_id=complaint_id))


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not role_required("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
    """).fetchone()["count"]

    submitted = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE status = 'Submitted'
    """).fetchone()["count"]

    in_progress = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE status = 'In Progress'
    """).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE status = 'Resolved'
    """).fetchone()["count"]

    boys_total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Boys'
    """).fetchone()["count"]

    boys_resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Boys'
          AND status = 'Resolved'
    """).fetchone()["count"]

    girls_total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Girls'
    """).fetchone()["count"]

    girls_resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Girls'
          AND status = 'Resolved'
    """).fetchone()["count"]

    recent = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        ORDER BY c.id DESC
        LIMIT 10
    """).fetchall()

    conn.close()

    stats = {
        "total": total,
        "submitted": submitted,
        "in_progress": in_progress,
        "resolved": resolved
    }

    boys_stats = {
        "total": boys_total,
        "pending": boys_total - boys_resolved,
        "resolved": boys_resolved
    }

    girls_stats = {
        "total": girls_total,
        "pending": girls_total - girls_resolved,
        "resolved": girls_resolved
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        boys_stats=boys_stats,
        girls_stats=girls_stats,
        recent=recent
    )


# ============================================================
# ADMIN COMPLAINTS
# ============================================================

@app.route("/admin/complaints")
def admin_complaints():

    if not role_required("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    complaints = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        ORDER BY c.id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin/complaints.html",
        complaints=complaints
    )


# ============================================================
# ADMIN REPORTS
# ============================================================

@app.route("/admin/reports")
def admin_reports():

    if not role_required("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
    """).fetchone()["count"]

    submitted = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE status = 'Submitted'
    """).fetchone()["count"]

    in_progress = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE status = 'In Progress'
    """).fetchone()["count"]

    resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE status = 'Resolved'
    """).fetchone()["count"]

    # Boys
    boys_total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Boys'
    """).fetchone()["count"]

    boys_resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Boys'
          AND status = 'Resolved'
    """).fetchone()["count"]

    # Girls
    girls_total = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Girls'
    """).fetchone()["count"]

    girls_resolved = conn.execute("""
        SELECT COUNT(*) AS count
        FROM complaints
        WHERE hostel_type = 'Girls'
          AND status = 'Resolved'
    """).fetchone()["count"]

    # Category statistics
    category_stats = conn.execute("""
        SELECT
            category,
            COUNT(*) AS count
        FROM complaints
        GROUP BY category
        ORDER BY count DESC
    """).fetchall()

    complaints = conn.execute("""
        SELECT
            c.*,
            u.name AS student_name,
            u.roll_number
        FROM complaints c
        JOIN users u
            ON c.student_id = u.id
        ORDER BY c.id DESC
    """).fetchall()

    conn.close()

    stats = {
        "total": total,
        "submitted": submitted,
        "in_progress": in_progress,
        "resolved": resolved
    }

    boys_stats = {
        "total": boys_total,
        "pending": boys_total - boys_resolved,
        "resolved": boys_resolved
    }

    girls_stats = {
        "total": girls_total,
        "pending": girls_total - girls_resolved,
        "resolved": girls_resolved
    }

    return render_template(
        "admin/reports.html",
        stats=stats,
        boys_stats=boys_stats,
        girls_stats=girls_stats,
        category_stats=category_stats,
        complaints=complaints
    )


# ============================================================
# ADMIN STAFF
# ============================================================

@app.route("/admin/staff")
def admin_staff():

    if not role_required("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    staff = conn.execute("""
        SELECT
            s.id,
            s.name,
            s.phone,
            s.department,
            s.hostel_type,
            u.username
        FROM staff s
        LEFT JOIN users u
            ON s.user_id = u.id
        ORDER BY s.hostel_type, s.department, s.name
    """).fetchall()

    total = len(staff)

    boys_count = sum(
        1
        for person in staff
        if person["hostel_type"] == "Boys"
    )

    girls_count = sum(
        1
        for person in staff
        if person["hostel_type"] == "Girls"
    )

    departments = len(
        set(
            person["department"]
            for person in staff
            if person["department"]
        )
    )

    conn.close()

    stats = {
        "total": total,
        "boys": boys_count,
        "girls": girls_count,
        "departments": departments
    }

    return render_template(
        "admin/staff.html",
        staff=staff,
        stats=stats
    )


# ============================================================
# ADMIN WARDENS
# ============================================================

@app.route("/admin/wardens")
def admin_wardens():

    if not role_required("admin"):
        return redirect(url_for("login"))

    conn = get_db()

    wardens = conn.execute("""
        SELECT
            id,
            name,
            username,
            hostel_type
        FROM users
        WHERE role = 'warden'
        ORDER BY hostel_type
    """).fetchall()

    total = len(wardens)

    boys = sum(
        1
        for warden in wardens
        if warden["hostel_type"] == "Boys"
    )

    girls = sum(
        1
        for warden in wardens
        if warden["hostel_type"] == "Girls"
    )

    conn.close()

    stats = {
        "total": total,
        "boys": boys,
        "girls": girls
    }

    return render_template(
        "admin/wardens.html",
        wardens=wardens,
        stats=stats
    )


# ============================================================
# SERVE COMPLAINT PHOTOS
# ============================================================

@app.route(
    "/complaint-photo/<filename>"
)
def complaint_photo(filename):

    return send_from_directory(
        COMPLAINT_PHOTO_FOLDER,
        filename
    )


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "Photo is too large. Maximum size is 5 MB.",
        "error"
    )

    return redirect(
        url_for("raise_complaint")
    )



# ============================================================
# GEC HOSTEL ROOM AND FEE MANAGEMENT (additive feature)
# ============================================================

@app.route("/hostel-fee-balance")
def hostel_fee_balance():
    if not role_required("admin", "warden"):
        return jsonify({"error": "Please log in as admin or warden"}), 403

    student_id = request.args.get("student_id", type=int)
    semester = request.args.get("semester", "").strip()

    valid_semesters = [
        f"{n}{suffix} Semester"
        for n, suffix in [
            (1, "st"), (2, "nd"), (3, "rd"), (4, "th"),
            (5, "th"), (6, "th"), (7, "th"), (8, "th")
        ]
    ]

    if not student_id or semester not in valid_semesters:
        return jsonify({"error": "Select a student and semester"}), 400

    conn = get_db()

    try:
        role = session.get("role")
        own_hostel = session.get("hostel_type") if role == "warden" else None

        student = conn.execute(
            """
            SELECT id, hostel_type
            FROM users
            WHERE id = ? AND role = 'student'
            """,
            (student_id,)
        ).fetchone()

        if not student:
            return jsonify({"error": "Student not found"}), 404

        if own_hostel and student["hostel_type"] != own_hostel:
            return jsonify({"error": "Student is not in your hostel"}), 403

        # Find the latest fee record for this student and semester.
        fee = conn.execute(
            """
            SELECT *
            FROM hostel_fee_payments
            WHERE student_id = ? AND semester = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (student_id, semester)
        ).fetchone()

        if fee:
            total_fee = float(fee["amount_due"])
            total_paid = float(fee["amount_paid"])
            balance = max(0, round(total_fee - total_paid, 2))

            return jsonify({
                "total_fee": total_fee,
                "total_paid": total_paid,
                "balance": balance,
                "room_id": fee["room_id"]
            })

        # If no fee record exists, find the room allocation.
        allocation = conn.execute(
            """
            SELECT r.id AS room_id, r.semester_rent
            FROM room_allocations a
            JOIN hostel_rooms r ON r.id = a.room_id
            WHERE a.student_id = ?
              AND a.semester = ?
              AND a.status = 'Active'
            LIMIT 1
            """,
            (student_id, semester)
        ).fetchone()

        if allocation:
            total_fee = float(allocation["semester_rent"])

            return jsonify({
                "total_fee": total_fee,
                "total_paid": 0,
                "balance": total_fee,
                "room_id": allocation["room_id"]
            })

        return jsonify({
            "total_fee": 0,
            "total_paid": 0,
            "balance": 0,
            "room_id": None,
            "message": "No fee record or active room allocation found for this semester."
        })

    finally:
        conn.close()
@app.route("/hostel-management", methods=["GET", "POST"])
def hostel_management():
    if not role_required("admin", "warden"):
        flash("Please log in as an admin or warden to manage hostel rooms and fees.", "error")
        return redirect(url_for("login"))

    role = session.get("role")
    own_hostel = session.get("hostel_type") if role == "warden" else None
    conn = get_db()

    if request.method == "POST":
        action = request.form.get("action", "")
        hostel_type = (own_hostel or request.form.get("hostel_type", "")).strip().title()
        if hostel_type not in ("Boys", "Girls"):
            flash("Please select a valid hostel.", "error")
            conn.close()
            return redirect(url_for("hostel_management"))

        try:
            if action == "add_floor":
                floor_number = int(request.form.get("floor_number", "0"))
                if floor_number < 1 or floor_number > 100:
                    raise ValueError("Floor number must be between 1 and 100.")
                conn.execute("""INSERT INTO hostel_floors(hostel_type,floor_number,created_by,created_at)
                                VALUES(?,?,?,?)""",
                             (hostel_type, floor_number, session["user_id"], datetime.now().isoformat(timespec="seconds")))
                conn.commit()
                flash(f"Floor {floor_number} added to {hostel_type} Hostel.", "success")

            elif action == "add_room":
                floor_id = int(request.form.get("floor_id", "0"))
                room_number = request.form.get("room_number", "").strip()
                room_type = request.form.get("room_type", "")
                capacity = int(request.form.get("capacity", "0"))
                if not room_number or len(room_number) > 20:
                    raise ValueError("Enter a valid room number (for example, 101).")
                if room_type not in ("Attached", "Non-Attached"):
                    raise ValueError("Select a valid room type.")
                if capacity < 1 or capacity > 20:
                    raise ValueError("Room capacity must be between 1 and 20.")
                floor = conn.execute("SELECT * FROM hostel_floors WHERE id=? AND hostel_type=?", (floor_id, hostel_type)).fetchone()
                if not floor:
                    raise ValueError("Select a floor belonging to this hostel.")
                rent = 18000 if room_type == "Attached" else 16000
                conn.execute("""INSERT INTO hostel_rooms(hostel_type,floor_id,room_number,room_type,capacity,semester_rent,created_by,created_at)
                                VALUES(?,?,?,?,?,?,?,?)""",
                             (hostel_type, floor_id, room_number, room_type, capacity, rent, session["user_id"], datetime.now().isoformat(timespec="seconds")))
                conn.commit()
                flash(f"Room {room_number} added successfully.", "success")

            elif action == "allocate":
                if role != "warden":
                    raise ValueError("Only wardens can allocate rooms.")
                student_id = int(request.form.get("student_id", "0"))
                room_id = int(request.form.get("room_id", "0"))
                student = conn.execute("SELECT * FROM users WHERE id=? AND role='student' AND hostel_type=?", (student_id, own_hostel)).fetchone()
                room = conn.execute("SELECT * FROM hostel_rooms WHERE id=? AND hostel_type=? AND is_active=1", (room_id, own_hostel)).fetchone()
                if not student or not room:
                    raise ValueError("Choose a registered student and a room in your hostel.")
                existing = conn.execute("SELECT id FROM room_allocations WHERE student_id=? AND status='Active'", (student_id,)).fetchone()
                occupied = conn.execute("SELECT COUNT(*) AS n FROM room_allocations WHERE room_id=? AND status='Active'", (room_id,)).fetchone()["n"]
                if existing:
                    raise ValueError("This student already has an active room allocation.")
                if occupied >= room["capacity"]:
                    raise ValueError("This room is full. Select a room with available beds.")
                semester = request.form.get("semester", "1st Semester").strip()
                if semester not in [f"{n}{suffix} Semester" for n, suffix in [(1,"st"),(2,"nd"),(3,"rd"),(4,"th"),(5,"th"),(6,"th"),(7,"th"),(8,"th")]]:
                    raise ValueError("Select a valid semester (1st to 8th).")
                conn.execute("INSERT INTO room_allocations(student_id,room_id,allocated_by,allocated_at,status,semester) VALUES(?,?,?,?, 'Active', ?)",
                             (student_id, room_id, session["user_id"], datetime.now().isoformat(timespec="seconds"), semester))
                conn.execute("UPDATE users SET room_number=?, room_type=? WHERE id=?", (room["room_number"], room["room_type"], student_id))
                conn.commit()
                flash(f"Room {room['room_number']} allocated to {student['name']} for {semester}.", "success")

            elif action == "change_room":
                if role != "warden":
                    raise ValueError("Only wardens can update room allocations.")
                student_id = int(request.form.get("student_id", "0"))
                room_id = int(request.form.get("room_id", "0"))
                semester = request.form.get("semester", "").strip()
                valid_semesters = [f"{n}{suffix} Semester" for n, suffix in [(1,"st"),(2,"nd"),(3,"rd"),(4,"th"),(5,"th"),(6,"th"),(7,"th"),(8,"th")]]
                if semester not in valid_semesters:
                    raise ValueError("Select a valid semester (1st to 8th).")
                student = conn.execute("SELECT * FROM users WHERE id=? AND role='student' AND hostel_type=?", (student_id, own_hostel)).fetchone()
                room = conn.execute("SELECT * FROM hostel_rooms WHERE id=? AND hostel_type=? AND is_active=1", (room_id, own_hostel)).fetchone()
                current = conn.execute("SELECT * FROM room_allocations WHERE student_id=? AND status='Active'", (student_id,)).fetchone()
                if not student or not room:
                    raise ValueError("Choose a registered student and a room in your hostel.")
                if current and current["room_id"] == room_id and current["semester"] == semester:
                    raise ValueError("Student is already allocated to this room for this semester.")
                occupied = conn.execute("SELECT COUNT(*) AS n FROM room_allocations WHERE room_id=? AND status='Active' AND student_id<>?", (room_id, student_id)).fetchone()["n"]
                if occupied >= room["capacity"]:
                    raise ValueError("This room is full. Select a room with available beds.")
                if current:
                    conn.execute("UPDATE room_allocations SET status='Completed', vacated_at=? WHERE id=?", (datetime.now().isoformat(timespec="seconds"), current["id"]))
                conn.execute("INSERT INTO room_allocations(student_id,room_id,allocated_by,allocated_at,status,semester) VALUES(?,?,?,?, 'Active', ?)",
                             (student_id, room_id, session["user_id"], datetime.now().isoformat(timespec="seconds"), semester))
                conn.execute("UPDATE users SET room_number=?, room_type=? WHERE id=?", (room["room_number"], room["room_type"], student_id))
                conn.commit()
                flash(f"Room updated to {room['room_number']} for {semester}; previous allocation remains in history.", "success")

            elif action == "record_hostel_payment":
                if request.form.get("payment_method", "Offline") != "Offline":
                    raise ValueError("Wardens can record offline payments only. Online payments are recorded automatically by the student portal.")
                student_id = int(request.form.get("student_id", "0"))
                room_id_text = request.form.get("room_id", "").strip()
                room_id = int(room_id_text) if room_id_text else None
                semester = request.form.get("semester", "").strip() or "1st Semester"
                if semester not in [f"{n}{suffix} Semester" for n, suffix in [(1,"st"),(2,"nd"),(3,"rd"),(4,"th"),(5,"th"),(6,"th"),(7,"th"),(8,"th")]]:
                    raise ValueError("Select a valid semester (1st to 8th).")
                amount_due = float(request.form.get("amount_due", "0"))
                amount_paid = float(request.form.get("amount_paid", "0"))

                # Validate fee amounts
                if amount_due <= 0:
                    raise ValueError("Outstanding balance must be greater than zero.")

                if amount_paid <= 0:
                    raise ValueError("Amount paid must be greater than zero.")

                if amount_paid > amount_due:
                    raise ValueError(
                        "Amount paid cannot exceed the outstanding balance."
                    )

                student = conn.execute(
                    """
                    SELECT id
                    FROM users
                    WHERE id = ?
                      AND role = 'student'
                      AND (? IS NULL OR hostel_type = ?)
                    """,
                    (student_id, own_hostel, own_hostel)
                ).fetchone()

                if not student:
                    raise ValueError("Select a valid student.")

                # Save the current installment payment
                conn.execute(
                    """
                    INSERT INTO hostel_fee_payments
                    (
                        student_id,
                        room_id,
                        semester,
                        amount_due,
                        amount_paid,
                        payment_date,
                        reference_number,
                        note,
                        recorded_by,
                        created_at,
                        payment_method
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Offline')
                    """,
                    (
                        student_id,
                        room_id,
                        semester,
                        amount_due,
                        amount_paid,
                        request.form.get("payment_date") or None,
                        request.form.get("reference_number", "").strip(),
                        request.form.get("note", "").strip(),
                        session["user_id"],
                        datetime.now().isoformat(timespec="seconds")
                    )
                )

                conn.commit()

                remaining_due = round(amount_due - amount_paid, 2)

                flash(
                    f"Hostel installment saved. "
                    f"Outstanding before payment: ₹{amount_due:.2f}, "
                    f"Paid now: ₹{amount_paid:.2f}, "
                    f"Remaining Due: ₹{remaining_due:.2f}",
                    "success"
                )

            elif action == "record_mess_payment":
                if request.form.get("payment_method", "Offline") != "Offline":
                    raise ValueError("Wardens can record offline payments only. Online payments are recorded automatically by the student portal.")
                student_id = int(request.form.get("student_id", "0"))
                option = request.form.get("payment_option", "")
                period = request.form.get("period_label", "").strip()
                amount_due_text = request.form.get("amount_due", "").strip()
                amount_paid_text = request.form.get("amount_paid", "0").strip() or "0"
                if option not in ("Daily", "Monthly", "Other"):
                    raise ValueError("Select Daily, Monthly, or Other mess payment.")
                # Friendly defaults: common Daily/Monthly amounts and a period label
                # are supplied if the form is submitted without them.
                if not period:
                    period = datetime.now().strftime("%B %Y") if option == "Monthly" else datetime.now().strftime("%Y-%m-%d")
                if not amount_due_text:
                    if option == "Daily":
                        amount_due_text = "100"
                    elif option == "Monthly":
                        amount_due_text = "31000"
                    else:
                        raise ValueError("Enter the amount due for the Other mess payment option.")
                amount_due = float(amount_due_text)
                amount_paid = float(amount_paid_text)
                if amount_due <= 0 or amount_paid < 0 or amount_paid > amount_due:
                    raise ValueError("Enter a positive amount due and a paid amount between ₹0 and the amount due.")
                student = conn.execute("SELECT id FROM users WHERE id=? AND role='student' AND (? IS NULL OR hostel_type=?)", (student_id, own_hostel, own_hostel)).fetchone()
                if not student:
                    raise ValueError("Select a valid student.")
                conn.execute("""INSERT INTO mess_payments(student_id,payment_option,period_label,amount_due,amount_paid,payment_date,reference_number,note,recorded_by,created_at,payment_method)
                                VALUES(?,?,?,?,?,?,?,?,?,?, 'Offline')""",
                             (student_id, option, period, amount_due, amount_paid, request.form.get("payment_date") or None,
                              request.form.get("reference_number","").strip(), request.form.get("note","").strip(),
                              session["user_id"], datetime.now().isoformat(timespec="seconds")))
                conn.commit()
                flash("Mess fee record saved.", "success")
            else:
                raise ValueError("Unknown action.")
        except (ValueError, TypeError) as exc:
            conn.rollback()
            flash(str(exc), "error")
        except sqlite3.IntegrityError:
            conn.rollback()
            flash("Could not save. Check for duplicate floor/room number or invalid details.", "error")
        finally:
            conn.close()
        return redirect(url_for("hostel_management"))

    params = []
    hostel_filter = ""
    if own_hostel:
        hostel_filter = " WHERE hostel_type=?"
        params.append(own_hostel)
    floors = conn.execute("SELECT * FROM hostel_floors" + hostel_filter + " ORDER BY hostel_type,floor_number", params).fetchall()
    rooms = conn.execute("""
        SELECT r.*, f.floor_number,
        (SELECT COUNT(*) FROM room_allocations a WHERE a.room_id=r.id AND a.status='Active') AS occupied,
        (r.capacity - (SELECT COUNT(*) FROM room_allocations a WHERE a.room_id=r.id AND a.status='Active')) AS available
        FROM hostel_rooms r JOIN hostel_floors f ON f.id=r.floor_id
    """ + (" WHERE r.hostel_type=?" if own_hostel else "") + " ORDER BY r.hostel_type,f.floor_number,r.room_number",
        (own_hostel,) if own_hostel else ()).fetchall()
    students = conn.execute("SELECT id,name,roll_number,hostel_type,room_preference FROM users WHERE role='student' " +
                            ("AND hostel_type=? " if own_hostel else "") + "ORDER BY name",
                            (own_hostel,) if own_hostel else ()).fetchall()
    active_allocations = conn.execute("""
        SELECT a.id, a.student_id, a.semester, u.name AS student_name, u.roll_number, r.room_number, r.hostel_type, r.room_type,
               f.floor_number, r.semester_rent
        FROM room_allocations a JOIN users u ON u.id=a.student_id
        JOIN hostel_rooms r ON r.id=a.room_id JOIN hostel_floors f ON f.id=r.floor_id
        WHERE a.status='Active' """ + ("AND r.hostel_type=? " if own_hostel else "") +
        "ORDER BY r.hostel_type,f.floor_number,r.room_number,u.name",
        (own_hostel,) if own_hostel else ()).fetchall()
    fee_rows = conn.execute("""
        SELECT p.*,u.name,u.roll_number FROM hostel_fee_payments p JOIN users u ON u.id=p.student_id
        """ + ("WHERE u.hostel_type=? " if own_hostel else "") + "ORDER BY p.id DESC LIMIT 200",
        (own_hostel,) if own_hostel else ()).fetchall()
    mess_rows = conn.execute("""
        SELECT p.*,u.name,u.roll_number FROM mess_payments p JOIN users u ON u.id=p.student_id
        """ + ("WHERE u.hostel_type=? " if own_hostel else "") + "ORDER BY p.id DESC LIMIT 200",
        (own_hostel,) if own_hostel else ()).fetchall()
    conn.close()
    room_summary = {}
    for h in ("Boys", "Girls"):
        if own_hostel and h != own_hostel:
            continue
        hr = [r for r in rooms if r["hostel_type"] == h]
        room_summary[h] = {
            "rooms": len(hr),
            "occupied": sum(1 for r in hr if r["occupied"] > 0),
            "available": sum(1 for r in hr if r["available"] > 0),
            "beds": sum(r["capacity"] for r in hr),
            "occupied_beds": sum(r["occupied"] for r in hr),
            "available_beds": sum(r["available"] for r in hr)
        }
    return render_template("hostel_management.html", own_hostel=own_hostel, floors=floors, rooms=rooms,
                           students=students, allocations=active_allocations, fee_rows=fee_rows,
                           mess_rows=mess_rows, room_summary=room_summary, role=role)


@app.route("/student/pay-fee", methods=["POST"])
def student_pay_fee():
    """Online payments are disabled. Students must pay the warden offline."""
    if not role_required("student"):
        return redirect(url_for("login"))

    flash(
        "Online payments are disabled. Please contact your hostel warden "
        "to pay your outstanding fee.",
        "info"
    )
    return redirect(url_for("student_fees"))

@app.route("/student/verify-online-payment", methods=["POST"])
def verify_online_payment():
    """Reject online payment verification because online payments are disabled."""
    if not role_required("student"):
        return redirect(url_for("login"))

    flash(
        "Online payments are disabled. If you have a previous payment "
        "reference, please contact your hostel warden for verification.",
        "error"
    )
    return redirect(url_for("student_fees"))
@app.route("/student/fees")
def student_fees():
    if not role_required("student"):
        return redirect(url_for("login"))
    conn = get_db()
    uid = session["user_id"]
    hostel_fees = conn.execute("SELECT * FROM hostel_fee_payments WHERE student_id=? ORDER BY id DESC", (uid,)).fetchall()
    mess_fees = conn.execute("SELECT * FROM mess_payments WHERE student_id=? ORDER BY id DESC", (uid,)).fetchall()
    transactions = conn.execute("SELECT * FROM fee_transactions WHERE student_id=? ORDER BY id DESC", (uid,)).fetchall()
    active = conn.execute("""
        SELECT r.*, f.floor_number, a.semester, a.allocated_at FROM room_allocations a
        JOIN hostel_rooms r ON r.id=a.room_id JOIN hostel_floors f ON f.id=r.floor_id
        WHERE a.student_id=? AND a.status='Active' LIMIT 1
    """, (uid,)).fetchone()
    allocation_history = conn.execute("""
        SELECT a.semester,a.allocated_at,a.vacated_at,a.status,r.room_number,r.room_type,r.hostel_type,f.floor_number
        FROM room_allocations a JOIN hostel_rooms r ON r.id=a.room_id JOIN hostel_floors f ON f.id=r.floor_id
        WHERE a.student_id=? ORDER BY a.id DESC
    """, (uid,)).fetchall()
    conn.close()
    return render_template("student_fees.html", hostel_fees=hostel_fees, mess_fees=mess_fees, transactions=transactions, active=active, allocation_history=allocation_history)


@app.errorhandler(404)
def page_not_found(error):

    return """
    <div style="
        font-family: Arial;
        text-align: center;
        padding: 80px;
    ">
        <h1>404</h1>
        <h2>Page Not Found</h2>
        <a href="/">Go Home</a>
    </div>
    """, 404


# ============================================================
# START APPLICATION
# ============================================================

# Run migrations/demo setup on import as well, so deployment servers
# such as Gunicorn also create the required tables and folders.
init_db()
ensure_demo_users()
ensure_demo_staff()

if __name__ == "__main__":


    # Create demo users
    ensure_demo_users()

    # Create Boys/Girls maintenance staff
    ensure_demo_staff()

    print("=" * 60)
    print("SMART HOSTEL COMPLAINT & MAINTENANCE SYSTEM")
    print("=" * 60)

    print("\nDemo Login Details:\n")

    print("STUDENT")
    print("Username/Roll : 24CSE1001")
    print("Password      : student123")

    print("\nBOYS WARDEN")
    print("Username      : boyswarden")
    print("Password      : boys123")

    print("\nGIRLS WARDEN")
    print("Username      : girlswarden")
    print("Password      : girls123")

    print("\nADMIN")
    print("Username      : admin")
    print("Password      : admin123")

    print("\nBOYS STAFF")
    print("boys_electrical / staff123")
    print("boys_plumber / staff123")
    print("boys_cleaning / staff123")
    print("boys_wifi / staff123")

    print("\nGIRLS STAFF")
    print("girls_electrical / staff123")
    print("girls_plumber / staff123")
    print("girls_cleaning / staff123")
    print("girls_wifi / staff123")

    print("\nServer starting...")
    print("http://127.0.0.1:5000")
    print("=" * 60)

    app.run(
        debug=True,
        use_reloader=False,
        host="127.0.0.1",
        port=5000
    )
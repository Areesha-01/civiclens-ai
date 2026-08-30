import os
import uuid
import hashlib
import secrets
import threading
from functools import wraps
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv

from ai_verification import analyze_report_image

load_dotenv()

app = Flask(__name__)
IS_PRODUCTION = os.environ.get("RENDER") == "true"
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-fallback-key-change-me')
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if IS_PRODUCTION else 'Lax'
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION

CORS(app, supports_credentials=True, origins=[FRONTEND_ORIGIN, "http://localhost:5173"])

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")
pool = ConnectionPool(
    DATABASE_URL,
    min_size=1,
    max_size=3,
    open=True,
    check=ConnectionPool.check_connection,
)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_db_connection():
    """Get a connection from the pool instead of opening a fresh one each time."""
    return pool.connection()


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${digest}"


def verify_password(password, stored_hash):
    try:
        salt, digest = stored_hash.split("$")
        return hashlib.sha256((salt + password).encode()).hexdigest() == digest
    except Exception:
        return False


def hash_cnic(cnic):
    """CNIC is sensitive PII — never store it in plain text."""
    return hashlib.sha256(cnic.strip().encode()).hexdigest()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "citizen_id" not in session:
            return jsonify({"error": "Please log in to submit a report."}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("is_admin"):
            return jsonify({"error": "Admin login required."}), 401
        return f(*args, **kwargs)
    return wrapper


def init_db():
    """Create all tables if they don't already exist."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id SERIAL PRIMARY KEY,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                image_path TEXT NOT NULL,
                lat DOUBLE PRECISION NOT NULL,
                lng DOUBLE PRECISION NOT NULL,
                ai_label TEXT,
                ai_confidence TEXT,
                ai_priority TEXT,
                ai_reasoning TEXT,
                status TEXT DEFAULT 'pending_verification',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS citizens (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL,
                cnic_hash TEXT NOT NULL UNIQUE,
                phone TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id SERIAL PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
            """
        )

        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_priority TEXT;")
        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_reasoning TEXT;")
        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS citizen_id INTEGER REFERENCES citizens(id);")
        cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS area TEXT;")

        cur.execute("SELECT COUNT(*) FROM admins;")
        if cur.fetchone()[0] == 0:
            demo_hash = hash_password("admin123")
            cur.execute(
                "INSERT INTO admins (username, password_hash) VALUES (%s, %s);",
                ("admin", demo_hash),
            )

        conn.commit()
        cur.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def process_verification_async(report_id, image_bytes, mime_type, description, category):
    """Runs in a background thread so the citizen gets an instant response
    instead of waiting for the AI call and DB write to finish."""
    try:
        ai_result = analyze_report_image(image_bytes, mime_type, description, category)

        ai_label = ai_result.get("predicted_category", category)
        ai_confidence = ai_result.get("confidence", "unknown")
        ai_priority = ai_result.get("priority", "medium")
        ai_reasoning = ai_result.get("reasoning", "")
        is_genuine = ai_result.get("is_genuine")
        category_match = ai_result.get("category_match", True)

        if is_genuine is True and category_match is False:
            status = "rejected"
            ai_reasoning = (
                f"Category mismatch: photo shows '{ai_label}', not '{category}'. {ai_reasoning}"
            ).strip()
        elif is_genuine is False:
            status = "rejected"
        elif is_genuine is True:
            status = "verified"
        else:
            status = "pending_verification"

        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE reports
                SET status = %s, ai_label = %s, ai_confidence = %s,
                    ai_priority = %s, ai_reasoning = %s
                WHERE id = %s;
                """,
                (status, ai_label, ai_confidence, ai_priority, ai_reasoning, report_id),
            )
            conn.commit()
            cur.close()
    except Exception as e:
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE reports SET ai_reasoning = %s WHERE id = %s;",
                    (f"Background verification crashed: {str(e)}", report_id),
                )
                conn.commit()
                cur.close()
        except Exception:
            pass


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


# ---------- Citizen auth ----------

@app.route("/citizen/signup", methods=["POST"])
def citizen_signup():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    cnic = (data.get("cnic") or "").strip()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    if not full_name or not cnic or not phone or not password:
        return jsonify({"error": "All fields are required."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    cnic_hash = hash_cnic(cnic)
    password_hash = hash_password(password)

    with get_db_connection() as conn:
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO citizens (full_name, cnic_hash, phone, password_hash) VALUES (%s, %s, %s, %s) RETURNING id;",
                (full_name, cnic_hash, phone, password_hash),
            )
            citizen_id = cur.fetchone()[0]
            conn.commit()
        except psycopg.errors.UniqueViolation:
            conn.rollback()
            cur.close()
            return jsonify({"error": "An account with this CNIC already exists."}), 409
        cur.close()

    session["citizen_id"] = citizen_id
    session["citizen_name"] = full_name
    return jsonify({"id": citizen_id, "full_name": full_name}), 201


@app.route("/citizen/login", methods=["POST"])
def citizen_login():
    data = request.get_json(silent=True) or {}
    cnic = (data.get("cnic") or "").strip()
    password = data.get("password") or ""

    cnic_hash = hash_cnic(cnic)
    with get_db_connection() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute("SELECT * FROM citizens WHERE cnic_hash = %s;", (cnic_hash,))
        citizen = cur.fetchone()
        cur.close()

    if not citizen or not verify_password(password, citizen["password_hash"]):
        return jsonify({"error": "Invalid CNIC or password."}), 401

    session["citizen_id"] = citizen["id"]
    session["citizen_name"] = citizen["full_name"]
    return jsonify({"id": citizen["id"], "full_name": citizen["full_name"]})


@app.route("/citizen/me", methods=["GET"])
def citizen_me():
    if "citizen_id" not in session:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "id": session["citizen_id"], "full_name": session["citizen_name"]})


@app.route("/citizen/logout", methods=["POST"])
def citizen_logout():
    session.pop("citizen_id", None)
    session.pop("citizen_name", None)
    return jsonify({"ok": True})


# ---------- Admin auth ----------

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    with get_db_connection() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute("SELECT * FROM admins WHERE username = %s;", (username,))
        admin = cur.fetchone()
        cur.close()

    if not admin or not verify_password(password, admin["password_hash"]):
        return jsonify({"error": "Invalid username or password."}), 401

    session["is_admin"] = True
    session["admin_username"] = username
    return jsonify({"username": username})


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    session.pop("admin_username", None)
    return jsonify({"ok": True})


@app.route("/admin/me", methods=["GET"])
def admin_me():
    if session.get("is_admin"):
        return jsonify({"logged_in": True, "username": session.get("admin_username")})
    return jsonify({"logged_in": False})


# ---------- Reports ----------

@app.route("/submit-report", methods=["POST"])
@login_required
def submit_report():
    photo = request.files.get("photo")
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "other").strip()
    area = request.form.get("area", "").strip()
    lat = request.form.get("lat")
    lng = request.form.get("lng")

    if not photo or photo.filename == "":
        return jsonify({"error": "Photo is required."}), 400
    if not allowed_file(photo.filename):
        return jsonify({"error": "Unsupported image format."}), 400
    if not description:
        return jsonify({"error": "Description is required."}), 400
    if not area:
        return jsonify({"error": "Area is required."}), 400
    if lat is None or lng is None:
        return jsonify({"error": "Location is required."}), 400

    ext = photo.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    image_bytes = photo.read()
    with open(os.path.join(UPLOAD_FOLDER, unique_name), "wb") as f:
        f.write(image_bytes)

    mime_type = photo.mimetype or f"image/{ext}"

    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO reports
                (description, category, area, image_path, lat, lng, status, citizen_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, status, created_at;
            """,
            (description, category, area, unique_name, float(lat), float(lng),
             "pending_verification", session["citizen_id"]),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()

    report_id = row[0]

    thread = threading.Thread(
        target=process_verification_async,
        args=(report_id, image_bytes, mime_type, description, category),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "id": report_id,
        "status": "pending_verification",
        "created_at": row[2].isoformat(),
        "image_url": f"/uploads/{unique_name}",
        "citizen_category": category,
        "message": "Your report was received and is being verified by AI. This usually takes a few seconds.",
    }), 201


@app.route("/reports", methods=["GET"])
def get_reports():
    with get_db_connection() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute("SELECT * FROM reports ORDER BY created_at DESC;")
        rows = cur.fetchall()
        cur.close()

    reports = []
    for r in rows:
        reports.append({
            "id": r["id"],
            "description": r["description"],
            "category": r["category"],
            "area": r["area"],
            "lat": r["lat"],
            "lng": r["lng"],
            "status": r["status"],
            "ai_label": r["ai_label"],
            "ai_confidence": r["ai_confidence"],
            "ai_priority": r["ai_priority"],
            "ai_reasoning": r["ai_reasoning"],
            "image_url": f"/uploads/{r['image_path']}",
            "created_at": r["created_at"].isoformat(),
        })
    return jsonify(reports)


@app.route("/admin/reports", methods=["GET"])
@admin_required
def admin_get_reports():
    with get_db_connection() as conn:
        cur = conn.cursor(row_factory=dict_row)
        cur.execute(
            """
            SELECT r.*, c.full_name AS citizen_name, c.phone AS citizen_phone
            FROM reports r
            LEFT JOIN citizens c ON r.citizen_id = c.id
            ORDER BY r.created_at DESC;
            """
        )
        rows = cur.fetchall()
        cur.close()

    reports = []
    for r in rows:
        reports.append({
            "id": r["id"],
            "description": r["description"],
            "category": r["category"],
            "area": r["area"],
            "lat": r["lat"],
            "lng": r["lng"],
            "status": r["status"],
            "ai_label": r["ai_label"],
            "ai_confidence": r["ai_confidence"],
            "ai_priority": r["ai_priority"],
            "ai_reasoning": r["ai_reasoning"],
            "image_url": f"/uploads/{r['image_path']}",
            "created_at": r["created_at"].isoformat(),
            "citizen_name": r["citizen_name"],
            "citizen_phone": r["citizen_phone"],
        })
    return jsonify(reports)


@app.route("/uploads/<filename>", methods=["GET"])
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
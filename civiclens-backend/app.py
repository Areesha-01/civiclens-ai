import os
import uuid
from datetime import datetime, timezone

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from ai_verification import analyze_report_image

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DATABASE_URL = os.environ.get("DATABASE_URL")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}


def get_db_connection():
    """Open a new connection to the PostgreSQL database."""
    return psycopg.connect(DATABASE_URL)


def init_db():
    """Create the reports table if it doesn't already exist."""
    conn = get_db_connection()
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
    # Safe to re-run: adds any columns missing from an older version of this table
    cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_priority TEXT;")
    cur.execute("ALTER TABLE reports ADD COLUMN IF NOT EXISTS ai_reasoning TEXT;")
    conn.commit()
    cur.close()
    conn.close()


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.now(timezone.utc).isoformat()})


@app.route("/submit-report", methods=["POST"])
def submit_report():
    photo = request.files.get("photo")
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "other").strip()
    lat = request.form.get("lat")
    lng = request.form.get("lng")

    if not photo or photo.filename == "":
        return jsonify({"error": "Photo is required."}), 400
    if not allowed_file(photo.filename):
        return jsonify({"error": "Unsupported image format."}), 400
    if not description:
        return jsonify({"error": "Description is required."}), 400
    if lat is None or lng is None:
        return jsonify({"error": "Location is required."}), 400

    # Save the image with a unique filename so uploads never collide
    ext = photo.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    image_bytes = photo.read()
    with open(os.path.join(UPLOAD_FOLDER, unique_name), "wb") as f:
        f.write(image_bytes)

    mime_type = photo.mimetype or f"image/{ext}"
    ai_result = analyze_report_image(image_bytes, mime_type, description, category)

    ai_label = ai_result.get("predicted_category", category)
    ai_confidence = ai_result.get("confidence", "unknown")
    ai_priority = ai_result.get("priority", "medium")
    ai_reasoning = ai_result.get("reasoning", "")
    is_genuine = ai_result.get("is_genuine")

    if is_genuine is False:
        status = "rejected_low_confidence"
    elif is_genuine is True:
        status = "verified"
    else:
        status = "pending_verification"

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO reports
            (description, category, image_path, lat, lng, status,
             ai_label, ai_confidence, ai_priority, ai_reasoning)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, status, created_at;
        """,
        (description, category, unique_name, float(lat), float(lng), status,
         ai_label, ai_confidence, ai_priority, ai_reasoning),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({
        "id": row[0],
        "status": row[1],
        "created_at": row[2].isoformat(),
        "image_url": f"/uploads/{unique_name}",
        "ai_label": ai_label,
        "ai_confidence": ai_confidence,
        "ai_priority": ai_priority,
        "ai_reasoning": ai_reasoning,
    }), 201


@app.route("/reports", methods=["GET"])
def get_reports():
    conn = get_db_connection()
    cur = conn.cursor(row_factory=dict_row)
    cur.execute("SELECT * FROM reports ORDER BY created_at DESC;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    reports = []
    for r in rows:
        reports.append({
            "id": r["id"],
            "description": r["description"],
            "category": r["category"],
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


@app.route("/uploads/<filename>", methods=["GET"])
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

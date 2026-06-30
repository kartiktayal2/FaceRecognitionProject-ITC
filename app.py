# =============================================================
# ITC Customer Analytics — app.py
# Flask + OpenCV + face_recognition + PostgreSQL
# =============================================================

import base64
import cv2
import face_recognition
import io
import json
import numpy as np
import os
import time

from detectors import smoking_detector
from PIL import Image
from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    request,
    Response,
    jsonify,
)

from database import get_connection


# =============================================================
# FLASK APP INIT
# =============================================================

app = Flask(__name__)

# Used by the System Information panel in the Admin Panel
APP_START_TIME: datetime = datetime.now()


# =============================================================
# SYSTEM SETTINGS — loaded from PostgreSQL at startup.
# The table `system_settings` must already exist with id = 1.
# Call reload_system_settings() after any POST to /settings so
# the new values take effect immediately without a server restart.
# =============================================================

# Safe fallback defaults — used only if the DB row is missing.
_SETTINGS_DEFAULTS: dict = {
    "new_face_delay":           3,
    "cooldown_seconds":         10,
    "pending_expire_seconds":   8,
    "known_threshold":          0.45,
    "unknown_threshold":        0.40,
    "dashboard_refresh_seconds":5,
    "auto_delete_logs_days":    3,
}


def load_system_settings() -> dict:
    """
    Read the single system_settings row (id = 1) from PostgreSQL.
    Returns a plain dict keyed by column name.
    Falls back to _SETTINGS_DEFAULTS if the row is not found or
    a database error occurs, so the application never crashes on startup.
    """
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            SELECT
                new_face_delay,
                cooldown_seconds,
                pending_expire_seconds,
                known_threshold,
                unknown_threshold,
                dashboard_refresh_seconds,
                auto_delete_logs_days
            FROM system_settings
            WHERE id = 1
            """
        )
        row = cur.fetchone()
        cur.close()
        conn.close()

        if row is None:
            print("[settings] WARNING: system_settings row id=1 not found — using defaults.")
            return dict(_SETTINGS_DEFAULTS)

        return {
            "new_face_delay":           float(row[0]),
            "cooldown_seconds":         float(row[1]),
            "pending_expire_seconds":   float(row[2]),
            "known_threshold":          float(row[3]),
            "unknown_threshold":        float(row[4]),
            "dashboard_refresh_seconds":int(row[5]),
            "auto_delete_logs_days":    int(row[6]),
        }

    except Exception as exc:
        print(f"[settings] ERROR loading system settings: {exc} — using defaults.")
        return dict(_SETTINGS_DEFAULTS)


def reload_system_settings() -> None:
    """
    Re-read system_settings from PostgreSQL and update the global
    SETTINGS dict in-place so all in-flight requests pick up the new
    values without a server restart.
    """
    global SETTINGS
    SETTINGS = load_system_settings()
    print(f"[settings] Reloaded: {SETTINGS}")


# Load once at module import time; routes use SETTINGS[...] directly.
SETTINGS: dict = load_system_settings()
print(f"[settings] Loaded at startup: {SETTINGS}")


# =============================================================
# IN-MEMORY FACE CACHE
# Loaded at startup; refreshed only after registration or
# after a new unknown customer is inserted.
# =============================================================

known_encodings  = []   # list of np.ndarray
known_names      = []   # list of str
known_ids        = []   # list of int (customers.id)

unknown_encodings = []  # list of np.ndarray
unknown_ids       = []  # list of int (unknown_customers.id)




# How often to call the Roboflow API
SMOKING_DETECT_EVERY_N_FRAMES = 8

# Internal frame counter
_smoking_frame_counter = 0

# Cache of the last detections
_last_smoking_detections = []


# =============================================================
# COOLDOWN / STATE TRACKING (in-process RAM only)
# =============================================================

# {customer_id: datetime}  — prevents re-counting known customers
known_cooldown: dict = {}

# {unknown_customer_id: datetime}  — prevents re-counting returning unknown
returning_cooldown: dict = {}

# =============================================================
# PENDING UNKNOWN FACE TRACKER (VERSION 2)
# -------------------------------------------------------------
# WHY THIS EXISTS:
#
# The previous implementation used a rounded face encoding as
# a dictionary key. Face encodings change slightly every frame,
# causing the timer to restart continuously.
#
# This implementation tracks ONLY ONE pending unknown face.
# If the same face remains visible (distance < threshold),
# the timer continues.
#
# If a different face appears, the timer restarts.
#
# Debug Prefix:
#     [PENDING]
# =============================================================

pending_unknown_face = None

# NOTE: NEW_FACE_WAIT_SECONDS, COOLDOWN_SECONDS, and PENDING_EXPIRE_SECONDS
# are no longer hardcoded here. Use SETTINGS["new_face_delay"],
# SETTINGS["cooldown_seconds"], and SETTINGS["pending_expire_seconds"] instead.


# =============================================================
# CAMERA — isolated so it can be swapped for a different
#          source at deployment time without touching logic.
# =============================================================

CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", 0))
camera: cv2.VideoCapture = cv2.VideoCapture(CAMERA_INDEX)


# =============================================================
# HELPER — encoding fingerprint
# A cheap, hashable key derived from the first 8 floats of the
# 128-d face encoding.  Good enough to group frames of the same
# face without a full distance search.
# =============================================================



# =============================================================
# HELPER — upsert today's row in daily_statistics
# =============================================================

def _ensure_daily_stats(cur, today: str) -> None:
    """Insert today's row if it does not yet exist."""
    cur.execute(
        """
        INSERT INTO daily_statistics (stat_date, known_today, unknown_today, returning_unknown_today)
        VALUES (%s, 0, 0, 0)
        ON CONFLICT (stat_date) DO NOTHING
        """,
        (today,),
    )


# =============================================================
# HELPER — log a visit and bump daily statistics
# customer_type: 'known' | 'unknown' | 'returning_unknown'
# =============================================================

def _record_visit(cur, customer_type: str, customer_id: int, today: str) -> None:
    """Insert a visit_log row and increment the matching daily counter."""
    cur.execute(
        """
        INSERT INTO visit_logs (customer_type, customer_id, visit_time)
        VALUES (%s, %s, NOW())
        """,
        (customer_type, customer_id),
    )

    if customer_type == "known":
        col = "known_today"
    elif customer_type == "unknown":
        col = "unknown_today"
    else:
        col = "returning_unknown_today"

    cur.execute(
        f"""
        UPDATE daily_statistics
        SET {col} = {col} + 1
        WHERE stat_date = %s
        """,
        (today,),
    )


# =============================================================
# CACHE LOAD FUNCTIONS
# =============================================================

def load_customer_faces() -> None:
    """Load all registered customers into RAM."""
    global known_encodings, known_names, known_ids

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute(
        "SELECT id, name, face_encoding FROM customers"
    )
    rows = cur.fetchall()

    conn.close()

    known_ids       = [r[0] for r in rows]
    known_names     = [r[1] for r in rows]
    known_encodings = [np.array(json.loads(r[2])) for r in rows]

    print(f"[cache] Loaded {len(rows)} customer face(s) into memory.")


def load_unknown_faces() -> None:
    """Load all previously-seen unknown customers into RAM."""
    global unknown_encodings, unknown_ids

    conn = get_connection()
    cur  = conn.cursor()

    cur.execute(
        "SELECT id, face_encoding FROM unknown_customers"
    )
    rows = cur.fetchall()

    conn.close()

    unknown_ids       = [r[0] for r in rows]
    unknown_encodings = [np.array(json.loads(r[1])) for r in rows]

    print(f"[cache] Loaded {len(rows)} unknown face(s) into memory.")


def refresh_face_cache() -> None:
    """Reload both caches.  Call after any DB write that adds new faces."""
    load_customer_faces()
    load_unknown_faces()


# =============================================================
# MAINTENANCE — delete visit_logs older than 3 days
# =============================================================

def delete_old_logs() -> None:
    conn = get_connection()
    cur  = conn.cursor()

    # Number of days to retain is configurable via system_settings.
    cutoff = datetime.now() - timedelta(days=SETTINGS["auto_delete_logs_days"])

    cur.execute(
        "DELETE FROM visit_logs WHERE visit_time < %s",
        (cutoff,),
    )

    deleted = cur.rowcount
    conn.commit()
    conn.close()

    print(f"[maintenance] Deleted {deleted} old visit log(s) (older than 3 days).")


# =============================================================
# ROUTES — pages
# =============================================================

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register-page")
def register_page():
    return render_template("register.html")


@app.route("/dashboard")
def dashboard():
    """
    Render the dashboard HTML page.
    All actual data is fetched by the frontend via /dashboard-data (JSON).
    """
    return render_template("dashboard.html")


# =============================================================
# ROUTE — dashboard data (JSON)
# Returns stats, top customers, recent visits, and a dynamic
# 7-day chart pulled from daily_statistics.
# =============================================================

@app.route("/dashboard-data")
def dashboard_data():
    conn = get_connection()
    cur  = conn.cursor()

    today = datetime.now().date().isoformat()

    # --- Ensure today exists so counts never come back NULL ---
    _ensure_daily_stats(cur, today)
    conn.commit()

    # --- Summary counts ---
    cur.execute("SELECT COUNT(*) FROM customers")
    total_registered = cur.fetchone()[0]

    cur.execute(
        "SELECT known_today, unknown_today, returning_unknown_today "
        "FROM daily_statistics WHERE stat_date = %s",
        (today,),
    )
    row = cur.fetchone()
    known_today              = row[0] if row else 0
    unknown_today            = row[1] if row else 0
    returning_unknown_today  = row[2] if row else 0

    # --- Top 5 customers by visit count ---
    cur.execute(
        """
        SELECT name, visit_count
        FROM customers
        ORDER BY visit_count DESC
        LIMIT 5
        """
    )
    top_customers = [
        {"name": r[0], "visit_count": r[1]}
        for r in cur.fetchall()
    ]

    # --- Recent 10 visits ---
    cur.execute(
        """
        SELECT
            vl.customer_type,
            vl.customer_id,
            vl.visit_time,
            COALESCE(c.name, 'Unknown #' || vl.customer_id::text) AS display_name
        FROM visit_logs vl
        LEFT JOIN customers c
            ON vl.customer_type = 'known' AND c.id = vl.customer_id
        ORDER BY vl.id DESC
        LIMIT 10
        """
    )
    recent_visits = [
        {
            "type":    r[0],
            "id":      r[1],
            "time":    r[2].strftime("%Y-%m-%d %H:%M:%S"),
            "name":    r[3],
        }
        for r in cur.fetchall()
    ]

    # --- Last 7 days chart data from daily_statistics ---
    cur.execute(
        """
        SELECT stat_date, known_today, unknown_today
        FROM daily_statistics
        WHERE stat_date >= CURRENT_DATE - INTERVAL '6 days'
        ORDER BY stat_date ASC
        """
    )
    chart_rows = cur.fetchall()

    # Build a complete 7-day series (fill missing days with 0)
    chart = []
    for i in range(6, -1, -1):
        d = (datetime.now().date() - timedelta(days=i)).isoformat()
        chart.append({"day": d, "known": 0, "unknown": 0})

    for r in chart_rows:
        date_str = r[0].isoformat() if hasattr(r[0], "isoformat") else str(r[0])
        for entry in chart:
            if entry["day"] == date_str:
                entry["known"]   = r[1]
                entry["unknown"] = r[2]
                break

    conn.close()

    return jsonify(
        {
            "total_registered":         total_registered,
            "known_today":              known_today,
            "unknown_today":            unknown_today,
            "returning_unknown_today":  returning_unknown_today,
            "top_customers":            top_customers,
            "recent_visits":            recent_visits,
            "chart":                    chart,
        }
    )


# =============================================================
# ROUTE — register a new customer via camera capture
# =============================================================

@app.route("/register-camera", methods=["POST"])
def register_camera():
    """
    Accepts JSON: { name, email, phone, image (base64 data-URL) }
    Encodes the face and stores it in PostgreSQL.
    Reloads the in-memory cache automatically.
    """
    data = request.json

    name  = data.get("name",  "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    image_data = data.get("image", "")

    if not name:
        return jsonify({"success": False, "message": "Name is required."}), 400

    # Decode base64 image
    try:
        raw = image_data.split(",")[1] if "," in image_data else image_data
        image_bytes = base64.b64decode(raw)
        image = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    except Exception as exc:
        return jsonify({"success": False, "message": f"Image decode error: {exc}"}), 400

    # Detect and encode face
    encodings = face_recognition.face_encodings(image)
    if len(encodings) == 0:
        return jsonify({"success": False, "message": "No face detected in the image."}), 400

    encoding = encodings[0]

    # Persist to PostgreSQL
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute(
        """
        INSERT INTO customers (name, email, phone, face_encoding)
        VALUES (%s, %s, %s, %s)
        """,
        (name, email, phone, json.dumps(encoding.tolist())),
    )

    conn.commit()
    conn.close()

    # Reload cache so the new face is active immediately
    refresh_face_cache()

    return jsonify({"success": True, "message": f"Customer '{name}' registered successfully."})


# =============================================================
# ROUTE — list all registered customers (JSON)
# =============================================================

@app.route("/customers")
def list_customers():
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute(
        """
        SELECT id, name, email, phone, visit_count, created_at, last_seen
        FROM customers
        ORDER BY name ASC
        """
    )
    rows = cur.fetchall()
    conn.close()

    customers = [
        {
            "id":          r[0],
            "name":        r[1],
            "email":       r[2],
            "phone":       r[3],
            "visit_count": r[4],
            "created_at":  r[5].strftime("%Y-%m-%d %H:%M:%S"),
            "last_seen":   r[6].strftime("%Y-%m-%d %H:%M:%S"),
        }
        for r in rows
    ]

    return jsonify(customers)


# =============================================================
# ROUTE — delete a registered customer
# =============================================================

@app.route("/delete-customer/<int:customer_id>", methods=["DELETE"])
def delete_customer(customer_id):
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
    conn.commit()
    conn.close()

    refresh_face_cache()

    return jsonify({"success": True, "message": f"Customer {customer_id} deleted."})


# =============================================================
# ROUTE — debug view (development aid, does not expose secrets)
# =============================================================

@app.route("/debug-db")
def debug_db():
    conn = get_connection()
    cur  = conn.cursor()

    cur.execute("SELECT id, name, email, phone, visit_count FROM customers")
    customers = cur.fetchall()

    cur.execute("SELECT id, visit_count, first_seen, last_seen FROM unknown_customers")
    unknowns = cur.fetchall()

    cur.execute("SELECT stat_date, known_today, unknown_today, returning_unknown_today FROM daily_statistics ORDER BY stat_date DESC LIMIT 7")
    stats = cur.fetchall()

    conn.close()

    return (
        f"<h2>Customers</h2><pre>{customers}</pre>"
        f"<h2>Unknown Customers</h2><pre>{unknowns}</pre>"
        f"<h2>Daily Statistics</h2><pre>{stats}</pre>"
    )


# =============================================================
# CAMERA — pause / resume (called by register page)
# =============================================================

@app.route("/pause-camera")
def pause_camera():
    global camera
    if camera is not None:
        camera.release()
        camera = None
    return "paused"


@app.route("/resume-camera")
def resume_camera():
    global camera
    camera = cv2.VideoCapture(CAMERA_INDEX)
    return "resumed"


# =============================================================
# RECOGNITION CORE — process one face encoding per frame
#
#  STEP 1 — Compare vs registered customers (green, threshold 0.45)
#  STEP 2 — Compare vs unknown_customers cache (yellow, threshold 0.40)
#  STEP 3 — Brand new face: show red, wait 3 s, then insert
# =============================================================

def _process_face(face_encoding: np.ndarray) -> tuple:
    """
    Determine the label, rectangle colour, and trigger any DB write
    for a single detected face.

    Returns (label: str, color: tuple[int,int,int])
    """
    global known_cooldown
    global returning_cooldown
    global pending_unknown_face
    global known_encodings, known_names, known_ids
    global unknown_encodings, unknown_ids

    now   = datetime.now()
    today = now.date().isoformat()

    # ----------------------------------------------------------
    # STEP 1 — registered customers
    # ----------------------------------------------------------
    if len(known_encodings) > 0:
        distances        = face_recognition.face_distance(known_encodings, face_encoding)
        best_idx         = int(np.argmin(distances))
        best_dist        = distances[best_idx]

        if best_dist < SETTINGS["known_threshold"]:
            customer_id   = known_ids[best_idx]
            customer_name = known_names[best_idx]

            # Cooldown check
            last = known_cooldown.get(customer_id)
            if last is None or (now - last).total_seconds() > SETTINGS["cooldown_seconds"]:
                known_cooldown[customer_id] = now

                conn = get_connection()
                cur  = conn.cursor()

                _ensure_daily_stats(cur, today)

                # Increment visit_count and update last_seen
                cur.execute(
                    """
                    UPDATE customers
                    SET visit_count = visit_count + 1,
                        last_seen   = NOW()
                    WHERE id = %s
                    """,
                    (customer_id,),
                )

                _record_visit(cur, "known", customer_id, today)

                conn.commit()
                conn.close()

                # Sync the in-memory name list (visit_count not cached, so no update needed)
                print(f"[recognition] Known customer: {customer_name} (id={customer_id})")

            return customer_name, (0, 255, 0)   # green

    # ----------------------------------------------------------
    # STEP 2 — previously-seen unknown customers
    # ----------------------------------------------------------
    if len(unknown_encodings) > 0:
        for i, stored_enc in enumerate(unknown_encodings):
            dist = face_recognition.face_distance([stored_enc], face_encoding)[0]

            if dist < SETTINGS["unknown_threshold"]:
                unknown_id = unknown_ids[i]

                last = returning_cooldown.get(unknown_id)
                if last is None or (now - last).total_seconds() > SETTINGS["cooldown_seconds"]:
                    returning_cooldown[unknown_id] = now

                    conn = get_connection()
                    cur  = conn.cursor()

                    _ensure_daily_stats(cur, today)

                    cur.execute(
                        """
                        UPDATE unknown_customers
                        SET visit_count = visit_count + 1,
                            last_seen   = NOW()
                        WHERE id = %s
                        """,
                        (unknown_id,),
                    )

                    _record_visit(cur, "returning_unknown", unknown_id, today)

                    conn.commit()
                    conn.close()

                    print(f"[recognition] Returning unknown id={unknown_id}")

                return "Returning Unknown", (0, 215, 255)   # yellow

    # ----------------------------------------------------------
    # STEP 3 — NEW UNKNOWN CUSTOMER (VERSION 2)
    # ----------------------------------------------------------
    # Uses face distance instead of unstable face keys.
    # Debug Prefix: [PENDING]
    # ----------------------------------------------------------

    if pending_unknown_face is None:

        pending_unknown_face = {
            "encoding": face_encoding.copy(),
            "first_seen": now,
            "last_seen": now,
        }

        print("[PENDING] Started tracking new face.")

        return "New Customer", (0, 0, 255)


    distance = face_recognition.face_distance(
        [pending_unknown_face["encoding"]],
        face_encoding
    )[0]

    if distance > 0.55:

        print(f"[PENDING] Different face detected ({distance:.3f}). Restarting timer.")

        pending_unknown_face = {
            "encoding": face_encoding.copy(),
            "first_seen": now,
            "last_seen": now,
        }

        return "New Customer", (0, 0, 255)


    pending_unknown_face["last_seen"] = now

    elapsed = (
        now - pending_unknown_face["first_seen"]
    ).total_seconds()

    print(f"[PENDING] Same face | elapsed={elapsed:.2f}s")

    if elapsed < SETTINGS["new_face_delay"]:
        return "New Customer", (0, 0, 255)


    print("[DB] Inserting unknown customer...")

    conn = get_connection()
    cur = conn.cursor()

    _ensure_daily_stats(cur, today)

    cur.execute(
        """
        INSERT INTO unknown_customers
        (
            face_encoding,
            visit_count,
            first_seen,
            last_seen
        )
        VALUES
        (
            %s,
            1,
            NOW(),
            NOW()
        )
        RETURNING id
        """,
        (
            json.dumps(
                pending_unknown_face["encoding"].tolist()
            ),
        ),
    )

    new_unknown_id = cur.fetchone()[0]

    _record_visit(
        cur,
        "unknown",
        new_unknown_id,
        today,
    )

    conn.commit()
    conn.close()

    unknown_ids.append(new_unknown_id)
    unknown_encodings.append(
        pending_unknown_face["encoding"].copy()
    )

    print(f"[DB] Unknown customer inserted (ID={new_unknown_id})")

    # Clear pending tracker after successful insert
    pending_unknown_face = None
    refresh_face_cache()

    # Prevent immediate re-insertion while the person
    # is still standing in front of the camera.
    returning_cooldown[new_unknown_id] = now

    return "New Customer", (0, 0, 255)




# =============================================================
# CAMERA STREAMING — gen_frames()
# Reuses the original streaming structure from the old app.py.
# Adds the new 3-step recognition logic via _process_face().
# =============================================================

def gen_frames():
    global camera
    global pending_unknown_face
    global _smoking_frame_counter, _last_smoking_detections

    while True:

        # Camera may be temporarily released during registration
        if camera is None:
            time.sleep(0.05)
            continue

        success, frame = camera.read()

        

        if not success:
            time.sleep(0.05)
            continue
        _smoking_frame_counter += 1
        
        if _smoking_frame_counter >= SMOKING_DETECT_EVERY_N_FRAMES:
            _smoking_frame_counter = 0
            _last_smoking_detections = smoking_detector.detect(frame)

        # Convert BGR frame to RGB for face_recognition
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Locate all faces in the current frame
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings_list = face_recognition.face_encodings(rgb_frame, face_locations)

        # ============================================================
        # PENDING UNKNOWN FACE CLEANUP (VERSION 2)
        #
        # If nobody has been seen for longer than the configured timeout,
        # discard the pending face so the next visitor starts fresh.
        # ============================================================

        now = datetime.now()

        if pending_unknown_face is not None:

            if "last_seen" not in pending_unknown_face:
                pending_unknown_face["last_seen"] = now

            idle_time = (
            now - pending_unknown_face["last_seen"]
            ).total_seconds()

            if idle_time > SETTINGS["pending_expire_seconds"]:

                print("[PENDING] Pending face expired.")

                pending_unknown_face = None

        # Process each detected face
        for (top, right, bottom, left), face_encoding in zip(
            face_locations, face_encodings_list
        ):
            label, color = _process_face(face_encoding)

            # Draw bounding rectangle
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            # Draw label above the rectangle
            cv2.putText(
                frame,
                label,
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

        # Encode frame as JPEG and yield for streaming
        ret, buffer = cv2.imencode(".jpg", frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + frame_bytes
            + b"\r\n"
        )


# =============================================================
# ROUTE — settings page
# =============================================================

@app.route("/settings")
def settings_page():
    """Render the settings configuration page."""
    return render_template("settings.html")


# =============================================================
# ROUTE — GET /settings  (JSON)
# Returns the current system_settings row as JSON.
# =============================================================

@app.route("/api/settings", methods=["GET"])
def get_settings():
    """Return current system settings from the in-memory SETTINGS dict."""
    return jsonify(SETTINGS)


# =============================================================
# ROUTE — POST /settings  (JSON)
# Accepts a JSON body with any subset of setting keys,
# persists them to PostgreSQL, then reloads SETTINGS in memory.
# No server restart required.
# =============================================================

@app.route("/api/settings", methods=["POST"])
def update_settings():
    """
    Update system_settings row id=1 in PostgreSQL.
    Accepts JSON: { new_face_delay, cooldown_seconds, pending_expire_seconds,
                    known_threshold, unknown_threshold,
                    dashboard_refresh_seconds, auto_delete_logs_days }
    All fields are optional; only provided fields are updated.
    """
    data = request.json
    if not data:
        return jsonify({"success": False, "message": "No data provided."}), 400

    # Allowed fields and their Python types for validation
    allowed: dict = {
        "new_face_delay":           float,
        "cooldown_seconds":         float,
        "pending_expire_seconds":   float,
        "known_threshold":          float,
        "unknown_threshold":        float,
        "dashboard_refresh_seconds":int,
        "auto_delete_logs_days":    int,
    }

    updates = {}
    errors  = []

    for key, cast in allowed.items():
        if key in data:
            try:
                updates[key] = cast(data[key])
            except (ValueError, TypeError):
                errors.append(f"'{key}' must be a valid {cast.__name__}.")

    if errors:
        return jsonify({"success": False, "message": " ".join(errors)}), 400

    if not updates:
        return jsonify({"success": False, "message": "No recognised fields provided."}), 400

    # Build a safe SET clause using column names we control (no user input in SQL)
    set_clause = ", ".join(f"{col} = %s" for col in updates)
    values     = list(updates.values()) + [1]   # id = 1

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            f"UPDATE system_settings SET {set_clause}, updated_at = NOW() WHERE id = %s",
            values,
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": f"Database error: {exc}"}), 500

    # Reload SETTINGS in memory — no restart required
    reload_system_settings()

    return jsonify({"success": True, "message": "Settings saved.", "settings": SETTINGS})


# =============================================================
# ROUTE — video feed
# =============================================================

@app.route("/video_feed")
def video_feed():
    return Response(
        gen_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


# =============================================================
# ADMIN PANEL — page route
# /settings is kept as a redirect so existing links still work.
# =============================================================

@app.route("/admin")
def admin_panel():
    """Render the full Admin Panel SPA."""
    return render_template("admin.html")


@app.route("/settings")
def settings_redirect():
    """Backward-compatible redirect — old /settings links go to admin."""
    from flask import redirect
    return redirect("/admin")


# =============================================================
# ADMIN API — helper: paginate a list
# =============================================================

def _paginate(rows: list, page: int, per_page: int) -> dict:
    """
    Slice *rows* and return a dict with pagination metadata.
    """
    total      = len(rows)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page        = max(1, min(page, total_pages))
    start       = (page - 1) * per_page
    end         = start + per_page
    return {
        "items":       rows[start:end],
        "total":       total,
        "page":        page,
        "per_page":    per_page,
        "total_pages": total_pages,
    }


# =============================================================
# ADMIN API — Registered Customers
# GET  /api/admin/customers          — paginated + search + sort
# PUT  /api/admin/customers/<id>     — edit name / email / phone
# DELETE /api/admin/customers/<id>   — delete + purge cache
# =============================================================

@app.route("/api/admin/customers", methods=["GET"])
def admin_list_customers():
    """
    Query params:
      search   — substring match on name / email / phone
      sort     — column: id | name | visit_count | last_seen  (default: name)
      order    — asc | desc  (default: asc)
      page     — int (default: 1)
      per_page — int (default: 20)
    """
    search   = request.args.get("search", "").strip()
    sort_col = request.args.get("sort",     "name")
    order    = request.args.get("order",    "asc").lower()
    page     = int(request.args.get("page",     1))
    per_page = int(request.args.get("per_page", 20))

    # Whitelist sort columns to prevent SQL injection
    allowed_sort = {"id", "name", "visit_count", "last_seen", "created_at"}
    if sort_col not in allowed_sort:
        sort_col = "name"
    direction = "DESC" if order == "desc" else "ASC"

    try:
        conn = get_connection()
        cur  = conn.cursor()

        if search:
            pattern = f"%{search}%"
            cur.execute(
                f"""
                SELECT id, name, email, phone, visit_count, created_at, last_seen
                FROM customers
                WHERE name ILIKE %s OR email ILIKE %s OR phone ILIKE %s
                ORDER BY {sort_col} {direction}
                """,
                (pattern, pattern, pattern),
            )
        else:
            cur.execute(
                f"""
                SELECT id, name, email, phone, visit_count, created_at, last_seen
                FROM customers
                ORDER BY {sort_col} {direction}
                """
            )

        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    items = [
        {
            "id":          r[0],
            "name":        r[1],
            "email":       r[2] or "",
            "phone":       r[3] or "",
            "visit_count": r[4],
            "created_at":  r[5].strftime("%Y-%m-%d %H:%M") if r[5] else "",
            "last_seen":   r[6].strftime("%Y-%m-%d %H:%M") if r[6] else "",
        }
        for r in rows
    ]

    return jsonify({"success": True, **_paginate(items, page, per_page)})


@app.route("/api/admin/customers/<int:customer_id>", methods=["PUT"])
def admin_edit_customer(customer_id):
    """
    Edit name, email, or phone for a registered customer.
    Accepts JSON: { name?, email?, phone? }
    """
    data = request.json or {}
    allowed = {"name", "email", "phone"}
    updates = {k: v.strip() for k, v in data.items() if k in allowed and isinstance(v, str)}

    if not updates:
        return jsonify({"success": False, "message": "No valid fields provided."}), 400

    if "name" in updates and not updates["name"]:
        return jsonify({"success": False, "message": "Name cannot be blank."}), 400

    set_clause = ", ".join(f"{col} = %s" for col in updates)
    values     = list(updates.values()) + [customer_id]

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            f"UPDATE customers SET {set_clause} WHERE id = %s",
            values,
        )
        affected = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    if affected == 0:
        return jsonify({"success": False, "message": "Customer not found."}), 404

    # Refresh name in the in-memory cache if the name changed
    if "name" in updates:
        for i, cid in enumerate(known_ids):
            if cid == customer_id:
                known_names[i] = updates["name"]
                break

    return jsonify({"success": True, "message": "Customer updated."})


@app.route("/api/admin/customers/<int:customer_id>", methods=["DELETE"])
def admin_delete_customer(customer_id):
    """
    Delete a registered customer, their visit logs, and evict them from
    the in-memory recognition cache immediately.
    """
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "DELETE FROM visit_logs WHERE customer_type = 'known' AND customer_id = %s",
            (customer_id,),
        )
        cur.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
        affected = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    if affected == 0:
        return jsonify({"success": False, "message": "Customer not found."}), 404

    # Evict from RAM cache without a full reload
    global known_ids, known_names, known_encodings
    if customer_id in known_ids:
        idx = known_ids.index(customer_id)
        known_ids.pop(idx)
        known_names.pop(idx)
        known_encodings.pop(idx)

    return jsonify({"success": True, "message": f"Customer {customer_id} deleted."})


# =============================================================
# ADMIN API — Unknown Customers
# GET    /api/admin/unknown-customers         — paginated + search
# DELETE /api/admin/unknown-customers/<id>    — delete one
# DELETE /api/admin/unknown-customers         — delete all
# =============================================================

@app.route("/api/admin/unknown-customers", methods=["GET"])
def admin_list_unknown():
    """
    Query params: search (matches id), sort, order, page, per_page
    """
    search   = request.args.get("search", "").strip()
    sort_col = request.args.get("sort",     "id")
    order    = request.args.get("order",    "desc").lower()
    page     = int(request.args.get("page",     1))
    per_page = int(request.args.get("per_page", 20))

    allowed_sort = {"id", "visit_count", "first_seen", "last_seen"}
    if sort_col not in allowed_sort:
        sort_col = "id"
    direction = "DESC" if order == "desc" else "ASC"

    try:
        conn = get_connection()
        cur  = conn.cursor()

        if search:
            cur.execute(
                f"""
                SELECT id, visit_count, first_seen, last_seen
                FROM unknown_customers
                WHERE id::text ILIKE %s
                ORDER BY {sort_col} {direction}
                """,
                (f"%{search}%",),
            )
        else:
            cur.execute(
                f"""
                SELECT id, visit_count, first_seen, last_seen
                FROM unknown_customers
                ORDER BY {sort_col} {direction}
                """
            )

        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    items = [
        {
            "id":          r[0],
            "visit_count": r[1],
            "first_seen":  r[2].strftime("%Y-%m-%d %H:%M") if r[2] else "",
            "last_seen":   r[3].strftime("%Y-%m-%d %H:%M") if r[3] else "",
        }
        for r in rows
    ]

    return jsonify({"success": True, **_paginate(items, page, per_page)})


@app.route("/api/admin/unknown-customers/<int:unknown_id>", methods=["DELETE"])
def admin_delete_unknown(unknown_id):
    """Delete one unknown customer and their visit logs; evict from cache."""
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "DELETE FROM visit_logs "
            "WHERE customer_type IN ('unknown','returning_unknown') AND customer_id = %s",
            (unknown_id,),
        )
        cur.execute("DELETE FROM unknown_customers WHERE id = %s", (unknown_id,))
        affected = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    if affected == 0:
        return jsonify({"success": False, "message": "Unknown customer not found."}), 404

    # Evict from RAM
    global unknown_ids, unknown_encodings
    if unknown_id in unknown_ids:
        idx = unknown_ids.index(unknown_id)
        unknown_ids.pop(idx)
        unknown_encodings.pop(idx)

    return jsonify({"success": True, "message": f"Unknown customer {unknown_id} deleted."})


@app.route("/api/admin/unknown-customers", methods=["DELETE"])
def admin_delete_all_unknown():
    """Delete ALL unknown customers and their visit logs; clear cache."""
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            "DELETE FROM visit_logs WHERE customer_type IN ('unknown','returning_unknown')"
        )
        cur.execute("DELETE FROM unknown_customers")
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    # Clear RAM cache for unknowns
    global unknown_ids, unknown_encodings
    unknown_ids       = []
    unknown_encodings = []

    return jsonify({"success": True, "message": f"Deleted {deleted} unknown customer(s)."})


# =============================================================
# ADMIN API — Visit Logs
# GET    /api/admin/visit-logs             — paginated, filterable
# DELETE /api/admin/visit-logs/delete-old  — remove logs older than N days
# =============================================================

@app.route("/api/admin/visit-logs", methods=["GET"])
def admin_list_logs():
    """
    Query params:
      type      — known | unknown | returning_unknown | '' (all)
      date_from — YYYY-MM-DD
      date_to   — YYYY-MM-DD
      search    — substring on customer_id or resolved name
      page, per_page
    """
    filter_type = request.args.get("type",      "").strip()
    date_from   = request.args.get("date_from", "").strip()
    date_to     = request.args.get("date_to",   "").strip()
    search      = request.args.get("search",    "").strip()
    page        = int(request.args.get("page",     1))
    per_page    = int(request.args.get("per_page", 30))

    conditions = []
    params     = []

    if filter_type in ("known", "unknown", "returning_unknown"):
        conditions.append("vl.customer_type = %s")
        params.append(filter_type)

    if date_from:
        conditions.append("vl.visit_time >= %s")
        params.append(date_from)

    if date_to:
        conditions.append("vl.visit_time <= %s")
        params.append(date_to + " 23:59:59")

    if search:
        conditions.append(
            "(vl.customer_id::text ILIKE %s OR c.name ILIKE %s)"
        )
        params += [f"%{search}%", f"%{search}%"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            f"""
            SELECT
                vl.id,
                vl.customer_type,
                vl.customer_id,
                vl.visit_time,
                COALESCE(c.name, 'Unknown #' || vl.customer_id::text) AS display_name
            FROM visit_logs vl
            LEFT JOIN customers c
                ON vl.customer_type = 'known' AND c.id = vl.customer_id
            {where}
            ORDER BY vl.id DESC
            """,
            params,
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    items = [
        {
            "id":            r[0],
            "customer_type": r[1],
            "customer_id":   r[2],
            "visit_time":    r[3].strftime("%Y-%m-%d %H:%M:%S") if r[3] else "",
            "name":          r[4],
        }
        for r in rows
    ]

    return jsonify({"success": True, **_paginate(items, page, per_page)})


@app.route("/api/admin/visit-logs/delete-old", methods=["DELETE"])
def admin_delete_old_logs():
    """
    Delete visit logs older than `days` days.
    JSON body: { days: int }
    """
    data = request.json or {}
    try:
        days = int(data.get("days", SETTINGS["auto_delete_logs_days"]))
    except (ValueError, TypeError):
        return jsonify({"success": False, "message": "Invalid days value."}), 400

    cutoff = datetime.now() - timedelta(days=days)

    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("DELETE FROM visit_logs WHERE visit_time < %s", (cutoff,))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({"success": True, "message": f"Deleted {deleted} log(s) older than {days} day(s)."})


# =============================================================
# ADMIN API — Database Overview
# GET /api/admin/database-overview
# =============================================================

@app.route("/api/admin/database-overview", methods=["GET"])
def admin_database_overview():
    """Return table counts, today's stats, and in-memory cache sizes."""
    today = datetime.now().date().isoformat()

    try:
        conn = get_connection()
        cur  = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM customers")
        total_customers = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM unknown_customers")
        total_unknown = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM visit_logs")
        total_logs = cur.fetchone()[0]

        cur.execute(
            "SELECT known_today, unknown_today, returning_unknown_today "
            "FROM daily_statistics WHERE stat_date = %s",
            (today,),
        )
        today_row = cur.fetchone()

        # PostgreSQL database size
        cur.execute("SELECT pg_size_pretty(pg_database_size(current_database()))")
        db_size = cur.fetchone()[0]

        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    return jsonify({
        "success":           True,
        "total_customers":   total_customers,
        "total_unknown":     total_unknown,
        "total_logs":        total_logs,
        "known_today":       today_row[0] if today_row else 0,
        "unknown_today":     today_row[1] if today_row else 0,
        "returning_today":   today_row[2] if today_row else 0,
        "db_size":           db_size,
        "cache_known":       len(known_ids),
        "cache_unknown":     len(unknown_ids),
    })


@app.route("/api/admin/cache/refresh", methods=["POST"])
def admin_refresh_cache():
    """Reload both face caches from PostgreSQL."""
    try:
        refresh_face_cache()
        return jsonify({
            "success": True,
            "message": "Face cache refreshed.",
            "cache_known":   len(known_ids),
            "cache_unknown": len(unknown_ids),
        })
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.route("/api/admin/settings/reset-defaults", methods=["POST"])
def admin_reset_settings_defaults():
    """
    Write _SETTINGS_DEFAULTS back to PostgreSQL and reload in memory.
    """
    d = _SETTINGS_DEFAULTS
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(
            """
            UPDATE system_settings SET
                new_face_delay           = %s,
                cooldown_seconds         = %s,
                pending_expire_seconds   = %s,
                known_threshold          = %s,
                unknown_threshold        = %s,
                dashboard_refresh_seconds = %s,
                auto_delete_logs_days    = %s,
                updated_at               = NOW()
            WHERE id = 1
            """,
            (
                d["new_face_delay"],
                d["cooldown_seconds"],
                d["pending_expire_seconds"],
                d["known_threshold"],
                d["unknown_threshold"],
                d["dashboard_refresh_seconds"],
                d["auto_delete_logs_days"],
            ),
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500

    reload_system_settings()
    return jsonify({"success": True, "message": "Settings reset to defaults.", "settings": SETTINGS})


# =============================================================
# ADMIN API — System Information
# GET /api/admin/system-info
# =============================================================

@app.route("/api/admin/system-info", methods=["GET"])
def admin_system_info():
    """
    Return runtime environment details — versions, uptime, statuses.
    All lookups are try/except guarded so a missing library never crashes.
    """
    import sys
    import flask
    import psycopg

    # Python version
    py_version = sys.version.split(" ")[0]

    # Library versions
    flask_version   = flask.__version__
    cv2_version     = cv2.__version__
    numpy_version   = np.__version__

    try:
        import face_recognition as _fr
        fr_version = getattr(_fr, "__version__", "installed")
    except Exception:
        fr_version = "unknown"

    # PostgreSQL version
    pg_version = "unknown"
    db_status  = "error"
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT version()")
        pg_version = cur.fetchone()[0].split(",")[0]   # e.g. "PostgreSQL 15.3 …"
        cur.close()
        conn.close()
        db_status = "connected"
    except Exception as exc:
        pg_version = str(exc)

    # Uptime
    uptime_delta   = datetime.now() - APP_START_TIME
    total_seconds  = int(uptime_delta.total_seconds())
    hours, rem     = divmod(total_seconds, 3600)
    minutes, secs  = divmod(rem, 60)
    uptime_str     = f"{hours}h {minutes}m {secs}s"

    # Camera status
    cam_status = "active" if camera is not None and camera.isOpened() else "inactive"

    # Recognition cache
    cache_status = f"{len(known_ids)} known, {len(unknown_ids)} unknown loaded"

    return jsonify({
        "success":        True,
        "python":         py_version,
        "flask":          flask_version,
        "opencv":         cv2_version,
        "numpy":          numpy_version,
        "face_recognition": fr_version,
        "postgresql":     pg_version,
        "uptime":         uptime_str,
        "app_start":      APP_START_TIME.strftime("%Y-%m-%d %H:%M:%S"),
        "db_status":      db_status,
        "camera_status":  cam_status,
        "cache_status":   cache_status,
        "cache_known":    len(known_ids),
        "cache_unknown":  len(unknown_ids),
    })


# =============================================================
# ENTRY POINT
# =============================================================

if __name__ == "__main__":

    # Clean up stale logs on startup
    delete_old_logs()

    # Load all faces into RAM before accepting requests
    refresh_face_cache()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=os.environ.get("FLASK_DEBUG", "true").lower() == "true",
    )



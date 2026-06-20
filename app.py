import base64
import cv2
from flask import Flask, render_template, request
import sqlite3
import face_recognition
import numpy as np
import json 
import requests
from sync_faces import sync_staff_faces
from flask import Flask, render_template, request, Response
from datetime import datetime, timedelta
last_seen = {}
last_yellow_seen = {}
last_red_seen = {}
attendance_marked = {}
COUNT_INTERVAL = 10
last_unknown_seen = None
camera = cv2.VideoCapture(0)

app = Flask(__name__)
@app.route('/register-page')
def register_page():
    return render_template("register.html")

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/register-camera', methods=['POST'])
def register_camera():

    data = request.json

    name = data["name"]
    email = data["email"]

    image_data = data["image"]

    image_data = image_data.split(",")[1]

    image_bytes = base64.b64decode(image_data)

    with open("temp.jpg", "wb") as f:
        f.write(image_bytes)

    image = face_recognition.load_image_file("temp.jpg")

    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        return "No face detected"

    encoding = encodings[0]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO users(name,email,face_encoding)
        VALUES(?,?,?)
        """,
        (
            name,
            email,
            json.dumps(encoding.tolist())
        )
    )

    conn.commit()
    conn.close()

    return "User Registered Successfully"

@app.route('/scan', methods=['POST'])
def scan():

    image_file = request.files['image']

    image = face_recognition.load_image_file(image_file)

    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        return "No face detected"

    uploaded_encoding = encodings[0]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT id,name,email,face_encoding FROM users"
    )

    users = cur.fetchall()

    conn.close()

    for user in users:

        stored_encoding = np.array(
            json.loads(user[3])
        )

        distance = face_recognition.face_distance(
            [stored_encoding],
            uploaded_encoding
        )[0]

        print("Checking:", user[1])
        print("Distance:", distance)

        if distance < 0.60:

            return f"""
            <h1>{user[1]}</h1>
            <p>ID: {user[0]}</p>
            <p>Email: {user[2]}</p>
            """
    return "User Not Found"

@app.route('/dashboard-data')
def dashboard_data():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("SELECT name, visit_count FROM users")
    users = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT SUM(visit_count) FROM users")
    total_visits = cur.fetchone()[0] or 0

    cur.execute("SELECT unknown_count FROM stats WHERE id = 1")
    unknown_count = cur.fetchone()[0]

    cur.execute("""
        SELECT user_name, status, visit_time
        FROM visitor_logs
        ORDER BY id DESC
        LIMIT 10
    """)
    logs = cur.fetchall()

    conn.close()

    return {
        "users": users,
        "logs": logs,
        "total_users": total_users,
        "total_visits": total_visits,
        "unknown_count": unknown_count
    }


@app.route('/scan-camera', methods=['POST'])
def scan_camera():
    data = request.json

    image_data = data["image"]
    image_data = image_data.split(",")[1]

    image_bytes = base64.b64decode(image_data)

    with open("temp_scan.jpg", "wb") as f:
        f.write(image_bytes)

    image = face_recognition.load_image_file("temp_scan.jpg")

    encodings = face_recognition.face_encodings(image)

    if len(encodings) == 0:
        return "No face detected"

    uploaded_encoding = encodings[0]

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute(
    "SELECT id,name,email,face_encoding FROM users"
    )

    users = cur.fetchall()

    conn.close()

    for user in users:

        stored_encoding = np.array(
            json.loads(user[3])
        )

        distance = face_recognition.face_distance(
            [stored_encoding],
            uploaded_encoding
        )[0]

        print("Checking:", user[1])
        print("Distance:", distance)
        
        if distance < 0.60:

            conn_log = sqlite3.connect("database.db")
            cur_log = conn_log.cursor()

            from datetime import datetime

            current_time = datetime.now()

            should_count = False

            if user[1] not in last_seen:

                should_count = True

            else:

                difference = (
                    current_time - last_seen[user[1]]
                ).total_seconds()

                print("Difference =", difference)

                if difference > COUNT_INTERVAL:   # testing
                    should_count = True

                    print("Should Count After =", should_count)

            if should_count:
                last_seen[user[1]] = current_time

                cur_log.execute(
                    """
                    INSERT INTO visitor_logs(user_name,status)
                    VALUES(?,?)
                    """,
                    (user[1], "KNOWN")
                )

                cur_log.execute(
                    """
                    UPDATE users
                    SET visit_count = visit_count + 1
                    WHERE id = ?
                    """,
                    (user[0],)
             )

                conn_log.commit()

            cur_log.execute(
              """
             SELECT visit_count
                FROM users
                WHERE id = ?
                """,
                (user[0],)
            )

            count = cur_log.fetchone()[0]

            conn_log.close()

            return f"""
        <h1>{user[1]}</h1>
        <p>ID: {user[0]}</p>
        <p>Email: {user[2]}</p>
        <p>Visit Count: {count}</p>
        """

    from datetime import datetime

    global last_unknown_seen








    # CHECK PREVIOUSLY SEEN UNKNOWN USERS

    conn_unknown = sqlite3.connect("database.db")
    cur_unknown = conn_unknown.cursor()

    cur_unknown.execute("""
    SELECT id, face_encoding, visit_count
    FROM unknown_faces
    """)

    unknown_faces = cur_unknown.fetchall()

    for unknown_user in unknown_faces:

        stored_unknown_encoding = np.array(
            json.loads(unknown_user[1])
        )

        distance = face_recognition.face_distance(
            [stored_unknown_encoding],
            uploaded_encoding
        )[0]

        if distance < 0.60:

            cur_unknown.execute("""
            UPDATE unknown_faces
            SET visit_count = visit_count + 1,
                last_seen = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (unknown_user[0],)
            )

            conn_unknown.commit()

            count = unknown_user[2] + 1

            conn_unknown.close()

            return f"""
            <h1 style='color:orange'>
            Previously Seen Unknown User
            </h1>

            <p>Visit Count: {count}</p>
            """

    conn_unknown.close()
    current_time = datetime.now()

    should_count_unknown = False

    if last_unknown_seen is None:

        should_count_unknown = True

    else:

        difference = (
            current_time - last_unknown_seen
        ).total_seconds()

        if difference > COUNT_INTERVAL:
            should_count_unknown = True

    if should_count_unknown:

        conn_unknown_new = sqlite3.connect("database.db")
        cur_unknown_new = conn_unknown_new.cursor()

        cur_unknown_new.execute(
        """
        INSERT INTO unknown_faces(face_encoding)
        VALUES(?)
        """,
        (
            json.dumps(
                uploaded_encoding.tolist()
            ),
        ))

        conn_unknown_new.commit()
        conn_unknown_new.close()

        last_unknown_seen = current_time

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute(
        """
        UPDATE stats
        SET unknown_count = unknown_count + 1
        WHERE id = 1
        """
        )

        conn.commit()

        cur.execute(
        """
        SELECT unknown_count
        FROM stats
        WHERE id = 1
        """
        )

        unknown_count = cur.fetchone()[0]

        conn.close()

        return f"""
        <h1 style='color:red'>
        New Unknown User
        </h1>

        <p>Unknown Count: {unknown_count}</p>
        """
    return "Unknown User"


@app.route('/debug-db')
def debug_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # Check users table
    cur.execute("SELECT id, name, email, visit_count FROM users")
    users = cur.fetchall()

    # Check stats table
    cur.execute("SELECT * FROM stats")
    stats = cur.fetchall()

    conn.close()

    return f"""
    <h2>Users Table</h2>
    <pre>{users}</pre>
    <h2>Stats Table</h2>
    <pre>{stats}</pre>
    """


@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # Registered users
    cur.execute("SELECT name, visit_count FROM users")
    users = cur.fetchall()

    # Totals
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]

    cur.execute("SELECT SUM(visit_count) FROM users")
    total_visits = cur.fetchone()[0] or 0

    cur.execute("SELECT unknown_count FROM stats WHERE id = 1")
    unknown_count = cur.fetchone()[0]

    # Highest visit count
    cur.execute("SELECT MAX(visit_count) FROM users")
    max_visits = cur.fetchone()[0] or 0

    # Recent activity logs (last 10 entries)
    cur.execute("""
        SELECT user_name, status, visit_time
        FROM visitor_logs
        ORDER BY id DESC
        LIMIT 10
    """)
    logs = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        users=users,
        logs=logs,
        total_users=total_users,
        total_visits=total_visits,
        unknown_count=unknown_count,
        max_visits=max_visits
    )





def gen_frames():
    global camera

    while True:

        # camera released while registering
        if camera is None:
            continue

        success, frame = camera.read()

        if not success:
            break

        # Convert frame to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(
            rgb_frame,
            face_locations
        )

        # Load known users
        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute(
            """
            SELECT
            staff_id,
            staff_code,
            name,
            face_encoding
            FROM staff_faces
            """
        )

        users = cur.fetchall()

        conn.close()

        known_encodings = [
            np.array(json.loads(u[3]))
            for u in users
        ]

        known_names = [u[2] for u in users]

        known_staff_codes = [u[1] for u in users]

        known_ids = [u[0] for u in users]

        for (top, right, bottom, left), face_encoding in zip(
            face_locations,
            face_encodings
        ):

            name = "Unknown"
            color = (0, 0, 255)

            if len(known_encodings) > 0:

                matches = face_recognition.compare_faces(
                    known_encodings,
                    face_encoding
                )

                face_distances = face_recognition.face_distance(
                    known_encodings,
                    face_encoding
                )

                best_match_index = np.argmin(face_distances)
                print("Matched:", known_names[best_match_index])
                print("Distance:", face_distances[best_match_index])

                if face_distances[best_match_index] < 0.45:
                    print("GREEN MATCH FOUND")

                    name = (
                        f"{known_names[best_match_index]}"
                        f" ({known_staff_codes[best_match_index]})"
                    )

                    color = (0, 255, 0)

                    staff_id = known_ids[best_match_index]

                    current_time = datetime.now()

                    should_mark = False

                    if staff_id not in attendance_marked:

                        should_mark = True

                    else:

                        seconds = (
                            current_time -
                            attendance_marked[staff_id]
                        ).total_seconds()

                        if seconds > 60:
                            should_mark = True

                    if should_mark:

                        attendance_marked[staff_id] = current_time
                        print("Sending staff_id:", staff_id)
                        print("Sending name:", known_names[best_match_index])

                        response = requests.post(
                            "https://stafftally.com/api/face-attendance",
                            json={
                                "staff_id": staff_id,
                                "device_name": "Face Recognition Camera 1"
                            }
                        )
                        print("Status Code:", response.status_code)
                        print("URL:", response.url)
                        print("Attendance Response:")
                        print(response.text)
                    conn_log = sqlite3.connect("database.db")
                    cur_log = conn_log.cursor()

                    # cur_log.execute(
                    #     """
                    #     UPDATE users
                    #     SET visit_count = visit_count + 1
                    #     WHERE id = ?
                    #     """,
                    #     (known_ids[best_match_index],)
                    # )

                    # cur_log.execute(
                    #     """
                    #     INSERT INTO visitor_logs(user_name,status)
                    #     VALUES(?,?)
                    #     """,
                    #     (name, "KNOWN")
                    # )

                    conn_log.commit()
                    conn_log.close()

                else:

                    conn_unknown = sqlite3.connect("database.db")
                    cur_unknown = conn_unknown.cursor()

                    cur_unknown.execute("""
                        SELECT id, face_encoding
                        FROM unknown_faces
                    """)

                    unknown_faces = cur_unknown.fetchall()

                    found_unknown = False

                    for unknown_user in unknown_faces:

                        stored_encoding = np.array(
                            json.loads(unknown_user[1])
                        )

                        distance = face_recognition.face_distance(
                        [stored_encoding],
                        face_encoding
                        )[0]

                        if distance < 0.45:
                            print("YELLOW MATCH FOUND")

                            name = "YELLOW TEST"
                            color = (0, 215, 255)   #yellow

                            found_unknown = True
                            break

                    conn_unknown.close()

                    if not found_unknown:

                        name = "New Unknown"
                        color = (0, 0, 255)   # Red
                        conn_unknown_new = sqlite3.connect("database.db")
                        cur_unknown_new = conn_unknown_new.cursor()

                        cur_unknown_new.execute("""
                            INSERT INTO unknown_faces(face_encoding)
                            VALUES(?)
                                """,
                        (
                        json.dumps(
                            face_encoding.tolist()
                        ),
                        ))

                        conn_unknown_new.commit()
                        conn_unknown_new.close()

            cv2.rectangle(
                frame,
                (left, top),
                (right, bottom),
                color,
                2
            )

            cv2.putText(
                frame,
                name,
                (left, top - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )

        ret, buffer = cv2.imencode('.jpg', frame)

        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n'
            + frame +
            b'\r\n'
        )


@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')



@app.route('/pause-camera')
def pause_camera():
    global camera

    if camera is not None:
        camera.release()

    return "paused"


@app.route('/resume-camera')
def resume_camera():
    global camera

    camera = cv2.VideoCapture(0)

    return "resumed"




def delete_old_logs():

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cutoff_date = (
        datetime.now() - timedelta(days=3)
    ).strftime("%Y-%m-%d %H:%M:%S")

    print("Deleting logs before:", cutoff_date)

    cur.execute("""
    DELETE FROM visitor_logs
    WHERE visit_time < ?
    """, (cutoff_date,))

    print("Deleted Rows:", cur.rowcount)

    conn.commit()
    conn.close()



if __name__ == "__main__":

    delete_old_logs()

    print("Syncing Staff Faces...")
    sync_staff_faces()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )


import requests
import face_recognition
import sqlite3
import json
def sync_staff_faces():

    FACE_SYNC_URL = "https://stafftally.com/api/face-sync"

    response = requests.get(FACE_SYNC_URL)

    staff_list = response.json()["data"]

    known_faces = {}

    for staff in staff_list:

        print(f"\nProcessing: {staff['name']}")

        conn = sqlite3.connect("database.db")
        cur = conn.cursor()

        cur.execute(
            "SELECT staff_id FROM staff_faces WHERE staff_id = ?",
            (staff["staff_id"],)
        )

        existing_staff = cur.fetchone()

        conn.close()

        if existing_staff:

            print("ALREADY EXISTS - SKIPPED")
            continue

        image_response = requests.get(
            staff["photo_url"],
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        print("Status:", image_response.status_code)

        if image_response.status_code != 200:
            print("SKIPPED")
            continue

        image_path = f"temp_{staff['staff_id']}.jpg"

        with open(image_path, "wb") as f:
            f.write(image_response.content)

        try:

            image = face_recognition.load_image_file(
                image_path
            )

            encodings = face_recognition.face_encodings(
                image
            )

            if len(encodings) > 0:

                known_faces[staff["staff_id"]] = {
                    "name": staff["name"],
                    "staff_code": staff["staff_code"],
                    "encoding": encodings[0]
                }

                conn = sqlite3.connect("database.db")
                cur = conn.cursor()

                cur.execute("""
                INSERT OR REPLACE INTO staff_faces
                (
                    staff_id,
                    staff_code,
                    name,
                    face_encoding
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    staff["staff_id"],
                    staff["staff_code"],
                    staff["name"],
                    json.dumps(
                        encodings[0].tolist()
                    )
                ))

                conn.commit()
                conn.close()

                print("FACE FOUND AND SAVED")

            else:

                print("NO FACE FOUND")

        except Exception as e:

            print("ERROR:", e)

    print("\n====================")
    print("TOTAL FACES LOADED:", len(known_faces))
    print("====================")
if __name__ == "__main__":
    sync_staff_faces()
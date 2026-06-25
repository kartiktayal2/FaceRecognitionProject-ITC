import psycopg


DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "itc_face_recognition",
    "user": "postgres",
    "password": "Kartik@21"
}


def get_connection():
    return psycopg.connect(**DB_CONFIG)
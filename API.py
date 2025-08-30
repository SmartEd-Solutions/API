from flask import Flask, request, jsonify
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import requests
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

app = Flask(__name__)

# ----------------------
# Database config
# ----------------------
DB_CONFIG = {
    'host': os.getenv("DB_HOST"),
    'user': os.getenv("DB_USER"),
    'password': os.getenv("DB_PASSWORD"),
    'database': os.getenv("DB_NAME")
}

def get_db():
    return mysql.connector.connect(**DB_CONFIG)

def ok(data=None):
    return jsonify({'status': 'ok', 'data': data}), 200

def err(message, code=400):
    return jsonify({'status': 'error', 'message': message}), code

# ----------------------
# Hugging Face config
# ----------------------
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/deepset/tinyroberta-squad2"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}

def ask_huggingface(question, context):
    payload = {"question": question, "context": context}
    response = requests.post(HF_API_URL, headers=HEADERS, json=payload)
    return response.json()

# ----------------------
# QA route
# ----------------------
@app.route('/ask', methods=['POST'])
def ask_question():
    payload = request.json or {}
    question = payload.get("question")

    if not question:
        return err("Question is required")

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute("SELECT first_name, last_name, class FROM students LIMIT 5")
        students = cur.fetchall()

        cur.execute("SELECT first_name, last_name, subject FROM teachers LIMIT 5")
        teachers = cur.fetchall()

        cur.close()
        conn.close()

        context = "Students:\n"
        for s in students:
            context += f"{s['first_name']} {s['last_name']} in class {s['class']}\n"

        context += "\nTeachers:\n"
        for t in teachers:
            context += f"{t['first_name']} {t['last_name']} teaches {t['subject']}\n"

        hf_response = ask_huggingface(question, context)
        return ok(hf_response)

    except Error as e:
        return err(str(e), 500)

# ----------------------
# Existing routes (students & teachers)
# ----------------------
@app.route('/students', methods=['POST'])
def create_student():
    payload = request.json or {}
    first_name = payload.get('first_name')
    last_name = payload.get('last_name')
    student_class = payload.get('class')
    roll_no = payload.get('roll_no')

    if not (first_name and last_name and student_class):
        return err('first_name, last_name and class are required')

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
              "INSERT INTO students (first_name, last_name, class, roll_no) VALUES (%s,%s,%s,%s)",
            (first_name, last_name, student_class, roll_no)
        )
        conn.commit()
        student_id = cur.lastrowid
        cur.close()
        conn.close()
        return ok({'id': student_id})
    except Error as e:
        return err(str(e), 500)

@app.route('/students', methods=['GET'])
def list_students():
    cls = request.args.get('class')
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        if cls:
            cur.execute("SELECT * FROM students WHERE class=%s ORDER BY last_name, first_name", (cls,))
        else:
            cur.execute("SELECT * FROM students ORDER BY class, last_name, first_name")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        return ok(rows)
    except Error as e:
        return err(str(e), 500)

@app.route('/teachers', methods=['POST'])
def create_teacher():
    payload = request.json or {}
    fn = payload.get('first_name'); ln = payload.get('last_name'); subject = payload.get('subject')
    if not (fn and ln):
        return err('first_name and last_name required')
    try:
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO teachers (first_name, last_name, subject) VALUES (%s,%s,%s)", (fn,ln,subject))
        conn.commit()
        tid = cur.lastrowid
        cur.close(); conn.close()
        return ok({'id': tid})
    except Error as e:
        return err(str(e), 500)

# ----------------------
# Run server
# ----------------------
if __name__ == "__main__":
    app.run(debug=True)

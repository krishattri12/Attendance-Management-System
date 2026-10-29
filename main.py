"""
Attendance Management System
DBMS Project - Python + SQLite
Run:  python main.py
Default login -> username: admin   password: admin123
"""
import csv
import getpass
import hashlib
import os
import sqlite3
from datetime import date, datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "attendance.db")

SCHEMA = """-- ============================================================
-- Attendance Management System : Database Schema (SQLite)
-- ============================================================
PRAGMA foreign_keys = ON;

DROP VIEW  IF EXISTS v_attendance_summary;
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS enrollment;
DROP TABLE IF EXISTS course;
DROP TABLE IF EXISTS student;
DROP TABLE IF EXISTS teacher;
DROP TABLE IF EXISTS department;
DROP TABLE IF EXISTS admin;

CREATE TABLE admin (
    username      TEXT PRIMARY KEY,
    password_hash TEXT NOT NULL
);

CREATE TABLE department (
    dept_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    dept_name TEXT NOT NULL UNIQUE
);

CREATE TABLE teacher (
    teacher_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE,
    dept_id    INTEGER NOT NULL,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE RESTRICT
);

CREATE TABLE student (
    student_id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no    TEXT NOT NULL UNIQUE,
    name       TEXT NOT NULL,
    email      TEXT UNIQUE,
    semester   INTEGER NOT NULL CHECK (semester BETWEEN 1 AND 8),
    dept_id    INTEGER NOT NULL,
    FOREIGN KEY (dept_id) REFERENCES department(dept_id) ON DELETE RESTRICT
);

CREATE TABLE course (
    course_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    dept_id     INTEGER NOT NULL,
    teacher_id  INTEGER NOT NULL,
    FOREIGN KEY (dept_id)    REFERENCES department(dept_id),
    FOREIGN KEY (teacher_id) REFERENCES teacher(teacher_id)
);

-- Many-to-many: a student takes many courses, a course has many students
CREATE TABLE enrollment (
    student_id INTEGER NOT NULL,
    course_id  INTEGER NOT NULL,
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id)  REFERENCES course(course_id)   ON DELETE CASCADE
);

-- P = Present, A = Absent, L = Leave
CREATE TABLE attendance (
    attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id    INTEGER NOT NULL,
    course_id     INTEGER NOT NULL,
    att_date      TEXT NOT NULL,                       -- YYYY-MM-DD
    status        TEXT NOT NULL CHECK (status IN ('P','A','L')),
    UNIQUE (student_id, course_id, att_date),          -- no duplicate marking
    FOREIGN KEY (student_id, course_id)
        REFERENCES enrollment(student_id, course_id) ON DELETE CASCADE
);

CREATE INDEX idx_att_course_date ON attendance(course_id, att_date);

-- Prevent attendance for future dates
CREATE TRIGGER trg_no_future_attendance
BEFORE INSERT ON attendance
WHEN NEW.att_date > date('now')
BEGIN
    SELECT RAISE(ABORT, 'Cannot mark attendance for a future date');
END;

-- Summary view: percentage per student per course (Leave counts as present)
CREATE VIEW v_attendance_summary AS
SELECT s.student_id, s.roll_no, s.name AS student_name,
       c.course_id, c.course_code, c.course_name,
       COUNT(a.attendance_id)                                   AS total_classes,
       SUM(CASE WHEN a.status IN ('P','L') THEN 1 ELSE 0 END)   AS attended,
       ROUND(100.0 * SUM(CASE WHEN a.status IN ('P','L') THEN 1 ELSE 0 END)
             / NULLIF(COUNT(a.attendance_id),0), 2)             AS percentage
FROM enrollment e
JOIN student s ON s.student_id = e.student_id
JOIN course  c ON c.course_id  = e.course_id
LEFT JOIN attendance a ON a.student_id = e.student_id AND a.course_id = e.course_id
GROUP BY s.student_id, c.course_id;
"""
MIN_PERCENT = 75.0


# ---------------------------------------------------------------- helpers
def hash_pw(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def connect():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create all tables if they do not exist yet."""
    conn = connect()
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='admin'").fetchone()
    if not exists:
        conn.executescript(SCHEMA)
        conn.execute("INSERT INTO admin VALUES (?, ?)", ("admin", hash_pw("admin123")))
        conn.commit()
        print("Database created.")
    conn.close()


def print_table(rows, headers):
    if not rows:
        print("  (no records)")
        return
    data = [[str(r[h]) if r[h] is not None else "-" for h in headers] for r in rows]
    widths = [max(len(h), *(len(row[i]) for row in data)) for i, h in enumerate(headers)]
    line = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print(line)
    print("| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |")
    print(line)
    for row in data:
        print("| " + " | ".join(v.ljust(w) for v, w in zip(row, widths)) + " |")
    print(line)


def ask_date(prompt="Date (YYYY-MM-DD, blank = today): "):
    while True:
        s = input(prompt).strip()
        if not s:
            return date.today().isoformat()
        try:
            return datetime.strptime(s, "%Y-%m-%d").date().isoformat()
        except ValueError:
            print("  Invalid date format.")


def ask_int(prompt):
    while True:
        try:
            return int(input(prompt))
        except ValueError:
            print("  Enter a number.")


# ---------------------------------------------------------------- login
def login(conn):
    for _ in range(3):
        user = input("Username: ").strip()
        try:
            pw = getpass.getpass("Password: ")
        except Exception:
            pw = input("Password: ")
        row = conn.execute("SELECT 1 FROM admin WHERE username=? AND password_hash=?",
                           (user, hash_pw(pw))).fetchone()
        if row:
            return True
        print("  Wrong credentials.")
    return False


# ---------------------------------------------------------------- CRUD
def list_departments(conn):
    print_table(conn.execute("SELECT * FROM department").fetchall(), ["dept_id", "dept_name"])


def add_department(conn):
    name = input("Department name: ").strip()
    try:
        with conn:
            conn.execute("INSERT INTO department(dept_name) VALUES (?)", (name,))
        print("  Department added.")
    except sqlite3.IntegrityError as e:
        print("  Error:", e)


def list_teachers(conn):
    rows = conn.execute("""SELECT t.teacher_id, t.name, t.email, d.dept_name
                           FROM teacher t JOIN department d USING(dept_id)""").fetchall()
    print_table(rows, ["teacher_id", "name", "email", "dept_name"])


def add_teacher(conn):
    list_departments(conn)
    name = input("Teacher name: ").strip()
    email = input("Email: ").strip() or None
    dept = ask_int("Department id: ")
    try:
        with conn:
            conn.execute("INSERT INTO teacher(name,email,dept_id) VALUES (?,?,?)",
                         (name, email, dept))
        print("  Teacher added.")
    except sqlite3.IntegrityError as e:
        print("  Error:", e)


def list_students(conn):
    rows = conn.execute("""SELECT s.student_id, s.roll_no, s.name, s.semester, d.dept_name
                           FROM student s JOIN department d USING(dept_id)
                           ORDER BY s.roll_no""").fetchall()
    print_table(rows, ["student_id", "roll_no", "name", "semester", "dept_name"])


def add_student(conn):
    list_departments(conn)
    roll = input("Roll no: ").strip()
    name = input("Name: ").strip()
    email = input("Email: ").strip() or None
    sem = ask_int("Semester (1-8): ")
    dept = ask_int("Department id: ")
    try:
        with conn:
            conn.execute("INSERT INTO student(roll_no,name,email,semester,dept_id) VALUES (?,?,?,?,?)",
                         (roll, name, email, sem, dept))
        print("  Student added.")
    except sqlite3.IntegrityError as e:
        print("  Error:", e)


def update_student(conn):
    sid = ask_int("Student id to update: ")
    name = input("New name (blank = keep): ").strip()
    sem = input("New semester (blank = keep): ").strip()
    with conn:
        if name:
            conn.execute("UPDATE student SET name=? WHERE student_id=?", (name, sid))
        if sem.isdigit():
            conn.execute("UPDATE student SET semester=? WHERE student_id=?", (int(sem), sid))
    print("  Updated (if the id existed).")


def delete_student(conn):
    sid = ask_int("Student id to delete: ")
    if input("  This also deletes their attendance. Sure? (y/n): ").lower() == "y":
        with conn:
            cur = conn.execute("DELETE FROM student WHERE student_id=?", (sid,))
        print("  Deleted." if cur.rowcount else "  No such student.")


def list_courses(conn):
    rows = conn.execute("""SELECT c.course_id, c.course_code, c.course_name, t.name AS teacher
                           FROM course c JOIN teacher t USING(teacher_id)""").fetchall()
    print_table(rows, ["course_id", "course_code", "course_name", "teacher"])


def add_course(conn):
    list_departments(conn)
    list_teachers(conn)
    code = input("Course code: ").strip()
    name = input("Course name: ").strip()
    dept = ask_int("Department id: ")
    teacher = ask_int("Teacher id: ")
    try:
        with conn:
            conn.execute("INSERT INTO course(course_code,course_name,dept_id,teacher_id) VALUES (?,?,?,?)",
                         (code, name, dept, teacher))
        print("  Course added.")
    except sqlite3.IntegrityError as e:
        print("  Error:", e)


def enroll_student(conn):
    list_students(conn)
    list_courses(conn)
    sid = ask_int("Student id: ")
    cid = ask_int("Course id: ")
    try:
        with conn:
            conn.execute("INSERT INTO enrollment VALUES (?,?)", (sid, cid))
        print("  Enrolled.")
    except sqlite3.IntegrityError as e:
        print("  Error (already enrolled / invalid id):", e)


# ---------------------------------------------------------------- attendance
def mark_attendance(conn):
    list_courses(conn)
    cid = ask_int("Course id: ")
    day = ask_date()
    students = conn.execute("""SELECT s.student_id, s.roll_no, s.name
                               FROM enrollment e JOIN student s USING(student_id)
                               WHERE e.course_id=? ORDER BY s.roll_no""", (cid,)).fetchall()
    if not students:
        print("  No students enrolled in this course.")
        return
    print(f"\nMarking attendance for {day}.  P = Present, A = Absent, L = Leave (Enter = P)")
    records = []
    for s in students:
        while True:
            st = input(f"  {s['roll_no']:<10} {s['name']:<22}: ").strip().upper() or "P"
            if st in ("P", "A", "L"):
                break
            print("   Use P, A or L.")
        records.append((s["student_id"], cid, day, st))
    try:
        with conn:  # one transaction: all rows saved or none
            conn.executemany("""INSERT INTO attendance(student_id,course_id,att_date,status)
                                VALUES (?,?,?,?)""", records)
        print(f"  Attendance saved for {len(records)} students.")
    except sqlite3.IntegrityError as e:
        print("  Could not save (already marked for this date, or invalid):", e)
    except sqlite3.DatabaseError as e:
        print("  Could not save:", e)


def edit_attendance(conn):
    sid = ask_int("Student id: ")
    cid = ask_int("Course id: ")
    day = ask_date()
    st = input("New status (P/A/L): ").strip().upper()
    if st not in ("P", "A", "L"):
        print("  Invalid status.")
        return
    with conn:
        cur = conn.execute("""UPDATE attendance SET status=?
                              WHERE student_id=? AND course_id=? AND att_date=?""",
                           (st, sid, cid, day))
    print("  Updated." if cur.rowcount else "  No such record.")


# ---------------------------------------------------------------- reports
def student_report(conn):
    roll = input("Roll no: ").strip()
    rows = conn.execute("""SELECT course_code, course_name, total_classes, attended,
                                  COALESCE(percentage,0) AS percentage
                           FROM v_attendance_summary WHERE roll_no=?""", (roll,)).fetchall()
    print_table(rows, ["course_code", "course_name", "total_classes", "attended", "percentage"])
    for r in rows:
        if r["total_classes"] and r["percentage"] < MIN_PERCENT:
            print(f"  WARNING: shortage in {r['course_name']} ({r['percentage']}%)")


def course_report(conn):
    list_courses(conn)
    cid = ask_int("Course id: ")
    rows = conn.execute("""SELECT roll_no, student_name, total_classes, attended,
                                  COALESCE(percentage,0) AS percentage
                           FROM v_attendance_summary WHERE course_id=?
                           ORDER BY roll_no""", (cid,)).fetchall()
    print_table(rows, ["roll_no", "student_name", "total_classes", "attended", "percentage"])


def daily_report(conn):
    list_courses(conn)
    cid = ask_int("Course id: ")
    day = ask_date()
    rows = conn.execute("""SELECT s.roll_no, s.name, a.status
                           FROM attendance a JOIN student s USING(student_id)
                           WHERE a.course_id=? AND a.att_date=? ORDER BY s.roll_no""",
                        (cid, day)).fetchall()
    print_table(rows, ["roll_no", "name", "status"])


def defaulters(conn):
    rows = conn.execute("""SELECT roll_no, student_name, course_name, percentage
                           FROM v_attendance_summary
                           WHERE total_classes > 0 AND percentage < ?
                           ORDER BY percentage""", (MIN_PERCENT,)).fetchall()
    print(f"Students below {MIN_PERCENT}% attendance:")
    print_table(rows, ["roll_no", "student_name", "course_name", "percentage"])


def export_csv(conn):
    rows = conn.execute("SELECT * FROM v_attendance_summary").fetchall()
    fname = os.path.join(BASE_DIR, f"attendance_report_{date.today()}.csv")
    with open(fname, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(rows[0].keys() if rows else [])
        w.writerows([tuple(r) for r in rows])
    print(f"  Exported to {fname}")


def load_sample_data(conn):
    """Insert demo data so the project can be shown immediately."""
    try:
        with conn:
            conn.executescript("""
            INSERT INTO department(dept_name) VALUES ('Computer Science'),('Electronics');
            INSERT INTO teacher(name,email,dept_id) VALUES
              ('Dr. Sharma','sharma@college.edu',1),('Prof. Verma','verma@college.edu',1),
              ('Dr. Gupta','gupta@college.edu',2);
            INSERT INTO student(roll_no,name,email,semester,dept_id) VALUES
              ('CS101','Aman Singh','aman@mail.com',3,1),('CS102','Riya Patel','riya@mail.com',3,1),
              ('CS103','Karan Mehta','karan@mail.com',3,1),('EC201','Neha Joshi','neha@mail.com',3,2);
            INSERT INTO course(course_code,course_name,dept_id,teacher_id) VALUES
              ('CS301','Database Systems',1,1),('CS302','Operating Systems',1,2),
              ('EC301','Digital Electronics',2,3);
            INSERT INTO enrollment VALUES (1,1),(2,1),(3,1),(1,2),(2,2),(3,2),(4,3);
            INSERT INTO attendance(student_id,course_id,att_date,status) VALUES
              (1,1,'2025-01-06','P'),(2,1,'2025-01-06','P'),(3,1,'2025-01-06','A'),
              (1,1,'2025-01-07','P'),(2,1,'2025-01-07','A'),(3,1,'2025-01-07','A'),
              (1,1,'2025-01-08','P'),(2,1,'2025-01-08','P'),(3,1,'2025-01-08','L'),
              (1,2,'2025-01-06','P'),(2,2,'2025-01-06','P'),(3,2,'2025-01-06','A'),
              (4,3,'2025-01-06','P'),(4,3,'2025-01-07','P');
            """)
        print("  Sample data loaded.")
    except sqlite3.IntegrityError:
        print("  Sample data already present.")


# ---------------------------------------------------------------- menu
MENU = {
    "1": ("Add department", add_department),
    "2": ("Add teacher", add_teacher),
    "3": ("Add student", add_student),
    "4": ("Add course", add_course),
    "5": ("Enroll student in course", enroll_student),
    "6": ("Mark attendance", mark_attendance),
    "7": ("Edit an attendance record", edit_attendance),
    "8": ("Student-wise report", student_report),
    "9": ("Course-wise report", course_report),
    "10": ("Daily report", daily_report),
    "11": ("Defaulters list (<75%)", defaulters),
    "12": ("Export report to CSV", export_csv),
    "13": ("View all students", list_students),
    "14": ("Update student", update_student),
    "15": ("Delete student", delete_student),
    "16": ("Load sample data", load_sample_data),
}


def main():
    init_db()
    conn = connect()
    print("=== ATTENDANCE MANAGEMENT SYSTEM ===")
    if not login(conn):
        print("Too many failed attempts.")
        return
    while True:
        print("\n----- MENU -----")
        for k, (label, _) in MENU.items():
            print(f"{k:>3}. {label}")
        print("  0. Exit")
        choice = input("Choice: ").strip()
        if choice == "0":
            break
        if choice in MENU:
            print()
            MENU[choice][1](conn)
        else:
            print("Invalid choice.")
    conn.close()
    print("Goodbye!")


if __name__ == "__main__":
    main()

-- ============================================================
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

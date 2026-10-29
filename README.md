# Attendance Management System (DBMS Project)

**Tech:** Python 3 + SQLite (`sqlite3` module, no installation needed)

## 1. Problem statement
Manual attendance registers are slow, error-prone and hard to analyse. This system stores
students, teachers, courses and daily attendance in a relational database and generates
reports such as attendance percentage and defaulter lists.

## 2. Objectives
- Store data in a structured, consistent database
- Mark / edit attendance course-wise and date-wise
- Calculate attendance percentage automatically
- Identify students below 75%
- Prevent duplicate or invalid entries using constraints

## 3. How to run
```
python main.py
```
Login: `admin` / `admin123`. Then choose option **16** to load sample data.
The database file `attendance.db` is created automatically from `schema.sql`.

## 4. ER diagram (text form)
```
DEPARTMENT 1 ---- N TEACHER
DEPARTMENT 1 ---- N STUDENT
DEPARTMENT 1 ---- N COURSE
TEACHER    1 ---- N COURSE        (a teacher teaches many courses)
STUDENT    M ---- N COURSE        (via ENROLLMENT)
ENROLLMENT 1 ---- N ATTENDANCE    (one row per student, course, date)
```

## 5. Tables
| Table | Primary key | Foreign keys | Notes |
|---|---|---|---|
| admin | username | - | password stored as SHA-256 hash |
| department | dept_id | - | dept_name UNIQUE |
| teacher | teacher_id | dept_id | |
| student | student_id | dept_id | roll_no UNIQUE, semester CHECK 1-8 |
| course | course_id | dept_id, teacher_id | course_code UNIQUE |
| enrollment | (student_id, course_id) | both | resolves the M:N relationship |
| attendance | attendance_id | (student_id, course_id) -> enrollment | UNIQUE(student, course, date), status CHECK P/A/L |

## 6. DBMS concepts used (for viva)
- **Primary / Foreign keys, ON DELETE CASCADE / RESTRICT** for referential integrity
- **Constraints:** NOT NULL, UNIQUE, CHECK, composite primary key
- **Normalization (3NF):** no repeating groups; teacher name is not repeated in course or
  attendance; the M:N relation is split into its own table.
- **Joins, GROUP BY, HAVING, subqueries, aggregate functions** (see `queries.sql`)
- **View:** `v_attendance_summary` computes percentage for reuse in reports
- **Trigger:** `trg_no_future_attendance` blocks future dates
- **Index:** `idx_att_course_date` speeds up course/date lookups
- **Transactions:** attendance for a whole class is saved atomically (all or nothing)
- **Parameterized queries (`?`)** prevent SQL injection

## 7. Features
Add department / teacher / student / course, enroll students, mark and edit attendance,
student-wise, course-wise and daily reports, defaulter list, CSV export, update/delete student, login.

## 8. Possible future scope
Web front-end (Flask), email alerts to defaulters, QR/face-based attendance, MySQL migration.

## 9. Files
- `schema.sql`  tables, view, trigger, index
- `main.py`     Python menu-driven application
- `queries.sql` sample SQL queries

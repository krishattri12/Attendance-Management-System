"""
Attendance Management System - Desktop GUI (Python Tkinter + SQLite)
Keep this file in the SAME folder as main.py (it re-uses its database code).
Run:  python gui.py        Login: admin / admin123
"""
import csv
import sqlite3
import tkinter as tk
from datetime import date, datetime, timedelta
from tkinter import filedialog, messagebox, ttk

import main as core

BG, CARD, SIDE = "#f4f6fb", "#ffffff", "#1f2a44"
ACCENT, TEXT, MUTED = "#3b6cf6", "#1c2333", "#6b7385"
OK, BAD, WARN, LINE = "#1a8f4c", "#d23a3a", "#b7791f", "#e1e4ea"
FONT = "Segoe UI"
MIN_PCT = core.MIN_PERCENT
LABEL = {"P": "Present", "A": "Absent", "L": "Leave"}


# ------------------------------------------------------------------ styling
def setup_style(root):
    s = ttk.Style(root)
    s.theme_use("clam")
    root.configure(bg=BG)
    s.configure(".", font=(FONT, 10), background=BG, foreground=TEXT)
    s.configure("TFrame", background=BG)
    s.configure("Card.TFrame", background=CARD)
    s.configure("TLabel", background=BG)
    s.configure("Card.TLabel", background=CARD)
    s.configure("Title.TLabel", font=(FONT, 20, "bold"))
    s.configure("Muted.TLabel", foreground=MUTED)
    s.configure("TButton", background="#e8ecf5", padding=(12, 6), borderwidth=0)
    s.map("TButton", background=[("active", "#d9dfee")])
    s.configure("Accent.TButton", background=ACCENT, foreground="white")
    s.map("Accent.TButton", background=[("active", "#2f58d0")])
    s.configure("Danger.TButton", background="#fbeaea", foreground=BAD)
    s.map("Danger.TButton", background=[("active", "#f6d5d5")])
    s.configure("TEntry", padding=5, fieldbackground="white")
    s.configure("TCombobox", padding=5, fieldbackground="white")
    s.configure("Treeview", rowheight=30, background="white", fieldbackground="white", borderwidth=0)
    s.configure("Treeview.Heading", font=(FONT, 10, "bold"), background="#e8ecf5", padding=6, relief="flat")
    s.map("Treeview", background=[("selected", "#dbe5ff")], foreground=[("selected", TEXT)])


def friendly(e):
    m = str(e)
    if "UNIQUE" in m:
        return "This value already exists (duplicate entry)."
    if "FOREIGN KEY" in m:
        return "This record is linked to other data, so the change is not allowed."
    if "CHECK" in m:
        return "One of the values is outside the allowed range."
    if "NOT NULL" in m:
        return "A required field is empty."
    return m


def make_tree(parent, cols, mode="browse"):
    box = tk.Frame(parent, bg=CARD, highlightthickness=1, highlightbackground=LINE)
    tree = ttk.Treeview(box, columns=[c[0] for c in cols], show="headings", selectmode=mode)
    for key, head, w in cols:
        tree.heading(key, text=head)
        tree.column(key, width=w, anchor="w", minwidth=50)
    sb = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    tree.tag_configure("odd", background="#f8f9fc")
    tree.tag_configure("good", foreground=OK)
    tree.tag_configure("bad", foreground=BAD)
    tree.tag_configure("P", foreground=OK)
    tree.tag_configure("A", foreground=BAD)
    tree.tag_configure("L", foreground=WARN)
    return box, tree


# ------------------------------------------------------------------ dialog
class Form(tk.Toplevel):
    """Generic popup form. fields = [(key, label, 'entry'|'combo', options, required)]"""

    def __init__(self, parent, title, fields, values, on_submit):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=CARD)
        self.resizable(False, False)
        self.on_submit, self.vars = on_submit, {}
        body = ttk.Frame(self, style="Card.TFrame", padding=22)
        body.pack()
        ttk.Label(body, text=title, style="Card.TLabel", font=(FONT, 14, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        first = None
        for r, (key, label, kind, opts, req) in enumerate(fields, start=1):
            ttk.Label(body, text=label + (" *" if req else ""), style="Card.TLabel").grid(
                row=r, column=0, sticky="w", pady=6, padx=(0, 16))
            var = tk.StringVar()
            cur = values.get(key)
            if kind == "combo":
                w = ttk.Combobox(body, textvariable=var, values=[o[1] for o in opts], state="readonly", width=32)
                for oid, lab in opts:
                    if oid == cur:
                        var.set(lab)
            else:
                w = ttk.Entry(body, textvariable=var, width=35)
                var.set("" if cur is None else str(cur))
            w.grid(row=r, column=1, pady=6)
            first = first or w
            self.vars[key] = (var, kind, opts, req, label)
        bar = ttk.Frame(body, style="Card.TFrame")
        bar.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(bar, text="Cancel", command=self.destroy).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="Save", style="Accent.TButton", command=self.submit).pack(side="left")
        self.bind("<Return>", lambda e: self.submit())
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(parent.winfo_toplevel())
        self.update_idletasks()
        p = parent.winfo_toplevel()
        x = p.winfo_rootx() + (p.winfo_width() - self.winfo_width()) // 2
        y = p.winfo_rooty() + (p.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.wait_visibility()
        self.grab_set()
        first.focus_set()

    def submit(self):
        out = {}
        for key, (var, kind, opts, req, label) in self.vars.items():
            raw = var.get().strip()
            if req and not raw:
                hint = " Create one first from its own page." if kind == "combo" and not opts else ""
                messagebox.showwarning("Missing value", f"Please fill in '{label}'.{hint}", parent=self)
                return
            if kind == "combo":
                out[key] = next((oid for oid, lab in opts if lab == raw), None)
            else:
                out[key] = raw
        err = self.on_submit(out)
        if err:
            messagebox.showerror("Could not save", err, parent=self)
        else:
            self.destroy()


# ------------------------------------------------------------------ pages
class Page(ttk.Frame):
    def __init__(self, app, title, subtitle=""):
        super().__init__(app.content, padding=(28, 22))
        self.app, self.conn = app, app.conn
        ttk.Label(self, text=title, style="Title.TLabel").pack(anchor="w")
        ttk.Label(self, text=subtitle, style="Muted.TLabel").pack(anchor="w", pady=(0, 14))

    def refresh(self):
        pass

    def opts(self, sql):
        return [(r[0], r[1]) for r in self.conn.execute(sql)]


class CrudPage(Page):
    cols, singular, allow_edit = [], "record", True

    def __init__(self, app, title, subtitle):
        super().__init__(app, title, subtitle)
        self.rows = {}
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Label(bar, text="Search:", style="Muted.TLabel").pack(side="left", padx=(0, 6))
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *a: self.refresh())
        ttk.Entry(bar, textvariable=self.q, width=30).pack(side="left")
        ttk.Button(bar, text="Delete", style="Danger.TButton", command=self.delete).pack(side="right", padx=(8, 0))
        if self.allow_edit:
            ttk.Button(bar, text="Edit", command=self.edit).pack(side="right", padx=(8, 0))
        ttk.Button(bar, text=f"+ Add {self.singular}", style="Accent.TButton", command=self.add).pack(side="right")
        box, self.tree = make_tree(self, self.cols)
        box.pack(fill="both", expand=True)
        self.count = ttk.Label(self, style="Muted.TLabel")
        self.count.pack(anchor="w", pady=(8, 0))
        if self.allow_edit:
            self.tree.bind("<Double-1>", lambda e: self.edit())
        self.tree.bind("<Delete>", lambda e: self.delete())

    # subclasses implement: fetch, fields, save, remove
    def refresh(self):
        rows = self.fetch(f"%{self.q.get().strip()}%")
        self.tree.delete(*self.tree.get_children())
        self.rows = {}
        for i, r in enumerate(rows):
            iid = str(r["id"])
            self.rows[iid] = r
            self.tree.insert("", "end", iid=iid, tags=("odd" if i % 2 else "",),
                             values=["" if r[k] is None else r[k] for k, _, _ in self.cols])
        self.count.config(text=f"{len(rows)} record(s)" if rows else "No records yet - click '+ Add' to create one.")

    def add(self):
        Form(self, f"Add {self.singular}", self.fields(), {}, lambda v: self.submit(v, None))

    def edit(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Select a row", "Click a row in the table first.", parent=self)
        Form(self, f"Edit {self.singular}", self.fields(), dict(self.rows[sel[0]]),
             lambda v: self.submit(v, sel[0]))

    def delete(self):
        sel = self.tree.selection()
        if not sel:
            return messagebox.showinfo("Select a row", "Click a row in the table first.", parent=self)
        if not messagebox.askyesno("Confirm delete", f"Delete this {self.singular}?\n"
                                   "Related attendance records may be removed too.", parent=self):
            return
        try:
            with self.conn:
                self.remove(sel[0])
        except sqlite3.Error as e:
            return messagebox.showerror("Cannot delete", friendly(e), parent=self)
        self.refresh()
        self.app.status(f"{self.singular.capitalize()} deleted")

    def submit(self, values, rid):
        try:
            with self.conn:
                self.save(values, rid)
        except sqlite3.Error as e:
            return friendly(e)
        self.refresh()
        self.app.status(f"{self.singular.capitalize()} saved")
        return None


class DepartmentsPage(CrudPage):
    cols, singular = [("dept_name", "Department", 400)], "department"

    def __init__(self, app):
        super().__init__(app, "Departments", "Academic departments")

    def fetch(self, like):
        return self.conn.execute("SELECT dept_id AS id, dept_name FROM department "
                                 "WHERE dept_name LIKE ? ORDER BY dept_name", (like,)).fetchall()

    def fields(self):
        return [("dept_name", "Department name", "entry", None, True)]

    def save(self, v, rid):
        if rid is None:
            self.conn.execute("INSERT INTO department(dept_name) VALUES (?)", (v["dept_name"],))
        else:
            self.conn.execute("UPDATE department SET dept_name=? WHERE dept_id=?", (v["dept_name"], int(rid)))

    def remove(self, rid):
        self.conn.execute("DELETE FROM department WHERE dept_id=?", (int(rid),))


class TeachersPage(CrudPage):
    cols = [("name", "Name", 220), ("email", "Email", 260), ("dept_name", "Department", 200)]
    singular = "teacher"

    def __init__(self, app):
        super().__init__(app, "Teachers", "Faculty members who teach courses")

    def fetch(self, like):
        return self.conn.execute("""SELECT t.teacher_id AS id, t.name, t.email, t.dept_id, d.dept_name
            FROM teacher t JOIN department d ON d.dept_id=t.dept_id
            WHERE t.name||' '||d.dept_name LIKE ? ORDER BY t.name""", (like,)).fetchall()

    def fields(self):
        return [("name", "Name", "entry", None, True), ("email", "Email", "entry", None, False),
                ("dept_id", "Department", "combo",
                 self.opts("SELECT dept_id, dept_name FROM department ORDER BY dept_name"), True)]

    def save(self, v, rid):
        args = (v["name"], v["email"] or None, v["dept_id"])
        if rid is None:
            self.conn.execute("INSERT INTO teacher(name,email,dept_id) VALUES (?,?,?)", args)
        else:
            self.conn.execute("UPDATE teacher SET name=?,email=?,dept_id=? WHERE teacher_id=?", args + (int(rid),))

    def remove(self, rid):
        self.conn.execute("DELETE FROM teacher WHERE teacher_id=?", (int(rid),))


class StudentsPage(CrudPage):
    cols = [("roll_no", "Roll no", 110), ("name", "Name", 220), ("email", "Email", 220),
            ("semester", "Sem", 60), ("dept_name", "Department", 180)]
    singular = "student"

    def __init__(self, app):
        super().__init__(app, "Students", "Add, edit and search students")

    def fetch(self, like):
        return self.conn.execute("""SELECT s.student_id AS id, s.roll_no, s.name, s.email, s.semester,
            s.dept_id, d.dept_name FROM student s JOIN department d ON d.dept_id=s.dept_id
            WHERE s.roll_no||' '||s.name||' '||d.dept_name LIKE ? ORDER BY s.roll_no""", (like,)).fetchall()

    def fields(self):
        return [("roll_no", "Roll no", "entry", None, True), ("name", "Name", "entry", None, True),
                ("email", "Email", "entry", None, False),
                ("semester", "Semester", "combo", [(i, str(i)) for i in range(1, 9)], True),
                ("dept_id", "Department", "combo",
                 self.opts("SELECT dept_id, dept_name FROM department ORDER BY dept_name"), True)]

    def save(self, v, rid):
        args = (v["roll_no"], v["name"], v["email"] or None, v["semester"], v["dept_id"])
        if rid is None:
            self.conn.execute("INSERT INTO student(roll_no,name,email,semester,dept_id) VALUES (?,?,?,?,?)", args)
        else:
            self.conn.execute("UPDATE student SET roll_no=?,name=?,email=?,semester=?,dept_id=? "
                              "WHERE student_id=?", args + (int(rid),))

    def remove(self, rid):
        self.conn.execute("DELETE FROM student WHERE student_id=?", (int(rid),))


class CoursesPage(CrudPage):
    cols = [("course_code", "Code", 100), ("course_name", "Course", 260),
            ("teacher", "Teacher", 200), ("dept_name", "Department", 190)]
    singular = "course"

    def __init__(self, app):
        super().__init__(app, "Courses", "Subjects, their teachers and departments")

    def fetch(self, like):
        return self.conn.execute("""SELECT c.course_id AS id, c.course_code, c.course_name, c.dept_id,
            c.teacher_id, d.dept_name, t.name AS teacher FROM course c
            JOIN department d ON d.dept_id=c.dept_id JOIN teacher t ON t.teacher_id=c.teacher_id
            WHERE c.course_code||' '||c.course_name||' '||t.name LIKE ? ORDER BY c.course_code""",
                                 (like,)).fetchall()

    def fields(self):
        return [("course_code", "Course code", "entry", None, True),
                ("course_name", "Course name", "entry", None, True),
                ("dept_id", "Department", "combo",
                 self.opts("SELECT dept_id, dept_name FROM department ORDER BY dept_name"), True),
                ("teacher_id", "Teacher", "combo",
                 self.opts("SELECT teacher_id, name FROM teacher ORDER BY name"), True)]

    def save(self, v, rid):
        args = (v["course_code"], v["course_name"], v["dept_id"], v["teacher_id"])
        if rid is None:
            self.conn.execute("INSERT INTO course(course_code,course_name,dept_id,teacher_id) VALUES (?,?,?,?)", args)
        else:
            self.conn.execute("UPDATE course SET course_code=?,course_name=?,dept_id=?,teacher_id=? "
                              "WHERE course_id=?", args + (int(rid),))

    def remove(self, rid):
        self.conn.execute("DELETE FROM course WHERE course_id=?", (int(rid),))


class EnrollmentPage(CrudPage):
    cols = [("roll_no", "Roll no", 110), ("name", "Student", 240),
            ("course_code", "Code", 100), ("course_name", "Course", 260)]
    singular, allow_edit = "enrollment", False

    def __init__(self, app):
        super().__init__(app, "Enrollment", "Which student attends which course")

    def fetch(self, like):
        return self.conn.execute("""SELECT e.student_id||'-'||e.course_id AS id, s.roll_no, s.name,
            c.course_code, c.course_name FROM enrollment e
            JOIN student s ON s.student_id=e.student_id JOIN course c ON c.course_id=e.course_id
            WHERE s.roll_no||' '||s.name||' '||c.course_code||' '||c.course_name LIKE ?
            ORDER BY c.course_code, s.roll_no""", (like,)).fetchall()

    def fields(self):
        return [("student_id", "Student", "combo",
                 self.opts("SELECT student_id, roll_no||' - '||name FROM student ORDER BY roll_no"), True),
                ("course_id", "Course", "combo",
                 self.opts("SELECT course_id, course_code||' - '||course_name FROM course ORDER BY course_code"), True)]

    def save(self, v, rid):
        self.conn.execute("INSERT INTO enrollment VALUES (?,?)", (v["student_id"], v["course_id"]))

    def remove(self, rid):
        s, c = rid.split("-")
        self.conn.execute("DELETE FROM enrollment WHERE student_id=? AND course_id=?", (int(s), int(c)))


class DashboardPage(Page):
    def __init__(self, app):
        super().__init__(app, "Dashboard", "Overview of attendance across all courses")
        ttk.Button(self, text="Load sample data", command=self.sample).pack(anchor="w", pady=(0, 12))
        self.cards = ttk.Frame(self)
        self.cards.pack(fill="x")
        lower = ttk.Frame(self)
        lower.pack(fill="both", expand=True, pady=(16, 0))
        lower.columnconfigure(0, weight=3, uniform="a")
        lower.columnconfigure(1, weight=2, uniform="a")
        lower.rowconfigure(0, weight=1)
        left = tk.Frame(lower, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        tk.Label(left, text="Attendance by course", bg=CARD, fg=TEXT, font=(FONT, 11, "bold")).pack(
            anchor="w", padx=16, pady=(14, 4))
        self.canvas = tk.Canvas(left, bg=CARD, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.canvas.bind("<Configure>", lambda e: self.draw())
        right = tk.Frame(lower, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        tk.Label(right, text="Needs attention", bg=CARD, fg=TEXT, font=(FONT, 11, "bold")).pack(
            anchor="w", padx=16, pady=(14, 8))
        box, self.tree = make_tree(right, [("s", "Student", 120), ("c", "Course", 120), ("p", "%", 50)])
        box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.bars = []

    def sample(self):
        n = self.conn.execute("SELECT (SELECT COUNT(*) FROM department)+(SELECT COUNT(*) FROM student)"
                              "+(SELECT COUNT(*) FROM course)").fetchone()[0]
        if n:
            return messagebox.showinfo("Database not empty",
                                       "Sample data can only be loaded into an empty database.", parent=self)
        core.load_sample_data(self.conn)
        self.refresh()
        self.app.status("Sample data loaded")

    def refresh(self):
        one = lambda sql: self.conn.execute(sql).fetchone()[0]
        students, courses = one("SELECT COUNT(*) FROM student"), one("SELECT COUNT(*) FROM course")
        classes = one("SELECT COUNT(*) FROM (SELECT DISTINCT course_id, att_date FROM attendance)")
        overall = one("SELECT 100.0*SUM(attended)/NULLIF(SUM(total_classes),0) FROM v_attendance_summary")
        short = self.conn.execute("""SELECT roll_no, student_name, course_name, percentage
            FROM v_attendance_summary WHERE total_classes>0 AND percentage<? ORDER BY percentage""",
                                  (MIN_PCT,)).fetchall()
        for w in self.cards.winfo_children():
            w.destroy()
        stats = [("Students", students, TEXT), ("Courses", courses, TEXT), ("Classes held", classes, TEXT),
                 ("Overall attendance", "-" if overall is None else f"{overall:.1f}%",
                  TEXT if overall is None else (OK if overall >= MIN_PCT else BAD)),
                 (f"Below {MIN_PCT:g}%", len(short), BAD if short else OK)]
        for i, (label, val, color) in enumerate(stats):
            self.cards.columnconfigure(i, weight=1, uniform="c")
            card = tk.Frame(self.cards, bg=CARD, highlightthickness=1, highlightbackground=LINE)
            card.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            tk.Label(card, text=val, bg=CARD, fg=color, font=(FONT, 22, "bold")).pack(anchor="w", padx=16, pady=(12, 0))
            tk.Label(card, text=label, bg=CARD, fg=MUTED).pack(anchor="w", padx=16, pady=(0, 12))
        self.bars = self.conn.execute("""SELECT course_name, 100.0*SUM(attended)/SUM(total_classes) AS pct
            FROM v_attendance_summary GROUP BY course_id HAVING SUM(total_classes)>0
            ORDER BY course_name""").fetchall()
        self.draw()
        self.tree.delete(*self.tree.get_children())
        for r in short[:12]:
            self.tree.insert("", "end", tags=("bad",), values=(r["student_name"], r["course_name"],
                                                               f"{r['percentage']:.0f}"))

    def draw(self):
        c = self.canvas
        c.delete("all")
        if not self.bars:
            c.create_text(4, 8, anchor="nw", fill=MUTED, font=(FONT, 10),
                          text="No attendance data yet.\nMark attendance to see course statistics.")
            return
        x0, x1 = 170, max(220, c.winfo_width() - 60)
        for i, b in enumerate(self.bars):
            y, pct, name = 10 + i * 44, b["pct"], b["course_name"]
            name = name if len(name) <= 22 else name[:21] + "…"
            c.create_text(0, y + 10, anchor="w", text=name, fill=TEXT, font=(FONT, 10))
            c.create_rectangle(x0, y, x1, y + 20, fill="#e8ecf5", outline="")
            c.create_rectangle(x0, y, x0 + (x1 - x0) * pct / 100, y + 20,
                               fill=OK if pct >= MIN_PCT else BAD, outline="")
            c.create_text(x1 + 8, y + 10, anchor="w", text=f"{pct:.0f}%", fill=TEXT, font=(FONT, 10, "bold"))


class MarkPage(Page):
    def __init__(self, app):
        super().__init__(app, "Mark Attendance", "Pick a course and date, set each student's status, then save")
        self.courses, self.status_of, self.loaded = [], {}, None
        top = tk.Frame(self, bg=CARD, highlightthickness=1, highlightbackground=LINE)
        top.pack(fill="x", pady=(0, 10))
        inner = ttk.Frame(top, style="Card.TFrame", padding=12)
        inner.pack(fill="x")
        ttk.Label(inner, text="Course", style="Card.TLabel").pack(side="left")
        self.course = tk.StringVar()
        self.cbox = ttk.Combobox(inner, textvariable=self.course, state="readonly", width=34)
        self.cbox.pack(side="left", padx=(8, 22))
        self.cbox.bind("<<ComboboxSelected>>", lambda e: self.load())
        ttk.Label(inner, text="Date", style="Card.TLabel").pack(side="left")
        ttk.Button(inner, text="◀", width=3, command=lambda: self.shift(-1)).pack(side="left", padx=(8, 2))
        self.date = tk.StringVar(value=date.today().isoformat())
        ent = ttk.Entry(inner, textvariable=self.date, width=12, justify="center")
        ent.pack(side="left")
        ent.bind("<Return>", lambda e: self.load())
        ent.bind("<FocusOut>", lambda e: self.load())
        ttk.Button(inner, text="▶", width=3, command=lambda: self.shift(1)).pack(side="left", padx=2)
        ttk.Button(inner, text="Today", command=lambda: self.shift(0)).pack(side="left", padx=(8, 0))
        self.info = ttk.Label(self, style="Muted.TLabel")
        self.info.pack(anchor="w", pady=(0, 6))
        box, self.tree = make_tree(self, [("roll", "Roll no", 120), ("name", "Student", 320), ("status", "Status", 140)],
                                   "extended")
        box.pack(fill="both", expand=True)
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(10, 0))
        for code, txt in (("P", "Present (P)"), ("A", "Absent (A)"), ("L", "Leave (L)")):
            ttk.Button(bar, text=txt, command=lambda c=code: self.set_status(c)).pack(side="left", padx=(0, 8))
        ttk.Button(bar, text="All present", command=self.all_present).pack(side="left")
        ttk.Button(bar, text="Save attendance", style="Accent.TButton", command=self.save).pack(side="right")
        self.summary = ttk.Label(bar, style="Muted.TLabel")
        self.summary.pack(side="right", padx=16)
        self.tree.bind("<Key>", lambda e: self.set_status(e.char.upper()) if e.char.upper() in LABEL else None)
        self.tree.bind("<Double-1>", self.cycle)

    def refresh(self):
        self.courses = self.opts("SELECT course_id, course_code||' - '||course_name FROM course ORDER BY course_code")
        self.cbox["values"] = [c[1] for c in self.courses]
        if self.course.get() not in [c[1] for c in self.courses]:
            self.course.set(self.courses[0][1] if self.courses else "")
        self.load(force=True)

    def course_id(self):
        return next((i for i, lab in self.courses if lab == self.course.get()), None)

    def get_date(self):
        try:
            return datetime.strptime(self.date.get().strip(), "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None

    def shift(self, days):
        d = self.get_date()
        base = datetime.strptime(d, "%Y-%m-%d").date() if d else date.today()
        self.date.set((base + timedelta(days=days) if days else date.today()).isoformat())
        self.load()

    def load(self, force=False):
        cid, d = self.course_id(), self.get_date()
        if not force and (cid, d) == self.loaded:
            return
        self.tree.delete(*self.tree.get_children())
        self.status_of, self.loaded = {}, None
        if cid is None:
            self.info.config(text="No courses yet. Add a course and enroll students first.")
            return self.update_summary()
        if d is None:
            self.info.config(text="Invalid date. Use the format YYYY-MM-DD.")
            return self.update_summary()
        rows = self.conn.execute("""SELECT s.student_id, s.roll_no, s.name, a.status FROM enrollment e
            JOIN student s ON s.student_id=e.student_id
            LEFT JOIN attendance a ON a.student_id=e.student_id AND a.course_id=e.course_id AND a.att_date=?
            WHERE e.course_id=? ORDER BY s.roll_no""", (d, cid)).fetchall()
        self.loaded = (cid, d)
        for r in rows:
            code, iid = r["status"] or "P", str(r["student_id"])
            self.status_of[iid] = code
            self.tree.insert("", "end", iid=iid, tags=(code,), values=(r["roll_no"], r["name"], LABEL[code]))
        if not rows:
            self.info.config(text="No students are enrolled in this course yet.")
        elif any(r["status"] for r in rows):
            self.info.config(text="Attendance already marked for this date. Saving will update it.")
        else:
            self.info.config(text="New sheet: everyone starts as Present. Select rows, or press P / A / L.")
        kids = self.tree.get_children()
        if kids:
            self.tree.selection_set(kids[0])
        self.update_summary()

    def update_summary(self):
        n = {k: list(self.status_of.values()).count(k) for k in LABEL}
        self.summary.config(text=f"Present {n['P']}  |  Absent {n['A']}  |  Leave {n['L']}")

    def set_status(self, code, items=None):
        items = items or self.tree.selection()
        for i in items:
            v = self.tree.item(i, "values")
            self.status_of[i] = code
            self.tree.item(i, values=(v[0], v[1], LABEL[code]), tags=(code,))
        if len(items) == 1:
            nxt = self.tree.next(items[0])
            if nxt:
                self.tree.selection_set(nxt)
                self.tree.see(nxt)
        self.update_summary()

    def all_present(self):
        self.set_status("P", self.tree.get_children())

    def cycle(self, event):
        i = self.tree.identify_row(event.y)
        if i:
            self.set_status({"P": "A", "A": "L", "L": "P"}[self.status_of[i]], [i])

    def save(self):
        cid, d = self.course_id(), self.get_date()
        if cid is None or d is None or not self.status_of:
            return messagebox.showwarning("Nothing to save", "Choose a course with enrolled students "
                                          "and a valid date.", parent=self)
        if d > date.today().isoformat():
            return messagebox.showerror("Invalid date", "Cannot mark attendance for a future date.", parent=self)
        try:
            with self.conn:
                self.conn.executemany("""INSERT INTO attendance(student_id,course_id,att_date,status)
                    VALUES (?,?,?,?) ON CONFLICT(student_id,course_id,att_date)
                    DO UPDATE SET status=excluded.status""",
                                      [(int(i), cid, d, st) for i, st in self.status_of.items()])
        except sqlite3.Error as e:
            return messagebox.showerror("Could not save", friendly(e), parent=self)
        self.info.config(text="Saved. You can reopen this date later to edit it.")
        self.app.status(f"Attendance saved for {len(self.status_of)} students on {d}")


class ReportsPage(Page):
    def __init__(self, app):
        super().__init__(app, "Reports", "Attendance percentage per student and course")
        self.courses, self.shown = [], []
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 10))
        self.course = tk.StringVar()
        self.cbox = ttk.Combobox(bar, textvariable=self.course, state="readonly", width=30)
        self.cbox.pack(side="left")
        self.cbox.bind("<<ComboboxSelected>>", lambda e: self.table())
        self.show = tk.StringVar(value="All students")
        sh = ttk.Combobox(bar, textvariable=self.show, state="readonly", width=22,
                          values=["All students", f"Defaulters only (<{MIN_PCT:g}%)"])
        sh.pack(side="left", padx=8)
        sh.bind("<<ComboboxSelected>>", lambda e: self.table())
        self.q = tk.StringVar()
        self.q.trace_add("write", lambda *a: self.table())
        ttk.Entry(bar, textvariable=self.q, width=20).pack(side="left")
        ttk.Label(bar, text="  search", style="Muted.TLabel").pack(side="left")
        ttk.Button(bar, text="Export CSV", style="Accent.TButton", command=self.export).pack(side="right")
        box, self.tree = make_tree(self, [("roll", "Roll no", 100), ("name", "Student", 200), ("course", "Course", 200),
                                          ("total", "Classes", 80), ("att", "Attended", 80),
                                          ("pct", "Percentage", 100), ("st", "Status", 120)])
        box.pack(fill="both", expand=True)
        self.count = ttk.Label(self, style="Muted.TLabel")
        self.count.pack(anchor="w", pady=(8, 0))

    def refresh(self):
        self.courses = [(None, "All courses")] + self.opts(
            "SELECT course_id, course_code||' - '||course_name FROM course ORDER BY course_code")
        self.cbox["values"] = [c[1] for c in self.courses]
        if self.course.get() not in [c[1] for c in self.courses]:
            self.course.set("All courses")
        self.table()

    def table(self):
        cid = next((i for i, lab in self.courses if lab == self.course.get()), None)
        rows = self.conn.execute("""SELECT roll_no, student_name, course_name, total_classes, attended, percentage
            FROM v_attendance_summary WHERE (? IS NULL OR course_id=?) AND roll_no||' '||student_name LIKE ?
            ORDER BY course_name, roll_no""", (cid, cid, f"%{self.q.get().strip()}%")).fetchall()
        if self.show.get().startswith("Defaulters"):
            rows = [r for r in rows if r["total_classes"] and r["percentage"] < MIN_PCT]
        self.tree.delete(*self.tree.get_children())
        self.shown, low = [], 0
        for i, r in enumerate(rows):
            p = r["percentage"]
            if p is None:
                pct, st, tag = "-", "No classes yet", ""
            elif p >= MIN_PCT:
                pct, st, tag = f"{p:.1f}%", "OK", "good"
            else:
                pct, st, tag, low = f"{p:.1f}%", "Shortage", "bad", low + 1
            vals = (r["roll_no"], r["student_name"], r["course_name"], r["total_classes"], r["attended"], pct, st)
            self.shown.append(vals)
            self.tree.insert("", "end", values=vals, tags=("odd" if i % 2 else "", tag))
        self.count.config(text=f"{len(rows)} record(s)  |  {low} below {MIN_PCT:g}%")

    def export(self):
        if not self.shown:
            return messagebox.showinfo("Nothing to export", "The table is empty.", parent=self)
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV file", "*.csv")],
                                            initialfile=f"attendance_report_{date.today()}.csv")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Roll no", "Student", "Course", "Classes", "Attended", "Percentage", "Status"])
                w.writerows(self.shown)
            self.app.status(f"Exported to {path}")


PAGES = [("Dashboard", DashboardPage), ("Students", StudentsPage), ("Courses", CoursesPage),
         ("Teachers", TeachersPage), ("Departments", DepartmentsPage), ("Enrollment", EnrollmentPage),
         ("Mark Attendance", MarkPage), ("Reports", ReportsPage)]


# ------------------------------------------------------------------ app shell
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Attendance Management System")
        self.geometry("1120x700")
        self.minsize(940, 580)
        core.init_db()
        self.conn = core.connect()
        setup_style(self)
        self.shell, self._reset = None, None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.show_login()

    def close(self):
        self.conn.close()
        self.destroy()

    def clear(self):
        if self.shell:
            self.shell.destroy()

    def show_login(self):
        self.clear()
        self.shell = root = tk.Frame(self, bg=SIDE)
        root.pack(fill="both", expand=True)
        card = tk.Frame(root, bg=CARD, padx=40, pady=32)
        card.place(relx=.5, rely=.5, anchor="center")
        tk.Label(card, text="Attendance Management", bg=CARD, fg=TEXT, font=(FONT, 18, "bold")).pack()
        tk.Label(card, text="Sign in to continue", bg=CARD, fg=MUTED).pack(pady=(2, 18))
        u, p = tk.StringVar(value="admin"), tk.StringVar()
        entries = {}
        for lab, var, mask in (("Username", u, ""), ("Password", p, "•")):
            tk.Label(card, text=lab, bg=CARD, fg=MUTED, anchor="w").pack(fill="x")
            entries[lab] = ttk.Entry(card, textvariable=var, show=mask, width=32)
            entries[lab].pack(pady=(2, 12))
        err = tk.Label(card, text="", bg=CARD, fg=BAD)
        err.pack()

        def go(*_):
            ok = self.conn.execute("SELECT 1 FROM admin WHERE username=? AND password_hash=?",
                                   (u.get().strip(), core.hash_pw(p.get()))).fetchone()
            if ok:
                self.unbind("<Return>")
                self.build_shell()
            else:
                err.config(text="Wrong username or password")
                p.set("")

        ttk.Button(card, text="Sign in", style="Accent.TButton", command=go).pack(fill="x", pady=(6, 0))
        tk.Label(card, text="Default login: admin / admin123", bg=CARD, fg=MUTED, font=(FONT, 9)).pack(pady=(12, 0))
        entries["Password"].focus_set()
        self.bind("<Return>", go)

    def build_shell(self):
        self.clear()
        self.shell = shell = tk.Frame(self, bg=BG)
        shell.pack(fill="both", expand=True)
        side = tk.Frame(shell, bg=SIDE, width=210)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        tk.Label(side, text="Attendance\nManager", bg=SIDE, fg="white", font=(FONT, 15, "bold"),
                 justify="left").pack(anchor="w", padx=20, pady=(24, 22))
        right = tk.Frame(shell, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        self.content = tk.Frame(right, bg=BG)
        self.content.pack(fill="both", expand=True)
        self.content.rowconfigure(0, weight=1)
        self.content.columnconfigure(0, weight=1)
        self.status_lbl = tk.Label(right, text="Ready", bg="#e8ecf5", fg=MUTED, anchor="w", padx=14, pady=5)
        self.status_lbl.pack(fill="x")
        self.pages, self.navbtns = {}, {}
        btn = dict(relief="flat", bd=0, anchor="w", font=(FONT, 11), padx=12, pady=9, cursor="hand2",
                   bg=SIDE, fg="#c9d2ea", activebackground="#2b3a5e", activeforeground="white")
        for name, cls in PAGES:
            page = cls(self)
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page
            b = tk.Button(side, text=name, command=lambda n=name: self.show(n), **btn)
            b.pack(fill="x", padx=10, pady=1)
            self.navbtns[name] = b
        tk.Button(side, text="Log out", command=self.show_login, **btn).pack(side="bottom", fill="x", padx=10, pady=14)
        self.show("Dashboard")

    def show(self, name):
        page = self.pages[name]
        page.refresh()
        page.tkraise()
        for n, b in self.navbtns.items():
            b.config(bg=ACCENT if n == name else SIDE, fg="white" if n == name else "#c9d2ea")

    def status(self, msg):
        self.status_lbl.config(text=msg)
        if self._reset:
            self.after_cancel(self._reset)
        self._reset = self.after(5000, lambda: self.status_lbl.config(text="Ready"))


if __name__ == "__main__":
    App().mainloop()

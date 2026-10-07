import os
import sqlite3
import uuid
from datetime import date, timedelta

from flask import Flask, abort, g, jsonify, render_template, request, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("LIBRARY_DB", os.path.join(BASE_DIR, "library.db"))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
LIBRARY_NAME = os.environ.get("LIBRARY_NAME", "College Central Library")
LOAN_DAYS = int(os.environ.get("LOAN_DAYS", 14))
MAX_BOOKS = int(os.environ.get("MAX_BOOKS_PER_STUDENT", 3))
FINE_PER_DAY = int(os.environ.get("FINE_PER_DAY", 2))
ALLOWED_PHOTO_EXT = {"png", "jpg", "jpeg", "webp", "gif"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id TEXT UNIQUE NOT NULL COLLATE NOCASE,
    name TEXT NOT NULL,
    roll_no TEXT COLLATE NOCASE,
    branch TEXT,
    year TEXT,
    email TEXT,
    phone TEXT,
    photo TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL COLLATE NOCASE,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT,
    total_copies INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL REFERENCES students(id),
    book_id INTEGER NOT NULL REFERENCES books(id),
    issue_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    return_date TEXT,
    fine INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_issues_active ON issues(return_date);
"""

BOOK_SELECT = """
SELECT b.*, b.total_copies - (
    SELECT COUNT(*) FROM issues i WHERE i.book_id = b.id AND i.return_date IS NULL
) AS available FROM books b
"""

ISSUE_SELECT = """
SELECT i.*, s.name AS student_name, s.card_id, s.roll_no,
       b.title AS book_title, b.code AS book_code, b.author AS book_author
FROM issues i
JOIN students s ON s.id = i.student_id
JOIN books b ON b.id = i.book_id
"""

SAMPLE_STUDENTS = [
    ("STU2024001", "Madhusudan Kumar", "22BTCS001", "Computer Science", "3rd", "madhusudan@example.com", "9876500001"),
    ("STU2024002", "Priya Sharma", "22BTEC014", "Electronics", "3rd", "priya@example.com", "9876500002"),
    ("STU2024003", "Rahul Verma", "23BTME021", "Mechanical", "2nd", "rahul@example.com", "9876500003"),
    ("STU2024004", "Ananya Singh", "24BTCS045", "Computer Science", "1st", "ananya@example.com", "9876500004"),
    ("STU2024005", "Arjun Patel", "21BTCE007", "Civil", "4th", "arjun@example.com", "9876500005"),
]

SAMPLE_BOOKS = [
    ("BK1001", "Introduction to Algorithms", "Cormen, Leiserson, Rivest, Stein", "Computer Science", 3),
    ("BK1002", "Operating System Concepts", "Silberschatz, Galvin, Gagne", "Computer Science", 2),
    ("BK1003", "Database System Concepts", "Silberschatz, Korth, Sudarshan", "Computer Science", 2),
    ("BK1004", "Computer Networks", "Andrew S. Tanenbaum", "Computer Science", 2),
    ("BK1005", "Higher Engineering Mathematics", "B. S. Grewal", "Mathematics", 4),
    ("BK1006", "Engineering Mechanics", "R. C. Hibbeler", "Mechanical", 2),
    ("BK1007", "Microelectronic Circuits", "Sedra & Smith", "Electronics", 2),
    ("BK1008", "Let Us C", "Yashavant Kanetkar", "Programming", 5),
    ("BK1009", "Clean Code", "Robert C. Martin", "Programming", 1),
    ("BK1010", "Concepts of Physics", "H. C. Verma", "Physics", 3),
]


# ---------------------------------------------------------------- database

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    if db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO students (card_id, name, roll_no, branch, year, email, phone) VALUES (?,?,?,?,?,?,?)",
            SAMPLE_STUDENTS)
    if db.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO books (code, title, author, category, total_copies) VALUES (?,?,?,?,?)",
            SAMPLE_BOOKS)
    db.commit()
    db.close()


def today():
    return date.today()


def overdue_fine(due_date, on_date=None):
    days = ((on_date or today()) - date.fromisoformat(due_date)).days
    return max(days, 0) * FINE_PER_DAY


def issue_to_dict(row):
    d = dict(row)
    if d["return_date"] is None:
        d["status"] = "overdue" if date.fromisoformat(d["due_date"]) < today() else "active"
        d["fine"] = overdue_fine(d["due_date"])
    else:
        d["status"] = "returned"
    return d


def student_to_dict(row):
    d = dict(row)
    d["photo_url"] = url_for("static", filename=f"uploads/{d['photo']}") if d.get("photo") else None
    return d


def active_issues_for(student_id):
    rows = get_db().execute(
        ISSUE_SELECT + " WHERE i.student_id = ? AND i.return_date IS NULL ORDER BY i.due_date",
        (student_id,)).fetchall()
    return [issue_to_dict(r) for r in rows]


def find_student(query):
    query = (query or "").strip()
    if not query:
        return None
    return get_db().execute(
        "SELECT * FROM students WHERE card_id = ? OR roll_no = ? LIMIT 1", (query, query)).fetchone()


def find_book(query):
    query = (query or "").strip()
    if not query:
        return None
    return get_db().execute(BOOK_SELECT + " WHERE b.code = ?", (query,)).fetchone()


@app.context_processor
def inject_globals():
    return dict(library_name=LIBRARY_NAME, loan_days=LOAN_DAYS, max_books=MAX_BOOKS,
                fine_per_day=FINE_PER_DAY)


# ---------------------------------------------------------------- pages

@app.route("/")
def desk():
    return render_template("desk.html", active="desk")


@app.route("/books")
def books_page():
    return render_template("books.html", active="books")


@app.route("/students")
def students_page():
    return render_template("students.html", active="students")


@app.route("/records")
def records_page():
    return render_template("records.html", active="records")


@app.route("/students/<int:sid>/card")
def student_card(sid):
    row = get_db().execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
    if row is None:
        abort(404)
    return render_template("card.html", s=student_to_dict(row))


@app.route("/books/<int:bid>/label")
def book_label(bid):
    row = get_db().execute(BOOK_SELECT + " WHERE b.id = ?", (bid,)).fetchone()
    if row is None:
        abort(404)
    return render_template("label.html", b=dict(row))


# ---------------------------------------------------------------- API: stats

@app.get("/api/stats")
def api_stats():
    db = get_db()
    t = today().isoformat()
    return jsonify(
        books=db.execute("SELECT COALESCE(SUM(total_copies),0) FROM books").fetchone()[0],
        titles=db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        students=db.execute("SELECT COUNT(*) FROM students").fetchone()[0],
        issued=db.execute("SELECT COUNT(*) FROM issues WHERE return_date IS NULL").fetchone()[0],
        overdue=db.execute("SELECT COUNT(*) FROM issues WHERE return_date IS NULL AND due_date < ?",
                           (t,)).fetchone()[0],
    )


# ---------------------------------------------------------------- API: students

STUDENT_FIELDS = ("card_id", "name", "roll_no", "branch", "year", "email", "phone")


def save_photo(file):
    if not file or not file.filename:
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ALLOWED_PHOTO_EXT:
        raise ValueError("Photo must be an image (png, jpg, jpeg, webp, gif)")
    name = f"{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(UPLOAD_DIR, name))
    return name


def read_student_form():
    data = {f: (request.form.get(f) or "").strip() for f in STUDENT_FIELDS}
    if not data["card_id"] or not data["name"]:
        raise ValueError("ID card number and name are required")
    return data


@app.get("/api/students")
def api_students():
    q = f"%{request.args.get('q', '').strip()}%"
    rows = get_db().execute(
        """SELECT s.*, (SELECT COUNT(*) FROM issues i WHERE i.student_id = s.id AND i.return_date IS NULL)
               AS issued_count
           FROM students s
           WHERE s.name LIKE ? OR s.card_id LIKE ? OR s.roll_no LIKE ? OR s.branch LIKE ?
           ORDER BY s.name""", (q, q, q, q)).fetchall()
    return jsonify([student_to_dict(r) for r in rows])


@app.get("/api/students/lookup")
def api_student_lookup():
    row = find_student(request.args.get("q"))
    if row is None:
        return jsonify(error="No student found for this ID card"), 404
    total = get_db().execute("SELECT COUNT(*) FROM issues WHERE student_id = ?", (row["id"],)).fetchone()[0]
    return jsonify(student=student_to_dict(row), active_issues=active_issues_for(row["id"]),
                   total_issued=total, max_books=MAX_BOOKS)


@app.post("/api/students")
def api_create_student():
    try:
        data = read_student_form()
        data["photo"] = save_photo(request.files.get("photo"))
    except ValueError as e:
        return jsonify(error=str(e)), 400
    db = get_db()
    try:
        cur = db.execute(
            "INSERT INTO students (card_id, name, roll_no, branch, year, email, phone, photo) "
            "VALUES (:card_id, :name, :roll_no, :branch, :year, :email, :phone, :photo)", data)
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="A student with this ID card number already exists"), 409
    return jsonify(id=cur.lastrowid), 201


@app.put("/api/students/<int:sid>")
def api_update_student(sid):
    db = get_db()
    existing = db.execute("SELECT * FROM students WHERE id = ?", (sid,)).fetchone()
    if existing is None:
        return jsonify(error="Student not found"), 404
    try:
        data = read_student_form()
        data["photo"] = save_photo(request.files.get("photo")) or existing["photo"]
    except ValueError as e:
        return jsonify(error=str(e)), 400
    data["id"] = sid
    try:
        db.execute(
            "UPDATE students SET card_id=:card_id, name=:name, roll_no=:roll_no, branch=:branch, "
            "year=:year, email=:email, phone=:phone, photo=:photo WHERE id=:id", data)
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="Another student already has this ID card number"), 409
    return jsonify(ok=True)


@app.delete("/api/students/<int:sid>")
def api_delete_student(sid):
    db = get_db()
    if active_issues_for(sid):
        return jsonify(error="Student still has books issued. Return them first."), 400
    db.execute("DELETE FROM issues WHERE student_id = ?", (sid,))
    db.execute("DELETE FROM students WHERE id = ?", (sid,))
    db.commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- API: books

def read_book_json():
    body = request.get_json(silent=True) or {}
    data = {f: str(body.get(f) or "").strip() for f in ("code", "title", "author", "category")}
    if not data["code"] or not data["title"]:
        raise ValueError("Book code and title are required")
    try:
        data["total_copies"] = int(body.get("total_copies") or 1)
    except (TypeError, ValueError):
        raise ValueError("Copies must be a number")
    if data["total_copies"] < 1:
        raise ValueError("Copies must be at least 1")
    return data


@app.get("/api/books")
def api_books():
    q = f"%{request.args.get('q', '').strip()}%"
    rows = get_db().execute(
        BOOK_SELECT + " WHERE b.title LIKE ? OR b.author LIKE ? OR b.code LIKE ? OR b.category LIKE ? "
        "ORDER BY b.title LIMIT ?", (q, q, q, q, int(request.args.get("limit", 500)))).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/books/lookup")
def api_book_lookup():
    row = find_book(request.args.get("q"))
    if row is None:
        return jsonify(error="No book found with this code"), 404
    return jsonify(dict(row))


@app.post("/api/books")
def api_create_book():
    try:
        data = read_book_json()
    except ValueError as e:
        return jsonify(error=str(e)), 400
    db = get_db()
    try:
        cur = db.execute("INSERT INTO books (code, title, author, category, total_copies) "
                         "VALUES (:code, :title, :author, :category, :total_copies)", data)
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="A book with this code already exists"), 409
    return jsonify(id=cur.lastrowid), 201


@app.put("/api/books/<int:bid>")
def api_update_book(bid):
    try:
        data = read_book_json()
    except ValueError as e:
        return jsonify(error=str(e)), 400
    db = get_db()
    issued = db.execute("SELECT COUNT(*) FROM issues WHERE book_id = ? AND return_date IS NULL",
                        (bid,)).fetchone()[0]
    if data["total_copies"] < issued:
        return jsonify(error=f"{issued} copies are currently issued; total cannot be lower"), 400
    data["id"] = bid
    try:
        db.execute("UPDATE books SET code=:code, title=:title, author=:author, category=:category, "
                   "total_copies=:total_copies WHERE id=:id", data)
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="Another book already has this code"), 409
    return jsonify(ok=True)


@app.delete("/api/books/<int:bid>")
def api_delete_book(bid):
    db = get_db()
    if db.execute("SELECT 1 FROM issues WHERE book_id = ? AND return_date IS NULL", (bid,)).fetchone():
        return jsonify(error="Some copies are still issued. Collect them first."), 400
    db.execute("DELETE FROM issues WHERE book_id = ?", (bid,))
    db.execute("DELETE FROM books WHERE id = ?", (bid,))
    db.commit()
    return jsonify(ok=True)


# ---------------------------------------------------------------- API: issue / return

@app.post("/api/issue")
def api_issue():
    body = request.get_json(silent=True) or {}
    student = find_student(body.get("card_id"))
    if student is None:
        return jsonify(error="Student not found. Scan the ID card again."), 404
    book = find_book(body.get("book_code"))
    if book is None:
        return jsonify(error="Book not found"), 404

    active = active_issues_for(student["id"])
    if any(a["status"] == "overdue" for a in active):
        return jsonify(error="Student has overdue books. Return them before issuing new ones."), 400
    if len(active) >= MAX_BOOKS:
        return jsonify(error=f"Limit reached: a student can hold at most {MAX_BOOKS} books"), 400
    if any(a["book_id"] == book["id"] for a in active):
        return jsonify(error="Student already has a copy of this book"), 400
    if book["available"] <= 0:
        return jsonify(error="No copies of this book are available right now"), 400

    issue_date = today()
    due_date = issue_date + timedelta(days=LOAN_DAYS)
    db = get_db()
    cur = db.execute("INSERT INTO issues (student_id, book_id, issue_date, due_date) VALUES (?,?,?,?)",
                     (student["id"], book["id"], issue_date.isoformat(), due_date.isoformat()))
    db.commit()
    return jsonify(id=cur.lastrowid, due_date=due_date.isoformat(), book_title=book["title"],
                   student_name=student["name"]), 201


@app.post("/api/return/<int:iid>")
def api_return(iid):
    db = get_db()
    row = db.execute("SELECT * FROM issues WHERE id = ?", (iid,)).fetchone()
    if row is None:
        return jsonify(error="Issue record not found"), 404
    if row["return_date"]:
        return jsonify(error="This book was already returned"), 400
    fine = overdue_fine(row["due_date"])
    db.execute("UPDATE issues SET return_date = ?, fine = ? WHERE id = ?", (today().isoformat(), fine, iid))
    db.commit()
    return jsonify(ok=True, fine=fine)


@app.get("/api/issues")
def api_issues():
    status = request.args.get("status", "active")
    q = f"%{request.args.get('q', '').strip()}%"
    where = ["(s.name LIKE ? OR s.card_id LIKE ? OR s.roll_no LIKE ? OR b.title LIKE ? OR b.code LIKE ?)"]
    params = [q, q, q, q, q]
    if status == "active":
        where.append("i.return_date IS NULL")
    elif status == "overdue":
        where.append("i.return_date IS NULL AND i.due_date < ?")
        params.append(today().isoformat())
    elif status == "returned":
        where.append("i.return_date IS NOT NULL")
    rows = get_db().execute(
        ISSUE_SELECT + " WHERE " + " AND ".join(where) + " ORDER BY i.id DESC LIMIT 1000", params).fetchall()
    return jsonify([issue_to_dict(r) for r in rows])


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)),
            debug=os.environ.get("FLASK_DEBUG") == "1")

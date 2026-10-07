# Library Management System

A web app for a college library. The librarian scans a student's **ID card** (QR code or barcode) and the student's details fill in automatically, so a book can be issued in a few seconds.

## Features

- **Issue desk.** Scan the ID card with a USB barcode scanner, the webcam, or an uploaded photo of the card, or type the ID / roll no. The student's photo, name, roll no., branch, year, contact details and current loans fill in automatically.
- **Issue books.** Scan the book's barcode or search by title, author or code. The due date is set automatically.
- **Rules enforced.** At most 3 books per student. No new issues while a book is overdue. The same title can't be issued twice to one student. A book can only be issued if copies are available.
- **Returns and fines.** Return a book from the desk or the Records page. The overdue fine (₹2/day) is calculated automatically.
- **Students.** Add, edit, delete, search, and upload a photo. Each student gets a **printable ID card with a QR code and barcode**.
- **Books.** Add, edit, delete, search, track copies, and print barcode labels.
- **Records.** Filter by issued, overdue, returned, or all.
- No login needed: open the site and start scanning.

## Run it

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. It opens straight to the issue desk.

On first run, a SQLite database (`library.db`) is created with 5 sample students (`STU2024001` to `STU2024005`) and 10 sample books (`BK1001` to `BK1010`).

> The camera scanner only works on `localhost` or over HTTPS, because browsers block camera access otherwise. USB barcode scanners work everywhere: they act like a keyboard and type the code followed by Enter.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `LIBRARY_NAME` | `College Central Library` | Shown in the header and on ID cards |
| `LOAN_DAYS` | `14` | Loan period |
| `MAX_BOOKS_PER_STUDENT` | `3` | Borrowing limit |
| `FINE_PER_DAY` | `2` | Fine (₹) per overdue day |
| `LIBRARY_DB` | `library.db` | SQLite file path |
| `PORT` | `5000` | Server port |

## How ID card scanning works

Each student has a unique **ID card no.** (for example `STU2024001`). The card printed from *Students → ID card* holds that number as both a QR code and a Code-128 barcode. When the card is scanned at the desk, the app looks up that number (or the roll no.) and fills in the student's details.

If your college ID cards already have a barcode or QR code, enter the value it contains as the student's *ID card no.* and the existing cards will work as they are.

## Project structure

```
app.py               Flask backend + REST API + SQLite
templates/           HTML pages (desk, books, students, records, ID card, label)
static/style.css     Styles
static/js/           Frontend logic (common helpers + scanner, issue desk)
static/vendor/       html5-qrcode (scanning), qrcodejs + JsBarcode (card generation)
```

## Java desktop version

`LibraryManagementSystem.java` is the older Swing desktop version of this project. Run it with `javac LibraryManagementSystem.java && java LibraryManagementSystem`.

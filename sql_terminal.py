"""
Interactive SQL Terminal CLI for Student Academic Progression & Portfolio DBMS.
Allows students and examiners to execute direct SQL queries directly from the terminal.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "instance", "student_progression.db")

def print_table(headers, rows):
    if not headers:
        print("Empty result.")
        return
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(val) if val is not None else "NULL"))
    
    border = "+-" + "-+-".join("-" * w for w in col_widths) + "-+"
    header_line = "| " + " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)) + " |"
    
    print(border)
    print(header_line)
    print(border)
    for row in rows:
        line = "| " + " | ".join(str(val if val is not None else "NULL").ljust(col_widths[i]) for i, val in enumerate(row)) + " |"
        print(line)
    print(border)
    print(f"({len(rows)} row{'s' if len(rows) != 1 else ''} returned)\n")

def main():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}. Run 'python app.py' first to create and seed the database.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    print("=" * 70)
    print("🎓 Student Progression DBMS - Terminal SQL Interface")
    print("Database: SQLite (instance/student_progression.db)")
    print("=" * 70)
    print("Available Tables: students, semester_results, subject_marks, drop_years, seminars, activities")
    print("Type your SQL query and press Enter (or type 'help', 'tables', 'schema', or 'exit'):\n")

    while True:
        try:
            query = input("SQL> ").strip()
            if not query:
                continue
            if query.lower() in ["exit", "quit", "q"]:
                print("Exiting SQL terminal. Goodbye!")
                break
            if query.lower() == "help":
                print("\nQuick SQL Examples:")
                print("  SELECT roll_no, full_name, current_status FROM students;")
                print("  SELECT semester_no, sgpa, cgpa FROM semester_results WHERE student_id = 1;")
                print("  SELECT * FROM drop_years;")
                print("  SELECT s.full_name, sem.title FROM students s JOIN seminars sem ON s.id = sem.student_id;\n")
                continue
            if query.lower() == "tables":
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                tables = [r[0] for r in cursor.fetchall()]
                print("Tables in database:", ", ".join(tables), "\n")
                continue
            if query.lower() == "schema":
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
                for r in cursor.fetchall():
                    print(r[0] + ";\n")
                continue

            if not query.endswith(";"):
                query += ";"

            cursor.execute(query)
            if query.strip().upper().startswith("SELECT"):
                headers = [desc[0] for desc in cursor.description] if cursor.description else []
                rows = cursor.fetchall()
                print_table(headers, rows)
            else:
                conn.commit()
                print(f"Query executed successfully. Rows affected: {cursor.rowcount}\n")
        except Exception as exc:
            print(f"SQL Error: {exc}\n")

if __name__ == "__main__":
    main()

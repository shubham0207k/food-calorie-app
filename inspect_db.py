import sqlite3

conn = sqlite3.connect('app.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=== ALL USERS ===")
cur.execute("SELECT id, username, email, role, banned, created_at FROM users")
for row in cur.fetchall():
    print(dict(row))

conn.close()

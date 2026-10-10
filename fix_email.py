import sqlite3
conn = sqlite3.connect('app.db')
conn.execute("UPDATE users SET email='shubham@gmail.com' WHERE id=2")
conn.commit()
print("Email fixed: shubham@gmail.com1  -->  shubham@gmail.com")
conn.close()

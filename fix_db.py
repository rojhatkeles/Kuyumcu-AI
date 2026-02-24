import sqlite3
import os

db_path = "./sql_app.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    try:
        cur.execute("ALTER TABLE transactions ADD COLUMN payment_type VARCHAR DEFAULT 'Cash'")
        print("Added payment_type column")
    except sqlite3.OperationalError as e:
        print(f"payment_type error: {e}")
        
    try:
        cur.execute("ALTER TABLE transactions ADD COLUMN net_try FLOAT DEFAULT 0.0")
        print("Added net_try column")
    except sqlite3.OperationalError as e:
        print(f"net_try error: {e}")
        
    conn.commit()
    conn.close()
    print("DB migration check complete.")
else:
    print("db not found.")

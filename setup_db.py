import mysql.connector

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=""
)

cur = conn.cursor()

# ---------------- DATABASE ----------------
cur.execute("CREATE DATABASE IF NOT EXISTS leave_management")
cur.execute("USE leave_management")

# ---------------- EMPLOYEES ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS employees (
    id INT AUTO_INCREMENT PRIMARY KEY,
    pf_no VARCHAR(30) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    password VARCHAR(255) NOT NULL,
    branch VARCHAR(100),
    role VARCHAR(20) DEFAULT 'employee',
    status VARCHAR(20) DEFAULT 'active',
    leave_balance INT DEFAULT 12
)
""")

# ---------------- LEAVE REQUESTS ----------------
cur.execute("""
CREATE TABLE IF NOT EXISTS leave_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    employee_id INT,
    leave_type VARCHAR(20),
    from_date DATE,
    to_date DATE,
    reason TEXT,
    status VARCHAR(20) DEFAULT 'pending'
)
""")

# ---------------- DEFAULT TEST USERS ----------------
cur.execute("SELECT * FROM employees WHERE pf_no='123'")
if not cur.fetchone():
    cur.execute("""
    INSERT INTO employees (pf_no, name, password, branch, role, status, leave_balance)
    VALUES ('123','Employee One','123','HQ','employee','active',12)
    """)

cur.execute("SELECT * FROM employees WHERE pf_no='M001'")
if not cur.fetchone():
    cur.execute("""
    INSERT INTO employees (pf_no, name, password, branch, role, status, leave_balance)
    VALUES ('M001','Manager','123','HQ','manager','active',12)
    """)

conn.commit()
conn.close()

print("Database setup completed")
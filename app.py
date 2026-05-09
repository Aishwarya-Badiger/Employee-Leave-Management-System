from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
import os

from werkzeug.utils import secure_filename

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from datetime import datetime, date

app = Flask(__name__)

app.secret_key = "secretkey"

# ================= FILE UPLOAD =================

UPLOAD_FOLDER = "static/uploads"

ALLOWED_EXTENSIONS = {
    'png',
    'jpg',
    'jpeg'
}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(
    os.path.join(app.root_path, UPLOAD_FOLDER),
    exist_ok=True
)

def allowed_file(filename):

    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ================= DATABASE =================

def get_db():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="org_leave_system"
    )


# ================= HOME =================

@app.route('/')
def home():

    return render_template('login.html')


# ================= LOGIN =================

@app.route('/login', methods=['POST'])
def login():

    pf_no = request.form['pf_no']
    password = request.form['password']

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        SELECT
            id,
            password,
            role

        FROM employees

        WHERE pf_no=%s

    """, (pf_no,))

    user = cur.fetchone()

    if not user:
        return "Invalid PF Number"

    stored_password = user[1]

    # PASSWORD CHECK

    if not check_password_hash(
        stored_password,
        password
    ):
        return "Invalid Password"

    session['user_id'] = user[0]

    session['role'] = user[2].strip().lower()

    # ROLE LOGIN

    if session['role'] == "admin":

        return redirect('/admin_dashboard')

    elif session['role'] == "manager":

        return redirect('/manager_dashboard')

    else:

        return redirect('/dashboard')


# ================= EMPLOYEE DASHBOARD =================

@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] != 'employee':
        return redirect('/')

    db = get_db()

    cur = db.cursor(dictionary=True)

    cur.execute("""

        SELECT *

        FROM employees

        WHERE id=%s

    """, (session['user_id'],))

    user = cur.fetchone()

    return render_template(
        'dashboard.html',
        user=user
    )


# ================= ADMIN DASHBOARD =================

@app.route('/admin_dashboard')
def admin_dashboard():

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] != 'admin':
        return redirect('/')

    return render_template('admin_dashboard.html')


# ================= MANAGER DASHBOARD =================

@app.route('/manager_dashboard')
def manager_dashboard():

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] not in ['manager', 'admin']:
        return redirect('/')

    status_filter = request.args.get('status')

    type_filter = request.args.get('type')

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        SELECT
            lr.id,
            e.name,
            lr.leave_type,
            lr.from_date,
            lr.to_date,
            lr.reason,
            lr.status,
            NULL,
            'normal'

        FROM leave_requests lr

        JOIN employees e
        ON lr.employee_id = e.id

        UNION ALL

        SELECT
            el.id,
            e.name,
            'Emergency',
            el.from_date,
            el.to_date,
            el.reason,
            el.status,
            el.proof_image,
            'emergency'

        FROM emergency_leaves el

        JOIN employees e
        ON el.employee_id = e.id

        ORDER BY from_date DESC

    """)

    data = cur.fetchall()

    filtered = []

    for r in data:

        status = (r[6] or "").lower()

        type_ = (r[8] or "").lower()

        if status_filter and status != status_filter.lower():
            continue

        if type_filter and type_ != type_filter.lower():
            continue

        filtered.append(r)

    return render_template(
        'manager_dashboard.html',
        requests=filtered
    )


# ================= EMPLOYEE LIST =================

@app.route('/employees')
def employees():

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] not in ['admin', 'manager']:
        return redirect('/')

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        SELECT
            id,
            pf_no,
            name,
            branch,
            role,
            leave_balance

        FROM employees

    """)

    employees = cur.fetchall()

    return render_template(
        'employee_info.html',
        employees=employees
    )


# ================= ADD EMPLOYEE PAGE =================

@app.route('/add_employee')
def add_employee():

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] not in ['admin', 'manager']:
        return redirect('/')

    return render_template('add_employee.html')


# ================= SAVE EMPLOYEE =================

@app.route('/save_employee', methods=['POST'])
def save_employee():

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] not in ['admin', 'manager']:
        return redirect('/')

    db = get_db()

    cur = db.cursor()

    hashed_password = generate_password_hash(
        request.form['password']
    )

    try:

        cur.execute("""

            INSERT INTO employees
            (
                pf_no,
                name,
                password,
                branch,
                role,
                leave_balance
            )

            VALUES (%s,%s,%s,%s,%s,%s)

        """, (

            request.form['pf_no'],
            request.form['name'],
            hashed_password,
            request.form['branch'],
            request.form['role'],
            2

        ))

        db.commit()

        flash("Employee Added Successfully ✅")

    except mysql.connector.IntegrityError:

        flash("PF Number Already Exists ❌")

    return redirect('/add_employee')


# ================= DELETE EMPLOYEE =================

@app.route('/delete_employee/<int:id>')
def delete_employee(id):

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] != 'admin':
        return redirect('/')

    if id == session['user_id']:
        return "You cannot delete yourself"

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        DELETE FROM employees

        WHERE id=%s

    """, (id,))

    db.commit()

    return redirect('/employees')


# ================= APPLY LEAVE =================

@app.route('/apply_leave')
def apply_leave():

    if 'user_id' not in session:
        return redirect('/')

    return render_template('apply_leave.html')


# ================= SUBMIT LEAVE =================

@app.route('/submit_leave', methods=['POST'])
def submit_leave():

    if 'user_id' not in session:
        return redirect('/')

    f = datetime.strptime(
        request.form['from_date'],
        "%Y-%m-%d"
    )

    t = datetime.strptime(
        request.form['to_date'],
        "%Y-%m-%d"
    )

    if f > t:
        return "Invalid Date Range"

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        SELECT COUNT(*)

        FROM leave_requests

        WHERE employee_id=%s
        AND status='approved'

    """, (session['user_id'],))

    if cur.fetchone()[0] >= 2:
        return "Limit reached → Use Emergency Leave"

    cur.execute("""

        INSERT INTO leave_requests
        (
            employee_id,
            leave_type,
            from_date,
            to_date,
            reason
        )

        VALUES (%s,%s,%s,%s,%s)

    """, (

        session['user_id'],
        request.form['leave_type'],
        request.form['from_date'],
        request.form['to_date'],
        request.form['reason']

    ))

    db.commit()

    return redirect('/dashboard')


# ================= LEAVE STATUS =================

@app.route('/leave_status')
def leave_status():

    if 'user_id' not in session:
        return redirect('/')

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        SELECT
            leave_type,
            from_date,
            to_date,
            reason,
            status

        FROM leave_requests

        WHERE employee_id=%s

    """, (session['user_id'],))

    normal_leaves = cur.fetchall()

    cur.execute("""

        SELECT
            'Emergency',
            from_date,
            to_date,
            reason,
            status

        FROM emergency_leaves

        WHERE employee_id=%s

    """, (session['user_id'],))

    emergency_leaves = cur.fetchall()

    all_leaves = normal_leaves + emergency_leaves

    return render_template(
        'leave_status.html',
        leaves=all_leaves
    )


# ================= EMERGENCY LEAVE PAGE =================

@app.route('/emergency_leave')
def emergency_leave():

    if 'user_id' not in session:
        return redirect('/')

    return render_template('emergency_leave.html')


# ================= SUBMIT EMERGENCY LEAVE =================

@app.route('/submit_emergency_leave', methods=['POST'])
def submit_emergency_leave():

    if 'user_id' not in session:
        return redirect('/')

    f = datetime.strptime(
        request.form['from_date'],
        "%Y-%m-%d"
    ).date()

    t = datetime.strptime(
        request.form['to_date'],
        "%Y-%m-%d"
    ).date()

    if f != date.today() or t != date.today():
        return "Emergency leave only allowed for today"

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        SELECT COUNT(*)

        FROM emergency_leaves

        WHERE employee_id=%s
        AND MONTH(from_date)=MONTH(CURDATE())

    """, (session['user_id'],))

    count = cur.fetchone()[0]

    if count >= 2:
        return "Emergency leave limit reached"

    file = request.files.get('proof')

    filename = None

    if file and file.filename != "":

        if allowed_file(file.filename):

            filename = secure_filename(file.filename)

            file.save(

                os.path.join(
                    app.root_path,
                    UPLOAD_FOLDER,
                    filename
                )

            )

    cur.execute("""

        INSERT INTO emergency_leaves
        (
            employee_id,
            reason,
            from_date,
            to_date,
            proof_image
        )

        VALUES (%s,%s,%s,%s,%s)

    """, (

        session['user_id'],
        request.form['reason'],
        request.form['from_date'],
        request.form['to_date'],
        filename

    ))

    db.commit()

    return redirect('/dashboard')


# ================= APPROVE LEAVE =================

@app.route('/approve/<int:id>/<type>')
def approve(id, type):

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] not in ['manager', 'admin']:
        return redirect('/')

    db = get_db()

    cur = db.cursor()

    if type == "normal":

        cur.execute("""

            SELECT employee_id

            FROM leave_requests

            WHERE id=%s

        """, (id,))

        emp = cur.fetchone()

        if emp:

            cur.execute("""

                UPDATE leave_requests

                SET status='approved'

                WHERE id=%s

            """, (id,))

            cur.execute("""

                UPDATE employees

                SET leave_balance = leave_balance - 1

                WHERE id=%s

            """, (emp[0],))

    else:

        cur.execute("""

            UPDATE emergency_leaves

            SET status='approved'

            WHERE id=%s

        """, (id,))

    db.commit()

    return redirect('/manager_dashboard')


# ================= REJECT LEAVE =================

@app.route('/reject/<int:id>/<type>')
def reject(id, type):

    if 'user_id' not in session:
        return redirect('/')

    if session['role'] not in ['manager', 'admin']:
        return redirect('/')

    db = get_db()

    cur = db.cursor()

    if type == "normal":

        cur.execute("""

            UPDATE leave_requests

            SET status='rejected'

            WHERE id=%s

        """, (id,))

    else:

        cur.execute("""

            UPDATE emergency_leaves

            SET status='rejected'

            WHERE id=%s

        """, (id,))

    db.commit()

    return redirect('/manager_dashboard')


# ================= FORGOT PASSWORD =================

@app.route('/forgot_password')
def forgot_password():

    return render_template('forgot_password.html')


# ================= RESET PASSWORD =================

@app.route('/reset_password', methods=['POST'])
def reset_password():

    pf_no = request.form['pf_no']

    new_password = request.form['new_password']

    db = get_db()

    cur = db.cursor()

    cur.execute("""

        SELECT id

        FROM employees

        WHERE pf_no=%s

    """, (pf_no,))

    user = cur.fetchone()

    if not user:

        flash("PF Number Not Found ❌")

        return redirect('/forgot_password')

    hashed_password = generate_password_hash(
        new_password
    )

    cur.execute("""

        UPDATE employees

        SET password=%s

        WHERE pf_no=%s

    """, (

        hashed_password,
        pf_no

    ))

    db.commit()

    flash("Password Updated Successfully ✅")

    return redirect('/forgot_password')


# ================= LOGOUT =================

@app.route('/logout')
def logout():

    session.clear()

    return redirect('/')


# ================= RUN APP =================

if __name__ == "__main__":

    app.run(debug=True)
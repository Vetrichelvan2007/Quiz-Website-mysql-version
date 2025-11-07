from flask import *
import mysql.connector  # changed from oracledb
from datetime import datetime
import os
app = Flask(__name__)
app.secret_key = "your_secret_key_here" 

# Run this command in CMD to start ngrok
# C:\Users\vetrichelvan\AppData\Local\Microsoft\WindowsApps\ngrok.exe http 5000

def connectdb():
    try:
        print("=== Attempting Aiven MySQL Database Connection ===")

        connection = mysql.connector.connect(
            host=os.getenv("DATABASE_HOST"),
            user=os.getenv("DATABASE_USERNAME"),
            password=os.getenv("DATABASE_PASSWORD"),
            database=os.getenv("DATABASE"),
            port=19176,
            ssl_disabled=False  # keep true for Aiven
        )

        if connection.is_connected():
            print("✓ Connected successfully to Aiven MySQL!")
            return connection

    except mysql.connector.Error as e:
        print(f"✗ MySQL Error: {e}")
        return None
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
        return None



def init_db():
    try:
        connection = connectdb()
        if connection is None:
            print("❌ Database connection failed. Tables not created.")
            return

        cursor = connection.cursor()

        print("🛠 Creating tables if not exist...")

        table_queries = [
            """
            CREATE TABLE IF NOT EXISTS department (
                dept_id INT PRIMARY KEY AUTO_INCREMENT,
                dept_name VARCHAR(100) UNIQUE NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS class (
                class_id INT PRIMARY KEY AUTO_INCREMENT,
                class_name VARCHAR(100) NOT NULL,
                dept_id INT NOT NULL,
                CONSTRAINT fk_class_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS app_user (
                user_id INT PRIMARY KEY AUTO_INCREMENT,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role ENUM('student','teacher','admin') NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS teacher (
                teacher_id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                CONSTRAINT fk_teacher_user FOREIGN KEY (user_id) REFERENCES app_user(user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS student (
                student_id INT PRIMARY KEY AUTO_INCREMENT,
                user_id INT NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                class_id INT NOT NULL,
                dept_id INT NOT NULL,
                CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES app_user(user_id),
                CONSTRAINT fk_student_class FOREIGN KEY (class_id) REFERENCES class(class_id),
                CONSTRAINT fk_student_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS quiz (
                quiz_id INT PRIMARY KEY AUTO_INCREMENT,
                name VARCHAR(100) NOT NULL,
                subject VARCHAR(100) NOT NULL,
                class_id INT NOT NULL,
                dept_id INT NOT NULL,
                no_of_question INT DEFAULT 10 NOT NULL,
                mark_per_question INT DEFAULT 1 NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                duration_minutes INT NOT NULL,
                created_by INT NOT NULL,
                starttime VARCHAR(10),
                endtime VARCHAR(10),
                status VARCHAR(20) DEFAULT 'active',
                total_marks INT GENERATED ALWAYS AS (no_of_question * mark_per_question) STORED,
                CONSTRAINT fk_quiz_class FOREIGN KEY (class_id) REFERENCES class(class_id),
                CONSTRAINT fk_quiz_dept FOREIGN KEY (dept_id) REFERENCES department(dept_id),
                CONSTRAINT fk_quiz_teacher FOREIGN KEY (created_by) REFERENCES teacher(teacher_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS quiz_question (
                question_id INT PRIMARY KEY AUTO_INCREMENT,
                quiz_id INT NOT NULL,
                question TEXT NOT NULL,
                op1 VARCHAR(255) NOT NULL,
                op2 VARCHAR(255) NOT NULL,
                op3 VARCHAR(255) NOT NULL,
                op4 VARCHAR(255) NOT NULL,
                correct_answer ENUM('op1','op2','op3','op4') NOT NULL,
                mark INT DEFAULT 1 NOT NULL,
                CONSTRAINT fk_question_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS result_for_each_question (
                result_for_each_question_id INT PRIMARY KEY AUTO_INCREMENT,
                quiz_id INT NOT NULL,
                question_id INT NOT NULL,
                student_id INT NOT NULL,
                question VARCHAR(500) NOT NULL,
                op1 VARCHAR(100) NOT NULL,
                op2 VARCHAR(100) NOT NULL,
                op3 VARCHAR(100) NOT NULL,
                op4 VARCHAR(100) NOT NULL,
                crt_ans ENUM('op1','op2','op3','op4') NOT NULL,
                student_ans ENUM('op1','op2','op3','op4') DEFAULT NULL,
                CONSTRAINT fk_rfeq_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id),
                CONSTRAINT fk_rfeq_question FOREIGN KEY (question_id) REFERENCES quiz_question(question_id),
                CONSTRAINT fk_rfeq_student FOREIGN KEY (student_id) REFERENCES student(student_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS result_for_quiz (
                result_id INT PRIMARY KEY AUTO_INCREMENT,
                quiz_id INT NOT NULL,
                student_id INT NOT NULL,
                total_mark INT DEFAULT 0,
                CONSTRAINT fk_rfq_quiz FOREIGN KEY (quiz_id) REFERENCES quiz(quiz_id),
                CONSTRAINT fk_rfq_student FOREIGN KEY (student_id) REFERENCES student(student_id)
            )
            """
        ]

        for query in table_queries:
            cursor.execute(query)
            connection.commit()

        print("✅ All tables created successfully!")

    except Exception as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        if connection:
            cursor.close()
            connection.close()



@app.route("/testdb")
def testdb():
    conn = connectdb()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT NOW();")
        result = cursor.fetchone()
        conn.close()
        return f"✅ Connected successfully! Server time: {result}"
    else:
        return "❌ Failed to connect to PlanetScale."

def no_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "-1"
    return response

@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            connection = connectdb()
            if connection is None:
                return "Database connection failed", 500

            cursor = connection.cursor()

            # MySQL uses %s placeholders
            cursor.execute(
                "SELECT * FROM app_user WHERE username=%s AND password_hash=%s",
                (username, password)
            )
            user = cursor.fetchone()
            print("User fetched:", user)

            if user and user[4].lower() == "teacher":
                cursor.execute("SELECT * FROM teacher WHERE user_id=%s", (user[0],))
                teacher = cursor.fetchone()
                print("Teacher fetched:", teacher)

                if teacher:
                    session["teacher_id"] = teacher[0]
                    session["teacher_name"] = teacher[2]
                    session["user_id"] = user[0]
                    session["username"] = user[1]
                    session["email"] = user[2]
                    session["password"] = user[3]
                    session["role"] = "teacher"

                    return redirect(url_for("teacher_dashboard"))

            elif user and user[4].lower() == "student":
                cursor.execute("SELECT * FROM student WHERE user_id=%s", (user[0],))
                student = cursor.fetchone()

                if student:
                    cursor.execute("SELECT class_name FROM class WHERE class_id=%s", (student[3],))
                    class_name = cursor.fetchone()[0]

                    cursor.execute("SELECT dept_name FROM department WHERE dept_id=%s", (student[4],))
                    dept_name = cursor.fetchone()[0]

                    session["student_id"] = student[0]
                    session["student_name"] = student[2]
                    session["user_id"] = user[0]
                    session["username"] = user[1]
                    session["email"] = user[2]
                    session["password"] = user[3]
                    session["class_id"] = student[3]
                    session["dept_id"] = student[4]
                    session["class_name"] = class_name
                    session["dept_name"] = dept_name
                    session["role"] = "student"

                    return redirect(url_for("student_dashboard"))

            return render_template("login.html", error="Invalid username or password")

        except Exception as e:
            print("Login error:", e)
            return render_template("login.html", error="Something went wrong")

        finally:
            if connection:
                connection.close()

    return render_template("login.html", error="")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    if request.method == "POST":
        fullname = (request.form.get("fullname") or "").strip()
        email = (request.form.get("email") or "").strip()
        username = (request.form.get("username") or "").strip()
        password = (request.form.get("password") or "").strip()

        if not all([fullname, email, username, password]):
            return "All fields are required!"

        try:
            connection = connectdb()
            cursor = connection.cursor()

            # Insert user into app_user (MySQL auto-increment user_id)
            cursor.execute(
                "INSERT INTO app_user (username, email, password_hash, role) VALUES (%s, %s, %s, 'teacher')",
                (username, email, password)
            )

            # Get the auto-generated user_id
            user_id = cursor.lastrowid

            # Insert into teacher table
            cursor.execute(
                "INSERT INTO teacher (user_id, name) VALUES (%s, %s)",
                (user_id, fullname)
            )

            connection.commit()
            return redirect(url_for("login"))

        except Exception as e:
            return f"Error: {str(e)}"

        finally:
            if connection:
                connection.close()

    return render_template("signup.html")

@app.route('/dashboard', methods=["POST", "GET"])
def teacher_dashboard():
    if "teacher_id" not in session:
        return redirect(url_for("login"))

    quizzes = []
    stats = {"total_quizzes": 0, "active_quizzes": 0, "total_students": 0}

    try:
        connection = connectdb()
        cursor = connection.cursor()

        query_all = """
            SELECT name, subject, start_date, end_date, duration_minutes, 
                   no_of_question, total_marks, status, quiz_id, class_id, dept_id, 
                   starttime, endtime
            FROM quiz 
            WHERE created_by = %s
            ORDER BY start_date DESC
        """
        cursor.execute(query_all, (int(session["teacher_id"]),))
        all_rows = cursor.fetchall()

        stats["total_quizzes"] = len(all_rows)
        now = datetime.now()
        count = 0

        for row in all_rows:
            count += 1
            quiz_id = row[8]
            start_date, end_date = row[2], row[3]
            start_time_str, end_time_str = row[11], row[12]

            # Parse "07:00 pm" and "08:00 am" safely into time objects
            try:
                start_time = datetime.strptime(start_time_str.strip().lower(), "%I:%M %p").time()
            except Exception:
                start_time = datetime.strptime("12:00 am", "%I:%M %p").time()

            try:
                end_time = datetime.strptime(end_time_str.strip().lower(), "%I:%M %p").time()
            except Exception:
                end_time = datetime.strptime("11:59 pm", "%I:%M %p").time()

            # Combine date + time for comparisons
            quiz_start = datetime.combine(start_date, start_time)
            quiz_end = datetime.combine(end_date, end_time)

            current_status = row[7]

            # Update quiz status
            if now < quiz_start and current_status != 'upcoming':
                cursor.execute("UPDATE quiz SET status='upcoming' WHERE quiz_id=%s", (quiz_id,))
                connection.commit()
                current_status = 'upcoming'
            elif quiz_start <= now <= quiz_end and current_status != 'active':
                cursor.execute("UPDATE quiz SET status='active' WHERE quiz_id=%s", (quiz_id,))
                connection.commit()
                current_status = 'active'
            elif now > quiz_end and current_status != 'inactive':
                cursor.execute("UPDATE quiz SET status='inactive' WHERE quiz_id=%s", (quiz_id,))
                connection.commit()
                current_status = 'inactive'

            # Fetch class and department names
            cursor.execute("SELECT class_name FROM class WHERE class_id=%s", (row[9],))
            class_name = cursor.fetchone()[0]

            cursor.execute("SELECT dept_name FROM department WHERE dept_id=%s", (row[10],))
            dept_name = cursor.fetchone()[0]

            quiz_data = {
                "name": row[0],
                "subject": row[1],
                "start_date": row[2].strftime("%Y-%m-%d"),
                "end_date": row[3].strftime("%Y-%m-%d"),
                "duration_minutes": row[4],
                "no_of_question": row[5],
                "total_marks": row[6],
                "status": current_status,
                "quiz_id": row[8],
                "class_name": class_name,
                "dept_name": dept_name,
                "starttime": row[11],
                "endtime": row[12]
            }

            if current_status == 'active':
                stats["active_quizzes"] += 1
                quizzes.append(quiz_data)

        # Total students count
        try:
            cursor.execute("SELECT COUNT(*) FROM student")
            stats["total_students"] = cursor.fetchone()[0]
        except:
            stats["total_students"] = 0

        cursor.close()
        connection.close()

    except Exception as e:
        return f"Error: {str(e)}"

    return render_template('teacherhomepage.html', quizzes=quizzes, stats=stats, total_quizzes=count)

@app.route("/editprofile", methods=["GET", "POST"])
def editprofile():
    if "teacher_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        teacher_name = request.form.get("teacherName") or session.get("name")
        teacher_username = request.form.get("username") or session.get("username")
        teacher_email = request.form.get("email") or session.get("email")
        teacher_password = request.form.get("password") or session.get("password")

        try:
            connection = connectdb()
            cursor = connection.cursor()

            # Update app_user
            cursor.execute(
                "UPDATE app_user SET username=%s, email=%s, password_hash=%s WHERE user_id=%s",
                (teacher_username.strip(), teacher_email.strip(), teacher_password.strip(), session["user_id"])
            )

            # Update teacher
            cursor.execute(
                "UPDATE teacher SET name=%s WHERE user_id=%s",
                (teacher_name.strip(), session["user_id"])
            )

            # Update session variables
            session["username"] = teacher_username
            session["email"] = teacher_email
            session["password"] = teacher_password
            session["name"] = teacher_name

            connection.commit()
            cursor.close()
            connection.close()

            return redirect(url_for('teacher_dashboard'))

        except Exception as e:
            print("Edit profile error:", e)

    return render_template("editprofile.html", teacher=session)


@app.route("/changepassword", methods=["POST","GET"])
def changepassword():
    if "role" not in session:
        return redirect(url_for("login"))

    role = {}

    if session["role"] == "teacher":
        if "teacher_id" not in session:
            return redirect(url_for("login"))
        role["id"] = session["teacher_id"]
        role["role"] = "Teacher"
        role["password"] = session["password"]

    elif session["role"] == "student":
        if "student_id" not in session:
            return redirect(url_for("login"))
        role["id"] = session["student_id"]
        role["role"] = "Student"
        role["password"] = session["password"]
    else:
        return redirect(url_for("login"))

    if request.method == "POST":
        newPassword = request.form.get("newPassword")
        confirmPassword = request.form.get("confirmPassword")

        if newPassword != confirmPassword:
            return render_template('changepassword.html', role=role, error="Passwords do not match")

        try:
            connection = connectdb()
            cursor = connection.cursor()

            # MySQL placeholder %s
            cursor.execute(
                "UPDATE app_user SET password_hash=%s WHERE user_id=%s",
                (newPassword, session["user_id"])
            )

            session["password"] = newPassword
            connection.commit()
            cursor.close()
            connection.close()

            return redirect(url_for('teacher_dashboard'))

        except Exception as e:
            print("Change password error:", e)
            return render_template('changepassword.html', role=role, error="Something went wrong")

    return render_template('changepassword.html', role=role)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route("/get_classes/<deptname>")
def get_classes(deptname):
    connection = connectdb()
    cursor = connection.cursor()

    # Get department ID
    cursor.execute(
        "SELECT dept_id FROM department WHERE LOWER(dept_name) = LOWER(%s)",
        (deptname,)
    )
    dept_row = cursor.fetchone()
    if not dept_row:
        cursor.close()
        connection.close()
        return jsonify([])

    dept_id = dept_row[0]

    # Get classes for the department
    cursor.execute(
        "SELECT class_name FROM class WHERE dept_id = %s ORDER BY class_name",
        (dept_id,)
    )
    classes = [row[0] for row in cursor.fetchall()]

    cursor.close()
    connection.close()
    return jsonify(classes)

@app.route("/createquiz", methods=["GET", "POST"])
def createquiz():
    if "teacher_id" not in session:
        return redirect(url_for("login"))

    # Fetch departments from MySQL
    connection = connectdb()
    cursor = connection.cursor()
    cursor.execute("SELECT dept_name FROM department ORDER BY dept_name")
    departments = [row[0] for row in cursor.fetchall()]
    cursor.close()
    connection.close()

    if request.method == "POST":
        quiz_name = request.form.get("quiz_name").strip()
        subject = request.form.get("subject").strip()
        classname = request.form.get("class").strip()
        deptname = request.form.get("dept").strip()
        no_of_questions = request.form.get("no_of_questions").strip()
        mark_per_question = request.form.get("mark_per_question").strip()
        start_date = request.form.get("start_date")
        start_time = request.form.get("start_time")
        start_ampm = request.form.get("start_ampm")
        end_date = request.form.get("end_date")
        end_time = request.form.get("end_time")
        end_ampm = request.form.get("end_ampm")
        duration = request.form.get("duration_minutes").strip()

        # Store quiz info in session
        session["quiz_info"] = {
            "quiz_name": quiz_name,
            "subject": subject,
            "class": classname,
            "dept": deptname,
            "no_of_questions": no_of_questions,
            "mark_per_question": mark_per_question,
            "start_date": start_date,
            "start_time": start_time,
            "start_ampm": start_ampm,
            "end_date": end_date,
            "end_time": end_time,
            "end_ampm": end_ampm,
            "duration": duration
        }

        return redirect(url_for("add_questions", total_questions=no_of_questions))

    return render_template("createquiz.html", departments=departments)

@app.route("/add_questions/<int:total_questions>", methods=["GET", "POST"])
def add_questions(total_questions):
    if "teacher_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        questions = []
        for i in range(1, total_questions + 1):
            question_text = request.form.get(f"question_{i}").strip()
            option1 = request.form.get(f"option1_{i}").strip()
            option2 = request.form.get(f"option2_{i}").strip()
            option3 = request.form.get(f"option3_{i}").strip()
            option4 = request.form.get(f"option4_{i}").strip()
            correct_option = request.form.get(f"correct_option_{i}").strip()

            questions.append({
                "question_text": question_text,
                "options": [option1, option2, option3, option4],
                "correct_option": correct_option
            })
        print(questions)

        try:
            connection = connectdb()
            cursor = connection.cursor()

            quiz_info = session.get("quiz_info", {})

            # Insert quiz (MySQL auto-increment quiz_id)
            cursor.execute("""
                INSERT INTO quiz 
                (name, subject, class_id, dept_id, no_of_question, mark_per_question, 
                 start_date, end_date, duration_minutes, created_by, starttime, endtime)
                VALUES (%s, %s,
                       (SELECT class_id FROM class WHERE class_name=%s),
                       (SELECT dept_id FROM department WHERE dept_name=%s),
                       %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                quiz_info["quiz_name"], quiz_info["subject"], quiz_info["class"], quiz_info["dept"],
                int(quiz_info["no_of_questions"]), int(quiz_info["mark_per_question"]),
                quiz_info["start_date"], quiz_info["end_date"], quiz_info["duration"],
                session["teacher_id"],
                f"{quiz_info['start_time']} {quiz_info['start_ampm']}",
                f"{quiz_info['end_time']} {quiz_info['end_ampm']}"
            ))

            # Get the inserted quiz_id
            quiz_id = cursor.lastrowid

            # Insert questions
            for q in questions:
                cursor.execute("""
                    INSERT INTO quiz_question 
                    (quiz_id, question, op1, op2, op3, op4, correct_answer, mark)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    quiz_id, q["question_text"], q["options"][0], q["options"][1], 
                    q["options"][2], q["options"][3], q["correct_option"], int(quiz_info["mark_per_question"])
                ))

            connection.commit()
            cursor.close()
            connection.close()
            return redirect(url_for("teacher_dashboard"))

        except Exception as e:
            print(f"Error: {e}")

    return render_template("mcq.html", total_questions=total_questions)

@app.route('/activequizzes')
def activequizzes():
    connection = connectdb()
    cur = connection.cursor()

    if session["role"] == "teacher":
        query = """
        SELECT quiz_id, name, subject, class_id, dept_id, no_of_question, 
               mark_per_question, start_date, end_date, duration_minutes, 
               starttime, endtime, status, total_marks
        FROM quiz 
        WHERE created_by = %s
        ORDER BY start_date DESC
        """
        cur.execute(query, (int(session["teacher_id"]),))
    elif session["role"] == "student":
        query = """
        SELECT quiz_id, name, subject, class_id, dept_id, no_of_question, 
               mark_per_question, start_date, end_date, duration_minutes, 
               starttime, endtime, status, total_marks
        FROM quiz 
        WHERE class_id = %s AND status='inactive'
        ORDER BY start_date DESC
        """
        cur.execute(query, (int(session["class_id"]),))

    quizzes = []
    for row in cur:
        quizzes.append({
            "quiz_id": row[0],
            "name": row[1],
            "subject": row[2],
            "class_id": row[3],
            "dept_id": row[4],
            "no_of_question": row[5],
            "mark_per_question": row[6],
            "start_date": row[7].strftime("%Y-%m-%d"),
            "end_date": row[8].strftime("%Y-%m-%d"),
            "DURATION_MINUTES": row[9],  # Match template
            "starttime": row[10],
            "endtime": row[11],
            "status": row[12],
            "total_marks": row[13]
        })

    cur.close()
    connection.close()

    return render_template(
        'activequizzes.html',
        quizzes=quizzes,
        student_id=session.get("student_id"),
        role=session.get("role")
    )

@app.route("/addstudent", methods=["POST","GET"])
def addstudent():
    if request.method == "POST":
        studentName = request.form.get("studentName").strip()
        studentClass = request.form.get("studentClass").strip()
        studentDept = request.form.get("studentDept").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password").strip()

        try:
            connection = connectdb()
            cursor = connection.cursor()

            # Insert into app_user (MySQL auto-increment user_id)
            username = f"{studentName}{email.split('@')[0]}"  # Generate unique username
            cursor.execute("""
                INSERT INTO app_user(username, email, password_hash, role)
                VALUES (%s, %s, %s, 'student')
            """, (username, email, password))
            user_id = cursor.lastrowid

            # Check if class exists
            cursor.execute("SELECT class_id, dept_id FROM class WHERE LOWER(class_name) = %s", (studentClass.lower(),))
            class_row = cursor.fetchone()

            if class_row:
                class_id, dept_id = class_row
            else:
                # Check if department exists
                cursor.execute("SELECT dept_id FROM department WHERE LOWER(dept_name) = %s", (studentDept.lower(),))
                dept_row = cursor.fetchone()
                if not dept_row:
                    cursor.execute("INSERT INTO department(dept_name) VALUES (%s)", (studentDept,))
                    dept_id = cursor.lastrowid
                else:
                    dept_id = dept_row[0]

                # Insert new class
                cursor.execute("INSERT INTO class(class_name, dept_id) VALUES (%s, %s)", (studentClass, dept_id))
                class_id = cursor.lastrowid

            # Insert into student (MySQL auto-increment student_id)
            cursor.execute("""
                INSERT INTO student(user_id, name, class_id, dept_id)
                VALUES (%s, %s, %s, %s)
            """, (user_id, studentName, class_id, dept_id))

            connection.commit()

        except Exception as e:
            connection.rollback()
            print("Error:", e)
        finally:
            cursor.close()
            connection.close()

    return render_template('addstudent.html')

@app.route('/viewstudents', methods=["GET", "POST"])
def viewstudents():
    students = []
    departments = ["AIDS", "CSC", "ECE", "AIML", "IT", "EEE"]

    if request.method == 'POST':
        delete_id = request.form.get('delete_id')
        if delete_id:
            try:
                delete_id = int(delete_id)
                connection = connectdb()
                cursor = connection.cursor()

                # Get user_id for the student
                cursor.execute("SELECT user_id FROM student WHERE student_id = %s", (delete_id,))
                user_row = cursor.fetchone()

                if user_row:
                    user_id = user_row[0]

                    # Delete related results
                    cursor.execute("DELETE FROM result_for_each_question WHERE student_id = %s", (delete_id,))
                    cursor.execute("DELETE FROM result_for_quiz WHERE student_id = %s", (delete_id,))

                    # Delete student
                    cursor.execute("DELETE FROM student WHERE student_id = %s", (delete_id,))

                    # Delete user
                    cursor.execute("DELETE FROM app_user WHERE user_id = %s", (user_id,))

                    connection.commit()
                    flash("Student deleted successfully!", "success")
                else:
                    flash("Student not found!", "warning")

            except Exception as e:
                connection.rollback()
                flash(f"Error deleting student: {e}", "danger")
            finally:
                cursor.close()
                connection.close()

    try:
        connection = connectdb()
        cursor = connection.cursor()

        # Fetch all students with class and department names
        query = """
        SELECT s.student_id, s.name, u.email, u.username, u.password_hash,
               c.class_name, d.dept_name
        FROM student s
        JOIN app_user u ON s.user_id = u.user_id
        JOIN class c ON s.class_id = c.class_id
        JOIN department d ON s.dept_id = d.dept_id
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            students.append({
                "student_id": row[0],
                "name": row[1],
                "email": row[2],
                "username": row[3],
                "password": row[4],
                "class_name": row[5],
                "department": row[6]
            })

        if not students:
            students = [{
                "student_id": 0,
                "name": "N/A",
                "email": "N/A",
                "username": "N/A",
                "password": "N/A",
                "class_name": "N/A",
                "department": "N/A"
            }]

    except Exception as e:
        flash(f"Error fetching students: {e}", "danger")
    finally:
        cursor.close()
        connection.close()

    return render_template('viewstudents.html', students=students, departments=departments)

@app.route('/editstudent/<int:student_id>', methods=["GET", "POST"])
def editstudent(student_id):
    student = None
    try:
        connection = connectdb()
        cursor = connection.cursor()

        # Fetch current student info with JOIN
        query = """
        SELECT s.student_id, s.name, u.email, u.username, u.password_hash,
               c.class_name, d.dept_name
        FROM student s
        JOIN app_user u ON s.user_id = u.user_id
        JOIN class c ON s.class_id = c.class_id
        JOIN department d ON s.dept_id = d.dept_id
        WHERE s.student_id = %s
        """
        cursor.execute(query, (student_id,))
        row = cursor.fetchone()

        if row:
            student = {
                "student_id": row[0],
                "name": row[1],
                "email": row[2],
                "username": row[3],
                "password": row[4],
                "class_name": row[5],
                "department": row[6]
            }
        else:
            return "Student not found", 404

    except Exception as e:
        print("Error fetching student:", e)
        return "Internal Server Error", 500
    finally:
        if connection:
            cursor.close()
            connection.close()

    # Handle POST
    if request.method == "POST":
        studentName = request.form.get("name")
        studentClass = request.form.get("class_name")
        studentDept = request.form.get("department")
        email = request.form.get("email")
        password = request.form.get("password")

        try:
            connection = connectdb()
            cursor = connection.cursor()

            # 1. Update user info
            cursor.execute("""
                UPDATE app_user 
                SET email = %s, password_hash = %s 
                WHERE user_id = (SELECT user_id FROM student WHERE student_id = %s)
            """, (email, password, student_id))

            # 2. Update student name
            cursor.execute("""
                UPDATE student SET name = %s WHERE student_id = %s
            """, (studentName, student_id))

            # 3. Check if department exists
            cursor.execute("SELECT dept_id FROM department WHERE dept_name = %s", (studentDept,))
            deptdetails = cursor.fetchone()

            if not deptdetails:
                cursor.execute("INSERT INTO department (dept_name) VALUES (%s)", (studentDept,))
                dept_id = cursor.lastrowid
            else:
                dept_id = deptdetails[0]

            # 4. Check if class exists
            cursor.execute("SELECT class_id FROM class WHERE class_name = %s", (studentClass,))
            classdetails = cursor.fetchone()

            if not classdetails:
                cursor.execute("INSERT INTO class (class_name, dept_id) VALUES (%s, %s)", (studentClass, dept_id))
                class_id = cursor.lastrowid
            else:
                class_id = classdetails[0]

            # 5. Update student's class and department
            cursor.execute("""
                UPDATE student
                SET class_id = %s,
                    dept_id = %s
                WHERE student_id = %s
            """, (class_id, dept_id, student_id))

            connection.commit()
            return redirect(url_for('viewstudents'))

        except Exception as e:
            if connection:
                connection.rollback()
            print("Error updating student:", e)
        finally:
            if connection:
                cursor.close()
                connection.close()

    return render_template('editstudent.html', student=student)

@app.route("/student_dashboard")
def student_dashboard():
    student_id = session.get("student_id")
    class_id = session.get("class_id")
    if not student_id:
        return redirect(url_for("login"))

    quizzes = []

    try:
        connection = connectdb()
        cursor = connection.cursor()

        now = datetime.now()

        query = """
            SELECT quiz_id, name, subject, start_date, end_date, duration_minutes, 
                   no_of_question, mark_per_question, starttime, endtime, status
            FROM quiz
            WHERE class_id = %s
            ORDER BY start_date ASC
        """
        cursor.execute(query, (class_id,))

        for row in cursor.fetchall():
            quiz_id, name, subject, start_date, end_date, duration_minutes, no_of_question, mark_per_question, starttime_str, endtime_str, status = row

            # Parse start and end times
            try:
                start_time = datetime.strptime(starttime_str.strip().lower(), "%I:%M %p").time()
            except:
                start_time = datetime.strptime("12:00 AM", "%I:%M %p").time()

            try:
                end_time = datetime.strptime(endtime_str.strip().lower(), "%I:%M %p").time()
            except:
                end_time = datetime.strptime("11:59 PM", "%I:%M %p").time()

            # Combine with dates
            quiz_start = datetime.combine(start_date, start_time)
            quiz_end = datetime.combine(end_date, end_time)

            # Update status based on current datetime
            if now < quiz_start and status != 'upcoming':
                cursor.execute("UPDATE quiz SET status='upcoming' WHERE quiz_id=%s", (quiz_id,))
                connection.commit()
                status = 'upcoming'
            elif quiz_start <= now <= quiz_end and status != 'active':
                cursor.execute("UPDATE quiz SET status='active' WHERE quiz_id=%s", (quiz_id,))
                connection.commit()
                status = 'active'
            elif now > quiz_end and status != 'inactive':
                cursor.execute("UPDATE quiz SET status='inactive' WHERE quiz_id=%s", (quiz_id,))
                connection.commit()
                status = 'inactive'

            # Only show active quizzes
            if status == 'active':
                quizzes.append({
                    'quiz_id': quiz_id,
                    'name': name,
                    'subject': subject,
                    'start_date': start_date.strftime("%Y-%m-%d"),
                    'end_date': end_date.strftime("%Y-%m-%d"),
                    'duration_minutes': duration_minutes,
                    'no_of_question': no_of_question,
                    'mark_per_question': mark_per_question,
                    'starttime': starttime_str,
                    'endtime': endtime_str,
                    'status': status
                })

    except Exception as e:
        print(f"Error: {e}")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return render_template("studenthomepage.html", quizzes=quizzes)

@app.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
def quiz(quiz_id):
    student_id = session.get("student_id")
    if not student_id:
        return redirect(url_for('login'))

    conn = None
    cursor = None

    try:
        conn = connectdb()
        cursor = conn.cursor()

        # Check if student already attempted
        cursor.execute("""
            SELECT COUNT(*) FROM result_for_quiz
            WHERE quiz_id = %s AND student_id = %s
        """, (quiz_id, student_id))
        if cursor.fetchone()[0] > 0:
            return redirect(url_for('show_result', student_id=student_id, quiz_id=quiz_id))

        # Fetch start_date, starttime, duration
        cursor.execute("""
            SELECT start_date, starttime, duration_minutes
            FROM quiz
            WHERE quiz_id = %s
        """, (quiz_id,))
        quiz_row = cursor.fetchone()

        if not quiz_row:
            return "<h3>❌ Quiz not found.</h3>"

        start_date, start_time_str, duration_minutes = quiz_row

        # Combine date and time
        try:
            start_time_obj = datetime.strptime(start_time_str.strip(), "%I:%M %p").time()
        except ValueError:
            return "<h3>⚠️ Invalid start time format in DB. Use format like '08:00 AM'.</h3>"

        quiz_start_datetime = datetime.combine(start_date, start_time_obj)
        current_datetime = datetime.now()

        if current_datetime < quiz_start_datetime:
            return f"<h3>⏳ The quiz hasn't started yet. It will be available at {start_time_str} on {start_date.strftime('%Y-%m-%d')}.</h3>"

        # If POST, save answers
        if request.method == 'POST':
            answers = {int(key[1:]): val if val else None for key, val in request.form.items() if key.startswith('q')}

            # Insert into result_for_quiz
            cursor.execute("""
                INSERT INTO result_for_quiz (quiz_id, student_id, total_mark)
                VALUES (%s, %s, 0)
            """, (quiz_id, student_id))
            result_id = cursor.lastrowid

            total_marks = 0

            for question_id, student_ans in answers.items():
                cursor.execute("""
                    SELECT question, op1, op2, op3, op4, correct_answer, mark
                    FROM quiz_question
                    WHERE question_id = %s
                """, (question_id,))
                row = cursor.fetchone()
                if not row:
                    continue

                question_text, op1, op2, op3, op4, correct_answer, mark_per_question = row
                obtained_mark = mark_per_question if student_ans == correct_answer else 0
                total_marks += obtained_mark

                cursor.execute("""
                    INSERT INTO result_for_each_question (
                        quiz_id, question_id, student_id, question, op1, op2, op3, op4,
                        crt_ans, student_ans
                    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (quiz_id, question_id, student_id, str(question_text), str(op1), str(op2), str(op3), str(op4), correct_answer, student_ans))

            cursor.execute("""
                UPDATE result_for_quiz SET total_mark = %s WHERE result_id = %s
            """, (total_marks, result_id))

            conn.commit()
            return redirect(url_for('student_dashboard'))

        # If GET, fetch quiz questions
        cursor.execute("""
            SELECT question_id, question, op1, op2, op3, op4
            FROM quiz_question
            WHERE quiz_id = %s
        """, (quiz_id,))

        rows = cursor.fetchall()
        if not rows:
            return "<h3>⚠️ No questions found for this quiz.</h3>"

        quiz_data = []
        for r in rows:
            quiz_data.append({
                "question_id": r[0],
                "question": str(r[1]),
                "option1": str(r[2]),
                "option2": str(r[3]),
                "option3": str(r[4]),
                "option4": str(r[5])
            })

        duration = duration_minutes * 60  # seconds

        return render_template("attendquiz.html", quiz_data=quiz_data, duration=duration)

    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
        return f"<h3>❌ An error occurred: {str(e)}</h3>"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/result/<int:student_id>/<int:quiz_id>')
def show_result(student_id, quiz_id):
    conn = None
    cursor = None
    try:
        conn = connectdb()
        cursor = conn.cursor()

        # Fetch total marks obtained
        cursor.execute("""
            SELECT total_mark 
            FROM result_for_quiz 
            WHERE quiz_id = %s AND student_id = %s
        """, (quiz_id, student_id))
        row = cursor.fetchone()
        if not row:
            return "<h3>Result not found!</h3>"
        total_mark = row[0]

        # Fetch per-question details
        cursor.execute("""
            SELECT question, op1, op2, op3, op4, crt_ans, student_ans
            FROM result_for_each_question
            WHERE quiz_id = %s AND student_id = %s
            ORDER BY result_for_each_question_id
        """, (quiz_id, student_id))

        questions = []
        for q in cursor.fetchall():
            question_text, op1, op2, op3, op4, crt_ans, student_ans = q
            options = [op1, op2, op3, op4]
            correct = student_ans == crt_ans

            # Convert numeric choice to option text if stored as 'q1', 'q2', etc.
            student_text = ""
            crt_text = ""
            try:
                if student_ans:
                    student_index = int(student_ans[-1]) - 1
                    if 0 <= student_index < 4:
                        student_text = options[student_index]
                if crt_ans:
                    crt_index = int(crt_ans[-1]) - 1
                    if 0 <= crt_index < 4:
                        crt_text = options[crt_index]
            except Exception:
                pass

            questions.append({
                "question": question_text,
                "options": options,
                "crt_ans": crt_ans,
                "student_ans": student_ans,
                "correct": correct,
                "student_text": student_text,
                "crt_text": crt_text
            })

        # Fetch total possible marks
        cursor.execute("SELECT total_marks FROM quiz WHERE quiz_id=%s", (quiz_id,))
        total_marks_row = cursor.fetchone()
        total_marks = total_marks_row[0] if total_marks_row else 0

        return render_template(
            "show_result.html",
            total_mark=total_mark,
            questions=questions,
            total_marks=total_marks
        )

    except Exception as e:
        if conn:
            conn.rollback()
        return f"Error: {str(e)}"

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/overallresults/<int:quiz_id>', methods=["GET","POST"])
def overallresults(quiz_id):
    if 'teacher_id' not in session:
        return redirect(url_for("login"))

    students = []
    try:
        connection = connectdb()
        cursor = connection.cursor()

        # Fetch quiz start_date
        cursor.execute("SELECT start_date FROM quiz WHERE quiz_id=%s", (quiz_id,))
        start_date_row = cursor.fetchone()
        if not start_date_row:
            return "<h3>Quiz not found.</h3>"

        start_date = start_date_row[0].date() if isinstance(start_date_row[0], datetime) else start_date_row[0]
        cur_date = datetime.now().date()

        if cur_date < start_date:
            return "<h3>Overall results will be available after the quiz date.</h3>"

        # Fetch all student results
        query = """
            SELECT 
                s.name AS student_name,
                r.quiz_id,
                r.total_mark,
                s.student_id,
                q.total_marks AS quiz_total_marks
            FROM result_for_quiz r
            JOIN student s ON r.student_id = s.student_id
            JOIN quiz q ON r.quiz_id = q.quiz_id
            WHERE r.quiz_id = %s
            ORDER BY s.name ASC
        """
        cursor.execute(query, (quiz_id,))
        results = cursor.fetchall()

        for result in results:
            students.append({
                "name": result[0],
                "quiz_id": result[1],
                "marks": result[2],
                "student_id": result[3],
                "total_marks": result[4]
            })

    except Exception as e:
        print(f"Error fetching overall results: {e}")
        students = []

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return render_template("overallresults.html", students=students, quiz_id=quiz_id)

@app.route('/studentprofile')
def studentprofile():
    if "student_id" not in session:
        return redirect(url_for("login"))  
    return render_template("studentprofile.html", student=session)

@app.route("/edit_quiz/<int:quiz_id>", methods=["GET", "POST"])
def edit_quiz(quiz_id):
    if "teacher_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None
    try:
        connection = connectdb()
        cursor = connection.cursor()

        if request.method == "POST":
            # Get form data
            quiz_name = request.form.get("quiz_name", "").strip()
            subject = request.form.get("subject", "").strip()
            classname = request.form.get("classname", "").strip()
            deptname = request.form.get("deptname", "").strip()
            duration = int(request.form.get("duration") or 0)
            start_date = request.form.get("start_date")
            start_time = request.form.get("start_time")
            start_ampm = request.form.get("start_ampm")
            end_date = request.form.get("end_date")
            end_time = request.form.get("end_time")
            end_ampm = request.form.get("end_ampm")

            # Validations
            if not quiz_name:
                flash("Quiz name cannot be empty!", "error")
                return redirect(url_for("edit_quiz", quiz_id=quiz_id))
            if not subject:
                flash("Subject cannot be empty!", "error")
                return redirect(url_for("edit_quiz", quiz_id=quiz_id))
            if duration <= 0:
                flash("Duration must be greater than 0!", "error")
                return redirect(url_for("edit_quiz", quiz_id=quiz_id))

            # Validate class exists
            cursor.execute("SELECT class_id FROM class WHERE class_name=%s", (classname,))
            class_row = cursor.fetchone()
            if not class_row:
                flash(f"Class '{classname}' does not exist!", "error")
                return redirect(url_for("edit_quiz", quiz_id=quiz_id))
            class_id = class_row[0]

            # Validate department exists
            cursor.execute("SELECT dept_id FROM department WHERE dept_name=%s", (deptname,))
            dept_row = cursor.fetchone()
            if not dept_row:
                flash(f"Department '{deptname}' does not exist!", "error")
                return redirect(url_for("edit_quiz", quiz_id=quiz_id))
            dept_id = dept_row[0]

            # Validate start < end datetime
            start_dt = datetime.strptime(f"{start_date} {start_time} {start_ampm}", "%Y-%m-%d %I:%M %p")
            end_dt = datetime.strptime(f"{end_date} {end_time} {end_ampm}", "%Y-%m-%d %I:%M %p")
            if start_dt >= end_dt:
                flash("Start date/time must be before end date/time!", "error")
                return redirect(url_for("edit_quiz", quiz_id=quiz_id))

            # Determine status
            status = "active" if end_dt > datetime.now() else "inactive"

            # ✅ Update quiz (MySQL version)
            cursor.execute("""
                UPDATE quiz SET 
                    name=%s, subject=%s, class_id=%s, dept_id=%s,
                    duration_minutes=%s, start_date=%s, starttime=%s,
                    end_date=%s, endtime=%s, status=%s
                WHERE quiz_id=%s
            """, (
                quiz_name, subject, class_id, dept_id, duration,
                start_date, f"{start_time} {start_ampm}",
                end_date, f"{end_time} {end_ampm}", status, quiz_id
            ))

            connection.commit()
            flash("Quiz updated successfully!", "success")
            return redirect(url_for("activequizzes"))

        # ✅ GET request: fetch quiz info (MySQL version)
        cursor.execute("SELECT * FROM quiz WHERE quiz_id=%s", (quiz_id,))
        quiz_row = cursor.fetchone()

        cursor.execute("SELECT class_name FROM class WHERE class_id=%s", (quiz_row[3],))
        class_name = cursor.fetchone()[0]

        cursor.execute("SELECT dept_name FROM department WHERE dept_id=%s", (quiz_row[4],))
        dept_name = cursor.fetchone()[0]

        quiz = {
            'quiz_id': quiz_id,
            'quiz_name': quiz_row[1],
            'subject': quiz_row[2],
            'classname': class_name,
            'deptname': dept_name,
            'duration': quiz_row[9],
            'start_date': quiz_row[7].strftime("%Y-%m-%d"),
            'start_time': quiz_row[11].split()[0],
            'start_ampm': quiz_row[11].split()[1],
            'end_date': quiz_row[8].strftime("%Y-%m-%d"),
            'end_time': quiz_row[12].split()[0],
            'end_ampm': quiz_row[12].split()[1]
        }

    except Exception as e:
        print(f"Error: {e}")
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for("activequizzes"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return render_template("edit_quiz.html", quiz=quiz)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)

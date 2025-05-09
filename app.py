from flask import Flask, request, render_template, redirect, url_for, session, flash, send_file
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors
import hashlib
import os
from werkzeug.utils import secure_filename


app = Flask(__name__)  # Initialize Flask
app.secret_key = 'alkdsajdaklsdjsalkdsa'
bcrypt = Bcrypt(app)

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'interview_system'

mysql = MySQL(app)  # Initialize MySQL

app.config['UPLOAD_FOLDER'] = 'uploads'  # Define it here
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)  # Now it won't throw an error

@app.route('/')
def index():
  return render_template('index.html')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config.get('ALLOWED_EXTENSIONS', set())

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        resume = request.files['resume']  # Get uploaded file

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return redirect(url_for('login', exists=True))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Validate and save resume
        if resume and allowed_file(resume.filename):
            filename = secure_filename(resume.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            resume.save(file_path)

            # Store user data including resume path
            cursor.execute("INSERT INTO users (username, email, password_hash, resume_path) VALUES (%s, %s, %s, %s)",
                           (username, email, hashed_password, file_path))
            mysql.connection.commit()
            cursor.close()

            flash("Sign-up successful! Resume uploaded.", "success")
            return redirect(url_for('login'))
        else:
            flash("Please upload a valid PDF resume.", "danger")
            return redirect(url_for("signup"))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None

    if request.args.get("exists"):
        error_message = "User already exists. Please log in."

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.check_password_hash(user['password_hash'], password):
            session['loggedin'] = True
            session['username'] = user['username']
            session['user_id'] = user['id']
            return redirect(url_for('interview'))
        else:
            error_message = "Invalid credentials!"

    return render_template('login.html', error=error_message)

############################################### - Interview.html

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()

    keyword_map = {
            1: ["background", "experience", "strengths", "achievements", "goals"],
            2: ["interpreted", "dynamic", "object-oriented", "libraries", "cross-platform"],
            3: ["mutable", "immutable", "unordered", "indexing", "performance"],
            4: ["constructor", "initialization", "object creation", "parameters", "self"],
            5: ["garbage collection", "reference counting", "heap", "optimization", "PEP 3121"],
            6: ["string", "integer", "float", "list", "dictionary"],
            7: ["copy module", "references", "memory", "deepcopy()", "shallow copy"],
            8: ["encapsulation", "inheritance", "polymorphism", "abstraction", "objects"],
            9: ["MRO", "super()", "diamond problem", "parent classes", "overriding"],
            10: ["@classmethod", "@staticmethod", "self", "instance", "bound method"],
            11: ["iterable", "next()", "StopIteration", "generator", "loop"],
            12: ["yield", "lazy evaluation", "memory efficiency", "iterators", "performance"],
            13: ["try-except", "raise", "error handling", "exception hierarchy", "logging"],
            14: ["debugging", "AssertionError", "validation", "try-except", "runtime handling"],
            15: ["unittest", "pytest", "assertions", "test cases", "mocking"],
            16: ["@decorator", "functions", "wrapping", "higher order", "DRY principle"],
            17: ["threads", "concurrency", "CPython", "performance", "memory management"],
            18: ["with statement", "__enter__", "__exit__", "resource management", "file handling"],
            19: ["LIFO", "push", "pop", "data structure", "list"],
            20: ["slice notation", "[::-1]", "reverse()", "iteration", "recursion"],
            21: ["dictionary", "frequency count", "OrderedDict", "iteration", "optimization"],
            22: ["micro vs full-stack", "routing", "ORM", "flexibility", "scalability"],
            23: ["migration scripts", "makemigrations", "migrate", "models", "schema changes"],
            24: ["CRUD", "Flask/Django", "HTTP methods", "JSON", "endpoints"],
            25: ["cloud", "Docker", "CI/CD", "virtual environment", "performance"],
            26: ["containers", "image", "virtualization", "orchestration", "dependencies"],
            27: ["pip", "virtualenv", "requirements.txt", "Poetry", "environment isolation"],
            28: ["debugging", "logging", "exception handling", "root cause analysis", "fix"],
            29: ["documentation", "blogs", "conferences", "open source", "latest features"],
            30: ["culture", "growth", "contribution", "values", "mission"]
        }

    if request.method == 'POST':
        user_id = session.get('user_id')  # Ensure user ID is stored in session

        # Get highest attempt number
        cursor.execute("SELECT MAX(attempt_number) AS max_attempt FROM interview_responses WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        max_attempt = result['max_attempt'] if result['max_attempt'] else 0

        attempt_number = max_attempt + 1

        # Loop through questions and insert responses
        for question in questions:
            response_text = request.form.get(f"q{question['id']}")
            if response_text:  # Only insert if there is a response
                cursor.execute(
                    "INSERT INTO interview_responses (user_id, question_id, attempt_number, response) VALUES (%s, %s, %s, %s)",
                    (user_id, question['id'], attempt_number, response_text)
                )

                score = sum(1 for keyword in keyword_map.get(question['id'], []) if keyword.lower() in response_text.lower())

                cursor.execute(
                    "INSERT INTO interview_scores (user_id, question_id, attempt_number, score) VALUES (%s, %s, %s, %s)",
                    (user_id, question['id'], attempt_number, score)
                )

        mysql.connection.commit()
        cursor.close()
        
        # Redirect to completion page
        return redirect(url_for('completion'))

    cursor.close()
    return render_template('interview.html', questions=questions)

############################################################## -- Interview.html

@app.route('/completion')
def completion():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    return render_template('completion.html')

@app.route('/employer_login', methods=['GET', 'POST'])
def employer_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Fetch employer data
        cursor.execute("SELECT * FROM employers WHERE email = %s", (email,))
        employer = cursor.fetchone()
        cursor.close()

        if employer and employer['password_hash'] == hashlib.sha256(password.encode()).hexdigest():
            session['employer_loggedin'] = True
            session['employer_id'] = employer['id']
            return redirect(url_for('employer_dashboard'))  # Redirect to dashboard

        flash("Invalid email or password. Please try again.", "error")  # Show error
        return redirect(url_for('employer_login'))

    return render_template('employer_login.html')

@app.route('/employer_dashboard')
def employer_dashboard():
    if 'employer_loggedin' not in session:
        return redirect(url_for('employer_login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch categorized candidate statistics
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT user_id) AS total_candidates,

            -- Eligible: At least one answer with score >=4 in the first attempt
            COUNT(DISTINCT CASE WHEN score >= 4 AND attempt_number = 1 THEN user_id END) AS eligible_candidates,

            -- Saved: Candidates averaging between 3.0 and 3.99 over multiple attempts
            COUNT(DISTINCT CASE WHEN score BETWEEN 3 AND 3.99 AND attempt_number > 1 THEN user_id END) AS saved_candidates,

            -- Pending: Candidates with at least one answer <3
            COUNT(DISTINCT CASE WHEN score < 3 THEN user_id END) AS pending_candidates
        FROM interview_scores
    """)
    stats = cursor.fetchone()

    if stats['total_candidates'] > 0:  # Avoid division by zero
        stats['eligible_percent'] = round((stats['eligible_candidates'] / stats['total_candidates']) * 100, 2)
        stats['saved_percent'] = round((stats['saved_candidates'] / stats['total_candidates']) * 100, 2)
        stats['pending_percent'] = round((stats['pending_candidates'] / stats['total_candidates']) * 100, 2)
    else:
        stats['eligible_percent'] = stats['saved_percent'] = stats['pending_percent'] = 0

    # Fetch leaderboard (Top Candidates)
    cursor.execute("""
        SELECT u.id AS user_id, u.username, 
            ROUND((SUM(s.score) / (COUNT(s.question_id) * 5)) * 100, 2) AS percentage_score,
            CASE 
                WHEN MIN(s.score) < 3 AND MAX(s.score) >= 4 THEN 'Eligible & Pending'
                WHEN MAX(s.score) >= 4 THEN 'Eligible'
                WHEN AVG(s.score) BETWEEN 3 AND 3.99 THEN 'Saved'
                ELSE 'Pending'
            END AS status
        FROM users u
        JOIN interview_scores s ON u.id = s.user_id
        GROUP BY u.id
        ORDER BY percentage_score DESC;
    """)
    leaderboard = cursor.fetchall()
    print(leaderboard)

    cursor.close()
    
    return render_template('employer_dashboard.html', stats=stats, leaderboard=leaderboard)

@app.route('/view_resume/<int:user_id>')
def view_resume(user_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT resume_path FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()

    if user and user["resume_path"]:
        return send_file(user["resume_path"], as_attachment=False)  # Opens the PDF in browser
    else:
        flash("Resume not found.", "danger")
        return redirect(url_for("employer_dashboard"))

if __name__ == '__main__':
  app.run(debug=True)
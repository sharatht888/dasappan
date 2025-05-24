from flask import Flask, request, render_template, redirect, url_for, session, flash, send_file, jsonify
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors
import hashlib
import os
from werkzeug.utils import secure_filename
import cohere
import numpy as np
import cv2

co = cohere.Client("HLq3omnEaFgsZ5v4qc7A7oqeZj9kwVzO2bfn1czP")


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
reference_answers = {
    1: "I'm a Python developer with X years of experience in web applications and automation. My strengths include backend development, database management, and API integrations.",
    2: "Python is an interpreted, high-level, dynamically typed language with extensive libraries, cross-platform compatibility, and support for object-oriented programming.",
    3: "Lists are ordered and mutable, tuples are ordered and immutable, and sets are unordered collections that do not allow duplicate values.",
    4: "The __init__ method initializes object attributes when an instance is created, allowing for custom initialization.",
    5: "Python manages memory using automatic garbage collection, reference counting, and heap memory allocation.",
    6: "Python's built-in data types include strings, integers, floats, lists, tuples, dictionaries, sets, and booleans.",
    7: "Shallow copies create a new object but reference the same elements, while deep copies create completely independent copies of the elements.",
    8: "Python's OOP principles include encapsulation, inheritance, polymorphism, and abstraction, which help organize and reuse code efficiently.",
    9: "Python uses the Method Resolution Order (MRO) and the C3 linearization algorithm to handle multiple inheritance and determine attribute lookup order.",
    10: "Class methods operate on the class itself using @classmethod, while static methods don't require a class instance and use @staticmethod.",
    11: "An iterator in Python is an object that implements the __iter__() and __next__() methods, allowing sequential traversal through elements.",
    12: "Generators are special iterators that use the yield keyword to produce values lazily, improving memory efficiency.",
    13: "Python handles exceptions using try-except blocks, allowing developers to gracefully catch and handle runtime errors.",
    14: "Assertions check conditions during debugging, while exceptions handle runtime errors dynamically with try-except blocks.",
    15: "Unit testing in Python can be performed using the unittest or pytest libraries, leveraging assertions to validate expected behavior.",
    16: "Decorators in Python modify functions or methods dynamically by wrapping them within another function using @decorator syntax.",
    17: "The Global Interpreter Lock (GIL) in Python ensures thread safety but limits true parallel execution in multi-threaded programs.",
    18: "Context managers use the 'with' statement and __enter__/__exit__ methods to handle resource management cleanly.",
    19: "A stack in Python can be implemented using a list with append() for push and pop() for removal, following LIFO principles.",
    20: "A string can be reversed in Python using slice notation [::-1] or the reverse() method on a list.",
    21: "To find the first non-repeating character in a string, use a dictionary to track occurrences and return the first unique entry.",
    22: "Django is a full-stack framework with built-in ORM and authentication, while Flask is lightweight, micro-framework providing flexibility.",
    23: "Database migrations in Django are handled using makemigrations and migrate commands to reflect schema changes in the database.",
    24: "A RESTful API follows HTTP methods like GET, POST, PUT, DELETE, using Flask or Django to create structured web services.",
    25: "Python applications can be deployed using Docker, AWS, Heroku, or cloud providers, ensuring portability and scalability.",
    26: "Docker enables containerization of Python applications, packaging dependencies and runtime in an isolated environment.",
    27: "Dependencies in Python projects are managed using pip, virtual environments, requirements.txt, or Poetry for isolation.",
    28: "A challenging bug I encountered involved a circular import issue in Flask, which I resolved using blueprint restructuring.",
    29: "I stay updated with Python developments through documentation, conferences, blogs, open-source contributions, and official PEP proposals.",
    30: "I want to work with your company because it aligns with my skills, offers growth opportunities, and has an innovative technical culture."
}

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM questions")
    questions = cursor.fetchall()
    cursor.close()

    if request.method == 'POST':
        user_id = session.get('user_id')

        # Get highest attempt number
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT MAX(attempt_number) AS max_attempt FROM interview_responses WHERE user_id = %s", (user_id,))
        result = cursor.fetchone()
        max_attempt = result['max_attempt'] if result['max_attempt'] else 0
        attempt_number = max_attempt + 1

        user_answers = {}

        for question in questions:
            response_text = request.form.get(f"q{question['id']}")
            if response_text:
                user_answers[f"q{question['id']}"] = response_text  # ✅ Fix assignment
                
                cursor.execute(
                    "INSERT INTO interview_responses (user_id, question_id, attempt_number, response) VALUES (%s, %s, %s, %s)",
                    (user_id, question['id'], attempt_number, response_text)
                )

        # **Embed Cohere for Similarity Scoring**
        user_list = [user_answers[q] for q in user_answers]
        ref_list = [reference_answers.get(int(q.replace("q", "")), "") for q in user_answers]  # ✅ Fix reference answer retrieval

        user_embeddings = co.embed(texts=user_list).embeddings
        ref_embeddings = co.embed(texts=ref_list).embeddings

        # **Loop through user_answers and store scores properly**
        for idx, (question_id, response_text) in enumerate(user_answers.items()):
            similarity = cosine_similarity(user_embeddings[idx], ref_embeddings[idx])  # ✅ Ensure correct indexing

            if similarity > 0.85:
                score = 4
            elif similarity > 0.65:
                score = 2
            else:
                score = -1

            cursor.execute(
                "INSERT INTO interview_scores (user_id, question_id, attempt_number, score) VALUES (%s, %s, %s, %s)",
                (user_id, question_id.replace("q", ""), attempt_number, score)
            )

        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('completion'))  # ✅ Moved outside the loop

    return render_template('interview.html', questions=questions)
    
def cosine_similarity(vec1, vec2):
    dot = sum(a * b for a, b in zip(vec1, vec2))
    mag1 = sum(a * a for a in vec1) ** 0.5
    mag2 = sum(b * b for b in vec2) ** 0.5
    return dot / (mag1 * mag2)
                

############################################################## -- Interview.html
@app.route("/failure")
def failure():
    return render_template("failure.html")

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

            COUNT(DISTINCT CASE WHEN attempt_number = 1 AND user_id IN (
                SELECT user_id FROM interview_scores GROUP BY user_id HAVING AVG(score) >= 3.5
            ) THEN user_id END) AS eligible_candidates,

            COUNT(DISTINCT CASE WHEN attempt_number > 1 AND user_id IN (
                SELECT user_id FROM interview_scores GROUP BY user_id HAVING AVG(score) BETWEEN 2.5 AND 3.99
            ) THEN user_id END) AS saved_candidates,

            COUNT(DISTINCT CASE WHEN user_id IN (
                SELECT user_id FROM interview_scores GROUP BY user_id HAVING AVG(score) < 2.5
            ) THEN user_id END) AS pending_candidates
        FROM interview_scores;
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
        SELECT 
            u.id AS user_id, 
            u.username, 
            ROUND(GREATEST(0, (SUM(s.score) / (COUNT(s.question_id) * 4.0)) * 100), 2) AS percentage_score, 
            CASE 
                WHEN ROUND((SUM(s.score) / (COUNT(s.question_id) * 4.0) * 100), 2) >= 70 THEN 'Eligible'
                WHEN ROUND((SUM(s.score) / (COUNT(s.question_id) * 4.0) * 100), 2) >= 50 THEN 'Saved'
                WHEN ROUND((SUM(s.score) / (COUNT(s.question_id) * 4.0) * 100), 2) < 50 THEN 'Pending'
                ELSE 'Unknown'
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

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")


cheating_count = 0
max_cheating_limit = 10

@app.route("/cheat_detect", methods=["POST"])
def cheat_detect():
    global cheating_count

    file = request.files.get("image")
    if not file:
        print("❌ No Image Received!")
        return jsonify({"error": "No image provided"}), 400

    try:
        # Convert uploaded image into OpenCV format
        image = np.frombuffer(file.read(), dtype=np.uint8)
        img = cv2.imdecode(image, cv2.IMREAD_COLOR)

        if img is None or img.size == 0:
            print("❌ Image decoding failed or empty!")
            return jsonify({"error": "Image decoding error"}), 500

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Verify Cascade Classifier is loaded
        if face_cascade.empty():
            print("❌ Haar cascade file not loaded properly!")
            return jsonify({"error": "Cascade classifier failed"}), 500

        # Try detecting faces safely
        try:
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        except cv2.error as e:
            print(f"⚠️ OpenCV Error: {e}")
            return jsonify({"error": "Face detection error"}), 500

        print(f"✅ Detected {len(faces)} face(s)")

        # Ensure function exits properly if no faces are detected
        faces = faces if faces is not None else []

        # Update cheating logic
        if len(faces) == 0:
            cheating_count += 1
            status = "🚨 Face Not Detected!"
        elif len(faces) > 1:
            cheating_count += 2
            status = "⚠️ Multiple Faces Detected!"
        else:
            cheating_count = max(0, cheating_count - 0.5)
            status = "✅ Normal Behavior"

        if cheating_count >= max_cheating_limit:
            return jsonify({"redirect": "/failure", "status": "❌ Too many suspicious behaviors detected!"})

        return jsonify({
            "face_detected": len(faces) > 0,
            "cheating_attempts": int(cheating_count),
            "status": status
        })

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
  app.run(debug=True)
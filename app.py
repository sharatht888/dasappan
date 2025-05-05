from flask import Flask, request, render_template, redirect, url_for, session
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'root'
app.config['MYSQL_DB'] = 'interview_system'

mysql = MySQL(app)
bcrypt = Bcrypt(app)

@app.route('/')
def index():
    return render_template('index.html')  # Landing Page

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            return redirect(url_for('login', exists=True))  # Redirect with a flag

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        cursor.execute("INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s)",
                       (username, email, hashed_password))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None

    if request.args.get("exists"):
        error_message = "User already exists. Redirected from signup."

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
            return redirect(url_for('dashboard'))  # Redirect after login
        else:
            error_message = "Invalid credentials!"

    return render_template('login.html', error=error_message)

@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        return f"Welcome, {session['username']}!"
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

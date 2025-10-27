from flask import Flask, render_template, redirect, url_for, request, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
import datetime
import csv
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# User Model
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    currency = db.Column(db.String(10), default='USD')  # Multi-currency support
    monthly_budget = db.Column(db.Float, default=1000.0)  # Default budget

# Expense Model
class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, default=datetime.date.today)
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Home Route
@app.route('/')
def index():
    return render_template('index.html')

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        currency = request.form['currency']
        monthly_budget = float(request.form['monthly_budget'])
        user = User(username=username, password=password, currency=currency, monthly_budget=monthly_budget)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Try again!', 'danger')
    return render_template('login.html')

# Dashboard Route
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    expenses = Expense.query.filter_by(user_id=current_user.id)
    total_spent = sum(exp.amount for exp in expenses)
    budget_warning = total_spent > current_user.monthly_budget

    # Filtering expenses by date & category
    if request.method == "POST":
        category = request.form.get("category")
        date = request.form.get("date")
        if category:
            expenses = expenses.filter_by(category=category)
        if date:
            expenses = expenses.filter_by(date=date)

    expenses = expenses.all()

    categories = {expense.category: 0 for expense in expenses}
    for expense in expenses:
        categories[expense.category] += expense.amount

    return render_template('dashboard.html', expenses=expenses, categories=categories, total_spent=total_spent, budget_warning=budget_warning, currency=current_user.currency)

# Add Expense Route
@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        category = request.form['category']
        amount = float(request.form['amount'])
        description = request.form['description']
        new_expense = Expense(user_id=current_user.id, category=category, amount=amount, description=description)
        db.session.add(new_expense)
        db.session.commit()
        flash('Expense added successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('add_expense.html')

# Export CSV Route
@app.route('/export_csv')
@login_required
def export_csv():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Date', 'Category', 'Amount', 'Description'])
    for expense in expenses:
        writer.writerow([expense.date, expense.category, expense.amount, expense.description])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv", as_attachment=True, download_name="expenses.csv")

# Logout
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)

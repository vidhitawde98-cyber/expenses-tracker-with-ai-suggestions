import matplotlib
matplotlib.use("Agg")
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import matplotlib.pyplot as plt
import os
import base64
from io import BytesIO
import psycopg2
from psycopg2.extras import RealDictCursor

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST).replace(tzinfo=None)

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'vidhi-expense-tracker-secret-2024')

# PostgreSQL Configuration
DATABASE_URL = os.environ.get('DATABASE_URL', '')

def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    """Create tables if they don't exist"""
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            email VARCHAR(200) UNIQUE NOT NULL,
            password VARCHAR(300) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            icon VARCHAR(20) NOT NULL,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            category VARCHAR(100) NOT NULL,
            amount FLOAT NOT NULL,
            note TEXT DEFAULT '',
            date TIMESTAMP DEFAULT NOW()
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS budgets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            category VARCHAR(100) NOT NULL,
            amount FLOAT NOT NULL,
            UNIQUE(user_id, category)
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database tables initialized")

# Initialize DB on startup
with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"DB init error: {e}")

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '⚠️ Please log in to access this page.'
login_manager.login_message_category = 'warning'


class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.created_at = user_data.get('created_at')

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (int(user_id),))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        return User(user_data) if user_data else None

    @staticmethod
    def get_by_email(email):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        return User(user_data) if user_data else None

    @staticmethod
    def get_by_username(username):
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        return User(user_data) if user_data else None


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


def initialize_user_categories(user_id):
    default_categories = [
        ("Food", "🍔"),
        ("Entertainment", "🎭"),
        ("Shopping", "🛍️"),
        ("Bills", "📑"),
        ("Other", "💼")
    ]
    conn = get_db()
    cur = conn.cursor()
    for name, icon in default_categories:
        cur.execute(
            "INSERT INTO categories (name, icon, user_id) VALUES (%s, %s, %s)",
            (name, icon, user_id)
        )
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Initialized categories for user {user_id}")


# AUTHENTICATION ROUTES
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not username or not email or not password:
            flash('❌ All fields are required!', 'danger')
            return render_template('register.html')

        if len(username) < 3:
            flash('❌ Username must be at least 3 characters!', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('❌ Password must be at least 6 characters!', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('❌ Passwords do not match!', 'danger')
            return render_template('register.html')

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT id FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            flash('❌ Email already registered! Please login.', 'danger')
            cur.close(); conn.close()
            return render_template('register.html')

        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            flash('❌ Username already taken!', 'danger')
            cur.close(); conn.close()
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        cur.execute(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
            (username, email, hashed_password)
        )
        user_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()

        initialize_user_categories(user_id)

        flash(f'✅ Account created successfully! Welcome {username}!', 'success')
        user = User.get_by_email(email)
        login_user(user)
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        if not email or not password:
            flash('❌ Please enter both email and password!', 'danger')
            return render_template('login.html')

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()

        if not user_data or not check_password_hash(user_data['password'], password):
            flash('❌ Invalid email or password!', 'danger')
            return render_template('login.html')

        user = User(user_data)
        login_user(user, remember=remember)
        flash(f'✅ Welcome back, {user.username}!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('home'))

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    logout_user()
    flash(f'👋 Goodbye, {username}! You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/profile')
@login_required
def profile():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as count FROM expenses WHERE user_id = %s", (int(current_user.id),))
    total_expenses = cur.fetchone()['count']

    cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE user_id = %s", (int(current_user.id),))
    total_amount = int(cur.fetchone()['total'])

    cur.execute("SELECT COUNT(*) as count FROM categories WHERE user_id = %s", (int(current_user.id),))
    total_categories = cur.fetchone()['count']

    cur.execute("SELECT * FROM users WHERE id = %s", (int(current_user.id),))
    user_data = cur.fetchone()

    cur.close()
    conn.close()

    return render_template('profile.html',
                           total_expenses=total_expenses,
                           total_amount=total_amount,
                           total_categories=total_categories,
                           user_data=user_data)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (int(current_user.id),))
        user_data = cur.fetchone()

        if not check_password_hash(user_data['password'], old_password):
            flash('❌ Current password is incorrect!', 'danger')
            cur.close(); conn.close()
            return redirect(url_for('change_password'))

        if old_password == new_password:
            flash('❌ New password must be different from current password!', 'warning')
            cur.close(); conn.close()
            return redirect(url_for('change_password'))

        if len(new_password) < 6:
            flash('❌ New password must be at least 6 characters!', 'danger')
            cur.close(); conn.close()
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('❌ New passwords do not match!', 'danger')
            cur.close(); conn.close()
            return redirect(url_for('change_password'))

        hashed = generate_password_hash(new_password, method='pbkdf2:sha256')
        cur.execute("UPDATE users SET password = %s WHERE id = %s", (hashed, int(current_user.id)))
        conn.commit()
        cur.close()
        conn.close()

        flash('✅ Password changed successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('change_password.html')


@app.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_text = request.form.get('confirm_text', '').strip()

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = %s", (int(current_user.id),))
        user_data = cur.fetchone()

        if not check_password_hash(user_data['password'], password):
            flash('❌ Incorrect password!', 'danger')
            cur.close(); conn.close()
            return redirect(url_for('delete_account'))

        if confirm_text.upper() != 'DELETE':
            flash('❌ You must type DELETE to confirm!', 'danger')
            cur.close(); conn.close()
            return redirect(url_for('delete_account'))

        username = current_user.username
        cur.execute("DELETE FROM users WHERE id = %s", (int(current_user.id),))
        conn.commit()
        cur.close()
        conn.close()

        logout_user()
        flash(f'💔 Account deleted successfully. Goodbye, {username}!', 'info')
        return redirect(url_for('register'))

    return render_template('delete_account.html')


# MAIN APP ROUTES
@app.route('/')
@login_required
def home():
    categories = get_user_categories()
    return render_template("add_expense.html", categories=categories)


@app.route('/favicon.ico')
def favicon():
    return "", 204


@app.route('/add', methods=['POST'])
@login_required
def add_expense():
    category = request.form['category']
    amount = request.form['amount']
    note = request.form.get('note', '').strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO expenses (user_id, category, amount, note, date) VALUES (%s, %s, %s, %s, %s)",
        (int(current_user.id), category, float(amount), note, now_ist())
    )
    conn.commit()
    cur.close()
    conn.close()

    flash(f"✅ Expense of ₹{amount} added to {category} successfully!", 'success')
    return redirect(url_for('home'))


@app.route('/view')
@login_required
def view_expenses():
    category_filter = request.args.get('category', '')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    conn = get_db()
    cur = conn.cursor()

    query = "SELECT * FROM expenses WHERE user_id = %s"
    params = [int(current_user.id)]

    if category_filter:
        query += " AND LOWER(category) LIKE %s"
        params.append(f'%{category_filter.lower()}%')

    if start_date:
        query += " AND date >= %s"
        params.append(datetime.strptime(start_date, "%Y-%m-%d"))

    if end_date:
        query += " AND date <= %s"
        params.append(datetime.strptime(end_date, "%Y-%m-%d"))

    query += " ORDER BY date DESC"
    cur.execute(query, params)
    expenses_raw = cur.fetchall()
    cur.close()
    conn.close()

    expenses_list = [
        (exp['id'], exp['category'], exp['amount'],
         exp['date'].strftime('%Y-%m-%d %H:%M:%S'), exp.get('note', ''))
        for exp in expenses_raw
    ]

    return render_template("view_expenses.html", expenses=expenses_list)


@app.route('/delete/<expense_id>')
@login_required
def delete_expense(expense_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("DELETE FROM expenses WHERE id = %s AND user_id = %s",
                    (int(expense_id), int(current_user.id)))
        deleted = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()

        if deleted > 0:
            flash('🗑️ Expense deleted successfully!', 'success')
        else:
            flash('❌ Expense not found!', 'danger')
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')

    return redirect(url_for('view_expenses'))


@app.route('/edit/<expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT * FROM expenses WHERE id = %s AND user_id = %s",
                    (int(expense_id), int(current_user.id)))
        expense = cur.fetchone()

        if not expense:
            flash('❌ Expense not found!', 'danger')
            cur.close(); conn.close()
            return redirect(url_for('view_expenses'))

        if request.method == 'POST':
            category = request.form.get('category')
            amount = request.form.get('amount')
            note = request.form.get('note', '').strip()
            date_str = request.form.get('date')

            if not category or not amount:
                flash('❌ Category and amount are required!', 'danger')
                cur.close(); conn.close()
                return redirect(url_for('edit_expense', expense_id=expense_id))

            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else expense['date']
            except ValueError:
                flash('❌ Invalid date format!', 'danger')
                cur.close(); conn.close()
                return redirect(url_for('edit_expense', expense_id=expense_id))

            cur.execute(
                "UPDATE expenses SET category=%s, amount=%s, note=%s, date=%s WHERE id=%s AND user_id=%s",
                (category, float(amount), note, expense_date, int(expense_id), int(current_user.id))
            )
            conn.commit()
            cur.close()
            conn.close()
            flash('✅ Expense updated successfully!', 'success')
            return redirect(url_for('view_expenses'))

        categories = get_user_categories()
        cur.close()
        conn.close()
        return render_template('edit_expense.html', expense=expense, categories=categories)

    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('view_expenses'))


@app.route('/clear')
@login_required
def clear_expenses():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM expenses WHERE user_id = %s", (int(current_user.id),))
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    flash(f'🗑️ All {deleted} expenses deleted!', 'info')
    return redirect(url_for('view_expenses'))


@app.route('/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    if request.method == 'POST':
        action = request.form.get('action')
        conn = get_db()
        cur = conn.cursor()

        if action == 'add':
            category_name = request.form.get('category_name')
            category_icon = request.form.get('category_icon')
            if category_name and category_icon:
                cur.execute(
                    "INSERT INTO categories (name, icon, user_id) VALUES (%s, %s, %s)",
                    (category_name, category_icon, int(current_user.id))
                )
                conn.commit()
                flash(f'✅ Category "{category_name}" added!', 'success')
            else:
                flash('❌ Provide both name and icon!', 'danger')

        elif action == 'delete':
            category_name = request.form.get('category_delete')
            cur.execute(
                "DELETE FROM categories WHERE name = %s AND user_id = %s",
                (category_name, int(current_user.id))
            )
            if cur.rowcount > 0:
                conn.commit()
                flash(f'🗑️ Category "{category_name}" deleted!', 'success')

        cur.close()
        conn.close()
        return redirect(url_for('manage_categories'))

    categories = get_user_categories()
    return render_template("categories.html", categories=categories)


def get_user_categories():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT name, icon FROM categories WHERE user_id = %s", (int(current_user.id),))
    cats = cur.fetchall()
    cur.close()
    conn.close()
    return [{'name': c['name'], 'icon': c['icon']} for c in cats]


@app.route('/budget', methods=['GET', 'POST'])
@login_required
def manage_budget():
    if request.method == 'POST':
        category = request.form.get('category')
        budget_amount = request.form.get('budget_amount')

        if category and budget_amount:
            try:
                budget_amount = float(budget_amount)
                conn = get_db()
                cur = conn.cursor()
                cur.execute('''
                    INSERT INTO budgets (user_id, category, amount)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, category)
                    DO UPDATE SET amount = EXCLUDED.amount
                ''', (int(current_user.id), category, budget_amount))
                conn.commit()
                cur.close()
                conn.close()
                flash(f'✅ Budget of ₹{budget_amount} set for {category}!', 'success')
            except ValueError:
                flash('❌ Invalid budget amount!', 'danger')

        return redirect(url_for('manage_budget'))

    categories = get_user_categories()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT category, amount FROM budgets WHERE user_id = %s", (int(current_user.id),))
    budget_dict = {b['category']: b['amount'] for b in cur.fetchall()}

    start_of_month = now_ist().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    cur.execute('''
        SELECT category, SUM(amount) as spent
        FROM expenses
        WHERE user_id = %s AND date >= %s
        GROUP BY category
    ''', (int(current_user.id), start_of_month))
    spending_dict = {r['category']: r['spent'] for r in cur.fetchall()}
    cur.close()
    conn.close()

    budget_data = []
    for cat in categories:
        cat_name = cat['name']
        budget = budget_dict.get(cat_name, 0)
        spent = spending_dict.get(cat_name, 0)
        if budget > 0:
            percentage = (spent / budget) * 100
            status = 'danger' if percentage >= 100 else ('warning' if percentage >= 80 else 'success')
        else:
            percentage = 0
            status = 'secondary'
        budget_data.append({
            'category': cat_name, 'icon': cat['icon'],
            'budget': budget, 'spent': spent,
            'remaining': max(0, budget - spent),
            'percentage': min(100, percentage), 'status': status
        })

    return render_template('budget.html', categories=categories, budget_data=budget_data)


@app.route('/insights')
@login_required
def generate_insights():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE user_id = %s", (int(current_user.id),))
    expenses = cur.fetchall()

    category_totals = defaultdict(int)
    monthly_totals = defaultdict(int)
    total_expenses = 0
    max_expense = 0
    highest_category = "None"
    ai_warnings = []

    thresholds = {
        "Food": 0.3, "Entertainment": 0.15,
        "Shopping": 0.2, "Bills": 0.25, "Other": 0.1
    }

    for expense in expenses:
        amount = int(expense['amount'])
        category = expense['category']
        month = expense['date'].strftime("%Y-%m")
        total_expenses += amount
        category_totals[category] += amount
        monthly_totals[month] += amount
        if amount > max_expense:
            max_expense = amount
            highest_category = category

    if total_expenses > 0:
        start_of_month = now_ist().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        cur.execute("SELECT category, amount FROM budgets WHERE user_id = %s", (int(current_user.id),))
        budget_dict = {b['category']: b['amount'] for b in cur.fetchall()}

        cur.execute('''
            SELECT category, SUM(amount) as spent FROM expenses
            WHERE user_id = %s AND date >= %s GROUP BY category
        ''', (int(current_user.id), start_of_month))
        month_spending = {r['category']: r['spent'] for r in cur.fetchall()}

        for category, budget in budget_dict.items():
            spent = month_spending.get(category, 0)
            if spent > 0:
                percentage = (spent / budget) * 100
                if percentage >= 100:
                    ai_warnings.append({"type": "danger",
                        "message": f"🚨 BUDGET ALERT: You've exceeded your {category} budget by ₹{int(spent - budget)}!"})
                elif percentage >= 80:
                    ai_warnings.append({"type": "warning",
                        "message": f"⚠️ Budget Warning: Only ₹{int(budget - spent)} left in {category} budget!"})

        for category, spent in category_totals.items():
            percentage = spent / total_expenses
            if category in thresholds:
                if percentage > thresholds[category]:
                    ai_warnings.append({"type": "warning",
                        "message": f"⚠️ You are overspending on {category} ({percentage:.1%} of total). Consider reducing it!"})
                else:
                    ai_warnings.append({"type": "success",
                        "message": f"✅ Good job! Your {category} spending is within limits ({percentage:.1%})."})

    cur.close()
    conn.close()

    savings_recommendation = total_expenses * 0.2
    if not category_totals:
        category_totals = {"No Data": 1}

    category_chart = generate_pie_chart(category_totals) if len(category_totals) > 1 else None
    trend_chart = generate_line_chart(monthly_totals) if monthly_totals else None

    return render_template("insights.html",
                           total_expenses=total_expenses, max_expense=max_expense,
                           highest_category=highest_category, category_totals=category_totals,
                           category_chart=category_chart, trend_chart=trend_chart,
                           ai_warnings=ai_warnings, savings_recommendation=savings_recommendation)


@app.route('/download')
@login_required
def download_expenses():
    import tempfile
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE user_id = %s ORDER BY date DESC", (int(current_user.id),))
    expenses = cur.fetchall()
    cur.close()
    conn.close()

    if not expenses:
        flash('🚨 No expenses to download!', 'danger')
        return redirect(url_for('view_expenses'))

    csv_filename = f"expenses_{current_user.username}.csv"
    csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
    with open(csv_path, 'w') as f:
        f.write("Category,Amount,Date,Note\n")
        for exp in expenses:
            note = (exp.get('note', '') or '').replace(',', ';')
            f.write(f"{exp['category']},{exp['amount']},{exp['date'].strftime('%Y-%m-%d %H:%M:%S')},{note}\n")

    return send_file(csv_path, as_attachment=True, download_name=csv_filename, mimetype="text/csv")


# CHART GENERATION
def generate_pie_chart(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    amounts = [int(v) for v in data.values()]
    labels = list(data.keys())
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    explode = [0.05] * len(labels)
    ax.pie(amounts, labels=labels, autopct='%1.1f%%', startangle=140,
           colors=colors, explode=explode, shadow=True,
           textprops={'fontsize': 11, 'weight': 'bold', 'color': 'black'})
    ax.axis('equal')
    plt.title('Category-wise Spending Distribution', fontsize=14, weight='bold', pad=20, color='black')
    plt.tight_layout()
    return save_chart(fig)


def generate_line_chart(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    months = list(data.keys())
    amounts = list(data.values())
    ax.plot(months, amounts, marker='o', linestyle='-', color='#4ECDC4',
            linewidth=2.5, markersize=8, markerfacecolor='#FF6B6B',
            markeredgecolor='#fff', markeredgewidth=2)
    ax.set_title("Monthly Spending Trends", fontsize=14, weight='bold', pad=15, color='black')
    ax.set_xlabel("Month", fontsize=12, weight='bold', color='black')
    ax.set_ylabel("Total Spent (₹)", fontsize=12, weight='bold', color='black')
    ax.tick_params(axis='x', colors='black', labelsize=10)
    ax.tick_params(axis='y', colors='black', labelsize=10)
    plt.xticks(rotation=45, ha='right')
    ax.grid(True, alpha=0.3, linestyle='--', color='gray')
    for month, amount in zip(months, amounts):
        ax.annotate(f'₹{amount}', (month, amount),
                    textcoords="offset points", xytext=(0, 10),
                    ha='center', fontsize=9, weight='bold', color='black')
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
    plt.tight_layout()
    return save_chart(fig)


def save_chart(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=100, bbox_inches='tight')
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


@app.route('/download-pdf')
@login_required
def download_pdf():
    from pdf_generator import create_pdf_report
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM expenses WHERE user_id = %s ORDER BY date DESC", (int(current_user.id),))
    expenses = cur.fetchall()
    cur.close()
    conn.close()

    if not expenses:
        flash('🚨 No expenses to generate report!', 'danger')
        return redirect(url_for('view_expenses'))

    category_totals = defaultdict(int)
    for expense in expenses:
        category_totals[expense['category']] += int(expense['amount'])

    category_chart = generate_pie_chart(category_totals) if len(category_totals) > 1 else None
    pdf_buffer = create_pdf_report(expenses, current_user.username, category_chart)
    pdf_filename = f"expense_report_{current_user.username}_{now_ist().strftime('%Y%m%d')}.pdf"

    return send_file(pdf_buffer, as_attachment=True,
                     download_name=pdf_filename, mimetype='application/pdf')


if __name__ == '__main__':
    app.run(debug=True)
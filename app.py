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
from pymongo import MongoClient
from bson.objectid import ObjectId

IST = timezone(timedelta(hours=5, minutes=30))

def now_ist():
    return datetime.now(IST).replace(tzinfo=None)

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'vidhi-expense-tracker-secret-2024')

# ── MongoDB Configuration ─────────────────────────────────────────────────────
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb+srv://expense_user:V3YAsekV8Bd5euMo@expense-tracker.zhkwjlw.mongodb.net/expense_tracker?retryWrites=true&w=majority&appName=expense-tracker')

client = MongoClient(MONGO_URI)
db = client['expense_tracker']

# Collections
users_col      = db['users']
categories_col = db['categories']
expenses_col   = db['expenses']
budgets_col    = db['budgets']

# Create indexes for performance
users_col.create_index('email',    unique=True)
users_col.create_index('username', unique=True)
expenses_col.create_index('user_id')
categories_col.create_index('user_id')
budgets_col.create_index([('user_id', 1), ('category', 1)], unique=True)

print("✅ MongoDB connected and indexes created")

# ── Flask-Login Setup ─────────────────────────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '⚠️ Please log in to access this page.'
login_manager.login_message_category = 'warning'


class User(UserMixin):
    def __init__(self, user_data):
        self.id         = str(user_data['_id'])
        self.username   = user_data['username']
        self.email      = user_data['email']
        self.created_at = user_data.get('created_at')

    @staticmethod
    def get_by_id(user_id):
        try:
            user_data = users_col.find_one({'_id': ObjectId(user_id)})
            return User(user_data) if user_data else None
        except Exception:
            return None

    @staticmethod
    def get_by_email(email):
        user_data = users_col.find_one({'email': email})
        return User(user_data) if user_data else None


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_user_categories():
    cats = categories_col.find({'user_id': current_user.id})
    return [{'name': c['name'], 'icon': c['icon']} for c in cats]


def initialize_user_categories(user_id):
    default_categories = [
        ("Food", "🍔"), ("Entertainment", "🎭"),
        ("Shopping", "🛍️"), ("Bills", "📑"), ("Other", "💼")
    ]
    for name, icon in default_categories:
        categories_col.insert_one({'name': name, 'icon': icon, 'user_id': user_id})


# ── AUTHENTICATION ROUTES ─────────────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username         = request.form.get('username', '').strip()
        email            = request.form.get('email', '').strip().lower()
        password         = request.form.get('password', '')
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

        if users_col.find_one({'email': email}):
            flash('❌ Email already registered! Please login.', 'danger')
            return render_template('register.html')
        if users_col.find_one({'username': username}):
            flash('❌ Username already taken!', 'danger')
            return render_template('register.html')

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        result = users_col.insert_one({
            'username':   username,
            'email':      email,
            'password':   hashed_password,
            'created_at': now_ist()
        })
        user_id = str(result.inserted_id)
        initialize_user_categories(user_id)

        user = User.get_by_email(email)
        login_user(user)
        flash(f'✅ Account created successfully! Welcome {username}!', 'success')
        return redirect(url_for('home'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)

        if not email or not password:
            flash('❌ Please enter both email and password!', 'danger')
            return render_template('login.html')

        user_data = users_col.find_one({'email': email})
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
    total_expenses   = expenses_col.count_documents({'user_id': current_user.id})
    total_amount_res = list(expenses_col.aggregate([
        {'$match': {'user_id': current_user.id}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]))
    total_amount     = int(total_amount_res[0]['total']) if total_amount_res else 0
    total_categories = categories_col.count_documents({'user_id': current_user.id})
    user_data        = users_col.find_one({'_id': ObjectId(current_user.id)})

    return render_template('profile.html',
                           total_expenses=total_expenses,
                           total_amount=total_amount,
                           total_categories=total_categories,
                           user_data=user_data)


@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old_password     = request.form.get('old_password', '')
        new_password     = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        user_data = users_col.find_one({'_id': ObjectId(current_user.id)})

        if not check_password_hash(user_data['password'], old_password):
            flash('❌ Current password is incorrect!', 'danger')
            return redirect(url_for('change_password'))
        if old_password == new_password:
            flash('❌ New password must be different from current password!', 'warning')
            return redirect(url_for('change_password'))
        if len(new_password) < 6:
            flash('❌ New password must be at least 6 characters!', 'danger')
            return redirect(url_for('change_password'))
        if new_password != confirm_password:
            flash('❌ New passwords do not match!', 'danger')
            return redirect(url_for('change_password'))

        hashed = generate_password_hash(new_password, method='pbkdf2:sha256')
        users_col.update_one({'_id': ObjectId(current_user.id)}, {'$set': {'password': hashed}})
        flash('✅ Password changed successfully!', 'success')
        return redirect(url_for('profile'))

    return render_template('change_password.html')


@app.route('/delete-account', methods=['GET', 'POST'])
@login_required
def delete_account():
    if request.method == 'POST':
        password     = request.form.get('password', '')
        confirm_text = request.form.get('confirm_text', '').strip()

        user_data = users_col.find_one({'_id': ObjectId(current_user.id)})

        if not check_password_hash(user_data['password'], password):
            flash('❌ Incorrect password!', 'danger')
            return redirect(url_for('delete_account'))
        if confirm_text.upper() != 'DELETE':
            flash('❌ You must type DELETE to confirm!', 'danger')
            return redirect(url_for('delete_account'))

        uid = current_user.id
        username = current_user.username
        expenses_col.delete_many({'user_id': uid})
        categories_col.delete_many({'user_id': uid})
        budgets_col.delete_many({'user_id': uid})
        users_col.delete_one({'_id': ObjectId(uid)})
        logout_user()
        flash(f'💔 Account deleted successfully. Goodbye, {username}!', 'info')
        return redirect(url_for('register'))

    return render_template('delete_account.html')


# ── MAIN APP ROUTES ───────────────────────────────────────────────────────────
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
    amount   = request.form['amount']
    note     = request.form.get('note', '').strip()

    expenses_col.insert_one({
        'user_id':  current_user.id,
        'category': category,
        'amount':   float(amount),
        'note':     note,
        'date':     now_ist()
    })
    flash(f"✅ Expense of ₹{amount} added to {category} successfully!", 'success')
    return redirect(url_for('home'))


@app.route('/view')
@login_required
def view_expenses():
    category_filter = request.args.get('category', '')
    start_date      = request.args.get('start_date')
    end_date        = request.args.get('end_date')

    query = {'user_id': current_user.id}

    if category_filter:
        query['category'] = {'$regex': category_filter, '$options': 'i'}
    if start_date:
        query.setdefault('date', {})['$gte'] = datetime.strptime(start_date, "%Y-%m-%d")
    if end_date:
        query.setdefault('date', {})['$lte'] = datetime.strptime(end_date, "%Y-%m-%d")

    expenses_raw  = list(expenses_col.find(query).sort('date', -1))
    expenses_list = [
        (str(e['_id']), e['category'], e['amount'],
         e['date'].strftime('%Y-%m-%d %H:%M:%S'), e.get('note', ''))
        for e in expenses_raw
    ]
    return render_template("view_expenses.html", expenses=expenses_list)


@app.route('/delete/<expense_id>')
@login_required
def delete_expense(expense_id):
    try:
        result = expenses_col.delete_one({'_id': ObjectId(expense_id), 'user_id': current_user.id})
        if result.deleted_count > 0:
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
        expense = expenses_col.find_one({'_id': ObjectId(expense_id), 'user_id': current_user.id})
        if not expense:
            flash('❌ Expense not found!', 'danger')
            return redirect(url_for('view_expenses'))

        if request.method == 'POST':
            category = request.form.get('category')
            amount   = request.form.get('amount')
            note     = request.form.get('note', '').strip()
            date_str = request.form.get('date')

            if not category or not amount:
                flash('❌ Category and amount are required!', 'danger')
                return redirect(url_for('edit_expense', expense_id=expense_id))

            try:
                expense_date = datetime.strptime(date_str, '%Y-%m-%d') if date_str else expense['date']
            except ValueError:
                flash('❌ Invalid date format!', 'danger')
                return redirect(url_for('edit_expense', expense_id=expense_id))

            expenses_col.update_one(
                {'_id': ObjectId(expense_id), 'user_id': current_user.id},
                {'$set': {'category': category, 'amount': float(amount), 'note': note, 'date': expense_date}}
            )
            flash('✅ Expense updated successfully!', 'success')
            return redirect(url_for('view_expenses'))

        categories = get_user_categories()
        return render_template('edit_expense.html', expense=expense, categories=categories)

    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
        return redirect(url_for('view_expenses'))


@app.route('/clear')
@login_required
def clear_expenses():
    result = expenses_col.delete_many({'user_id': current_user.id})
    flash(f'🗑️ All {result.deleted_count} expenses deleted!', 'info')
    return redirect(url_for('view_expenses'))


@app.route('/categories', methods=['GET', 'POST'])
@login_required
def manage_categories():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            category_name = request.form.get('category_name')
            category_icon = request.form.get('category_icon')
            if category_name and category_icon:
                categories_col.insert_one({
                    'name': category_name, 'icon': category_icon, 'user_id': current_user.id
                })
                flash(f'✅ Category "{category_name}" added!', 'success')
            else:
                flash('❌ Provide both name and icon!', 'danger')

        elif action == 'delete':
            category_name = request.form.get('category_delete')
            result = categories_col.delete_one({'name': category_name, 'user_id': current_user.id})
            if result.deleted_count > 0:
                flash(f'🗑️ Category "{category_name}" deleted!', 'success')

        return redirect(url_for('manage_categories'))

    categories = get_user_categories()
    return render_template("categories.html", categories=categories)


@app.route('/budget', methods=['GET', 'POST'])
@login_required
def manage_budget():
    if request.method == 'POST':
        category      = request.form.get('category')
        budget_amount = request.form.get('budget_amount')

        if category and budget_amount:
            try:
                budget_amount = float(budget_amount)
                budgets_col.update_one(
                    {'user_id': current_user.id, 'category': category},
                    {'$set': {'amount': budget_amount}},
                    upsert=True
                )
                flash(f'✅ Budget of ₹{budget_amount} set for {category}!', 'success')
            except ValueError:
                flash('❌ Invalid budget amount!', 'danger')
        return redirect(url_for('manage_budget'))

    categories  = get_user_categories()
    budget_list = list(budgets_col.find({'user_id': current_user.id}))
    budget_dict = {b['category']: b['amount'] for b in budget_list}

    start_of_month = now_ist().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spending_agg = expenses_col.aggregate([
        {'$match': {'user_id': current_user.id, 'date': {'$gte': start_of_month}}},
        {'$group': {'_id': '$category', 'spent': {'$sum': '$amount'}}}
    ])
    spending_dict = {r['_id']: r['spent'] for r in spending_agg}

    budget_data = []
    for cat in categories:
        cat_name   = cat['name']
        budget     = budget_dict.get(cat_name, 0)
        spent      = spending_dict.get(cat_name, 0)
        if budget > 0:
            percentage = (spent / budget) * 100
            status     = 'danger' if percentage >= 100 else ('warning' if percentage >= 80 else 'success')
        else:
            percentage = 0
            status     = 'secondary'
        budget_data.append({
            'category': cat_name, 'icon': cat['icon'],
            'budget': budget, 'spent': spent,
            'remaining': max(0, budget - spent),
            'percentage': min(100, percentage), 'status': status
        })

    return render_template('budget.html', categories=categories, budget_data=budget_data)


@app.route('/budget/delete', methods=['POST'])
@login_required
def delete_budget():
    category = request.form.get('category')
    budgets_col.delete_one({'user_id': current_user.id, 'category': category})
    flash(f'🗑️ Budget for {category} deleted!', 'success')
    return redirect(url_for('manage_budget'))


@app.route('/insights')
@login_required
def generate_insights():
    expenses       = list(expenses_col.find({'user_id': current_user.id}))
    category_totals = defaultdict(int)
    monthly_totals  = defaultdict(int)
    total_expenses  = 0
    max_expense     = 0
    highest_category = "None"
    ai_warnings     = []

    thresholds = {
        "Food": 0.3, "Entertainment": 0.15,
        "Shopping": 0.2, "Bills": 0.25, "Other": 0.1
    }

    for expense in expenses:
        amount   = int(expense['amount'])
        category = expense['category']
        month    = expense['date'].strftime("%Y-%m")
        total_expenses      += amount
        category_totals[category] += amount
        monthly_totals[month]     += amount
        if amount > max_expense:
            max_expense      = amount
            highest_category = category

    if total_expenses > 0:
        start_of_month = now_ist().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        budget_list    = list(budgets_col.find({'user_id': current_user.id}))
        budget_dict    = {b['category']: b['amount'] for b in budget_list}

        spending_agg = expenses_col.aggregate([
            {'$match': {'user_id': current_user.id, 'date': {'$gte': start_of_month}}},
            {'$group': {'_id': '$category', 'spent': {'$sum': '$amount'}}}
        ])
        month_spending = {r['_id']: r['spent'] for r in spending_agg}

        for category, budget in budget_dict.items():
            spent = month_spending.get(category, 0)
            if spent > 0:
                pct = (spent / budget) * 100
                if pct >= 100:
                    ai_warnings.append({"type": "danger",
                        "message": f"🚨 BUDGET ALERT: You've exceeded your {category} budget by ₹{int(spent - budget)}!"})
                elif pct >= 80:
                    ai_warnings.append({"type": "warning",
                        "message": f"⚠️ Budget Warning: Only ₹{int(budget - spent)} left in {category} budget!"})

        for category, spent in category_totals.items():
            pct = spent / total_expenses
            if category in thresholds:
                if pct > thresholds[category]:
                    ai_warnings.append({"type": "warning",
                        "message": f"⚠️ You are overspending on {category} ({pct:.1%} of total). Consider reducing it!"})
                else:
                    ai_warnings.append({"type": "success",
                        "message": f"✅ Good job! Your {category} spending is within limits ({pct:.1%})."})

    savings_recommendation = total_expenses * 0.2
    if not category_totals:
        category_totals = {"No Data": 1}

    category_chart = generate_pie_chart(category_totals) if len(category_totals) > 1 else None
    trend_chart    = generate_line_chart(monthly_totals) if monthly_totals else None

    return render_template("insights.html",
                           total_expenses=total_expenses,
                           max_expense=max_expense,
                           highest_category=highest_category,
                           category_totals=category_totals,
                           category_chart=category_chart,
                           trend_chart=trend_chart,
                           ai_warnings=ai_warnings,
                           savings_recommendation=savings_recommendation)


@app.route('/download')
@login_required
def download_expenses():
    import tempfile
    expenses = list(expenses_col.find({'user_id': current_user.id}).sort('date', -1))

    if not expenses:
        flash('🚨 No expenses to download!', 'danger')
        return redirect(url_for('view_expenses'))

    csv_filename = f"expenses_{current_user.username}.csv"
    csv_path     = os.path.join(tempfile.gettempdir(), csv_filename)
    with open(csv_path, 'w') as f:
        f.write("Category,Amount,Date,Note\n")
        for exp in expenses:
            note = (exp.get('note', '') or '').replace(',', ';')
            f.write(f"{exp['category']},{exp['amount']},{exp['date'].strftime('%Y-%m-%d %H:%M:%S')},{note}\n")

    return send_file(csv_path, as_attachment=True, download_name=csv_filename, mimetype="text/csv")


@app.route('/download-pdf')
@login_required
def download_pdf():
    from pdf_generator import create_pdf_report
    expenses = list(expenses_col.find({'user_id': current_user.id}).sort('date', -1))

    if not expenses:
        flash('🚨 No expenses to generate report!', 'danger')
        return redirect(url_for('view_expenses'))

    category_totals = defaultdict(int)
    for expense in expenses:
        category_totals[expense['category']] += int(expense['amount'])

    category_chart = generate_pie_chart(category_totals) if len(category_totals) > 1 else None
    pdf_buffer     = create_pdf_report(expenses, current_user.username, category_chart)
    pdf_filename   = f"expense_report_{current_user.username}_{now_ist().strftime('%Y%m%d')}.pdf"

    return send_file(pdf_buffer, as_attachment=True,
                     download_name=pdf_filename, mimetype='application/pdf')


# ── CHART GENERATION ──────────────────────────────────────────────────────────
def generate_pie_chart(data):
    if not data:
        return None
    fig, ax = plt.subplots(figsize=(8, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    amounts  = [int(v) for v in data.values()]
    labels   = list(data.keys())
    colors   = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    explode  = [0.05] * len(labels)
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
    months  = list(data.keys())
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
    buffer  = BytesIO()
    fig.savefig(buffer, format="png", dpi=100, bbox_inches='tight')
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"


if __name__ == '__main__':
    app.run(debug=True)
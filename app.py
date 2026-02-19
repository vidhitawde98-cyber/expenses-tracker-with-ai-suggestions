import matplotlib
matplotlib.use("Agg")
from flask import Flask, render_template, request, send_file, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId
from collections import defaultdict
from datetime import datetime
import matplotlib.pyplot as plt
import os
import base64
from io import BytesIO

app = Flask(__name__, template_folder='templates')
app.secret_key = os.environ.get('SECRET_KEY', 'vidhi-expense-tracker-secret-2024')

# MongoDB Configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
client = MongoClient(MONGO_URI)
db = client['expense_tracker']

# Collections
users_collection = db['users']
expenses_collection = db['expenses']
categories_collection = db['categories']

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = '⚠️ Please log in to access this page.'
login_manager.login_message_category = 'warning'


# User Model
class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.email = user_data['email']
        self.created_at = user_data.get('created_at')
    
    @staticmethod
    def get_by_id(user_id):
        user_data = users_collection.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None
    
    @staticmethod
    def get_by_email(email):
        user_data = users_collection.find_one({'email': email})
        return User(user_data) if user_data else None
    
    @staticmethod
    def get_by_username(username):
        user_data = users_collection.find_one({'username': username})
        return User(user_data) if user_data else None


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


# Initialize default categories for new users
def initialize_user_categories(user_id):
    default_categories = [
        {"name": "Food", "icon": "🍔", "user_id": user_id},
        {"name": "Entertainment", "icon": "🎭", "user_id": user_id},
        {"name": "Shopping", "icon": "🛍️", "user_id": user_id},
        {"name": "Bills", "icon": "📑", "user_id": user_id},
        {"name": "Other", "icon": "💼", "user_id": user_id}
    ]
    categories_collection.insert_many(default_categories)
    print(f"✅ Initialized {len(default_categories)} categories for user {user_id}")


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
        
        # Validation
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
        
        # Check if user exists
        if users_collection.find_one({'email': email}):
            flash('❌ Email already registered! Please login.', 'danger')
            return render_template('register.html')
        
        if users_collection.find_one({'username': username}):
            flash('❌ Username already taken!', 'danger')
            return render_template('register.html')
        
        # Create user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        
        user_data = {
            'username': username,
            'email': email,
            'password': hashed_password,
            'created_at': datetime.now()
        }
        
        result = users_collection.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        # Initialize categories
        initialize_user_categories(user_id)
        
        flash(f'✅ Account created successfully! Welcome {username}!', 'success')
        
        # Auto-login
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
        
        user_data = users_collection.find_one({'email': email})
        
        if not user_data:
            flash('❌ Invalid email or password!', 'danger')
            return render_template('login.html')
        
        if not check_password_hash(user_data['password'], password):
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
    """User profile page"""
    # Get user stats
    total_expenses = expenses_collection.count_documents({'user_id': current_user.id})
    
    # Calculate total amount spent
    pipeline = [
        {'$match': {'user_id': current_user.id}},
        {'$group': {'_id': None, 'total': {'$sum': '$amount'}}}
    ]
    result = list(expenses_collection.aggregate(pipeline))
    total_amount = result[0]['total'] if result else 0
    
    # Get total categories
    total_categories = categories_collection.count_documents({'user_id': current_user.id})
    
    # Get user data
    user_data = users_collection.find_one({'_id': ObjectId(current_user.id)})
    
    return render_template('profile.html',
                         total_expenses=total_expenses,
                         total_amount=int(total_amount),
                         total_categories=total_categories,
                         user_data=user_data)

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
    note = request.form.get('note', '').strip()  # ← NEW: Get note
    
    expense_data = {
        'user_id': current_user.id,
        'category': category,
        'amount': float(amount),
        'note': note,  # ← NEW: Store note
        'date': datetime.now()
    }
    
    expenses_collection.insert_one(expense_data)
    
    flash(f"✅ Expense of ₹{amount} added to {category} successfully!", 'success')
    return redirect(url_for('home'))


@app.route('/view')
@login_required
def view_expenses():
    category_filter = request.args.get('category', '').lower()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = {'user_id': current_user.id}
    
    if category_filter:
        query['category'] = {'$regex': category_filter, '$options': 'i'}
    
    if start_date:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
        query['date'] = {'$gte': start_date_obj}
    
    if end_date:
        end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
        if 'date' in query:
            query['date']['$lte'] = end_date_obj
        else:
            query['date'] = {'$lte': end_date_obj}
    
    expenses = list(expenses_collection.find(query).sort('date', -1))
    
    expenses_list = [
    (exp['_id'], exp['category'], exp['amount'], exp['date'].strftime('%Y-%m-%d %H:%M:%S'), exp.get('note', ''))
    for exp in expenses
    ]
    
    return render_template("view_expenses.html", expenses=expenses_list)


@app.route('/delete/<expense_id>')
@login_required
def delete_expense(expense_id):
    try:
        result = expenses_collection.delete_one({
            '_id': ObjectId(expense_id),
            'user_id': current_user.id
        })
        
        if result.deleted_count > 0:
            flash('🗑️ Expense deleted successfully!', 'success')
        else:
            flash('❌ Expense not found!', 'danger')
    
    except Exception as e:
        flash(f'❌ Error: {str(e)}', 'danger')
    
    return redirect(url_for('view_expenses'))


@app.route('/clear')
@login_required
def clear_expenses():
    result = expenses_collection.delete_many({'user_id': current_user.id})
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
                categories_collection.insert_one({
                    'name': category_name,
                    'icon': category_icon,
                    'user_id': current_user.id
                })
                flash(f'✅ Category "{category_name}" added!', 'success')
            else:
                flash('❌ Provide both name and icon!', 'danger')
        
        elif action == 'delete':
            category_name = request.form.get('category_delete')
            
            result = categories_collection.delete_one({
                'name': category_name,
                'user_id': current_user.id
            })
            
            if result.deleted_count > 0:
                flash(f'🗑️ Category "{category_name}" deleted!', 'success')
        
        return redirect(url_for('manage_categories'))
    
    categories = get_user_categories()
    return render_template("categories.html", categories=categories)


def get_user_categories():
    categories = list(categories_collection.find({'user_id': current_user.id}))
    return [{'name': cat['name'], 'icon': cat['icon']} for cat in categories]


@app.route('/insights')
@login_required
def generate_insights():
    expenses = list(expenses_collection.find({'user_id': current_user.id}))
    
    category_totals = defaultdict(int)
    monthly_totals = defaultdict(int)
    total_expenses = 0
    max_expense = 0
    highest_category = "None"
    ai_warnings = []
    
    thresholds = {
        "Food": 0.3,
        "Entertainment": 0.15,
        "Shopping": 0.2,
        "Bills": 0.25,
        "Other": 0.1
    }
    
    for expense in expenses:
        amount = int(expense['amount'])
        category = expense['category']
        date_obj = expense['date']
        month = date_obj.strftime("%Y-%m")
        
        total_expenses += amount
        category_totals[category] += amount
        monthly_totals[month] += amount
        
        if amount > max_expense:
            max_expense = amount
            highest_category = category
    
    if total_expenses > 0:
        for category, spent in category_totals.items():
            percentage = spent / total_expenses
            
            if category in thresholds:
                if percentage > thresholds[category]:
                    ai_warnings.append({
                        "type": "warning",
                        "message": f"⚠️ You are overspending on {category} ({percentage:.1%} of total). Consider reducing it!"
                    })
                else:
                    ai_warnings.append({
                        "type": "success",
                        "message": f"✅ Good job! Your {category} spending is within limits ({percentage:.1%})."
                    })
    
    savings_recommendation = total_expenses * 0.2
    
    if not category_totals:
        category_totals = {"No Data": 1}
    
    category_chart = generate_pie_chart(category_totals) if len(category_totals) > 1 else None
    trend_chart = generate_line_chart(monthly_totals) if monthly_totals else None
    
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
    expenses = list(expenses_collection.find({'user_id': current_user.id}).sort('date', -1))
    
    if not expenses:
        flash('🚨 No expenses to download!', 'danger')
        return redirect(url_for('view_expenses'))
    
    csv_filename = f"expenses_{current_user.username}.csv"
    csv_path = f"/tmp/{csv_filename}"
    
    with open(csv_path, 'w') as f:
        f.write("Category,Amount,Date\n")
        for exp in expenses:
            f.write(f"{exp['category']},{exp['amount']},{exp['date'].strftime('%Y-%m-%d %H:%M:%S')}\n")
    
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
    
    for i, (month, amount) in enumerate(zip(months, amounts)):
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


if __name__ == '__main__':
    app.run(debug=True)
import matplotlib
matplotlib.use("Agg")  # ✅ REQUIRED for Render / servers
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from collections import defaultdict
from datetime import datetime  
import matplotlib.pyplot as plt
import os
import base64
from io import BytesIO

app = Flask(__name__, template_folder='templates')  # ✅ Define Flask only ONCE
app.secret_key = 'vidhi'  # ✅ Required for flash messages

EXPENSE_FILE = "expenses.txt"

# ✅ Ensure the file exists to avoid errors
if not os.path.exists(EXPENSE_FILE):
    with open(EXPENSE_FILE, "w") as f:
        f.write("Category,Amount,Date\n")  # Create file with header

# ✅ ADD THIS: Ensure categories file exists at startup
CATEGORIES_FILE = "categories.txt"
if not os.path.exists(CATEGORIES_FILE):
    default_categories = [
        "Food,🍔",
        "Entertainment,🎭",
        "Shopping,🛍️",
        "Bills,📑",
        "Other,💼"
    ]
    with open(CATEGORIES_FILE, "w", encoding='utf-8') as f:
        f.write("\n".join(default_categories))


@app.route('/')
def home():
    categories = get_categories()  # ✅ Get categories
    return render_template("add_expense.html", categories=categories)  # ✅ Pass to template

@app.route('/favicon.ico')
def favicon():
    return "", 204  # Returns an empty response with status 204 (No Content)

@app.route('/add', methods=['POST'])
def add_expense():
    category = request.form['category']
    amount = request.form['amount']
    entry = f"{category},{amount},{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"

    with open(EXPENSE_FILE, "a") as f:
        f.write(entry)

    print("DEBUG: Added Expense:", entry)

    # ✅ Redirect to the home page with a success message instead of plain HTML
    flash("✅ Expense Added Successfully!")
    return redirect(url_for('home'))  # ← THIS WAS MISSING!


@app.route('/view')
def view_expenses():
    expenses = []
    category_filter = request.args.get('category', '').lower()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    try:
        with open(EXPENSE_FILE, "r") as f:
            for line in f:
                data = line.strip().split(",")
                if len(data) != 3 or 'date' in data[2].lower():
                 continue  # Skip malformed lines or headers

                category, amount, date_str = data

                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        continue  # Skip  if invalid date format


                if category_filter and category_filter not in category.lower():
                    continue  

                if start_date:
                    start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                    if date_obj < start_date_obj:
                        continue  

                if end_date:
                    end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                    if date_obj > end_date_obj:
                        continue  

                expenses.append((category, amount, date_str))

    except FileNotFoundError:
        expenses = []

    return render_template("view_expenses.html", expenses=expenses)

# ✅ Route to delete a specific expense
@app.route('/delete/<int:index>')
def delete_expense(index):
    try:
        with open(EXPENSE_FILE, "r") as f:
            lines = f.readlines()
        
        # Keep header and remove the specific expense
        if index > 0 and index < len(lines):
            deleted_line = lines.pop(index)
            
            with open(EXPENSE_FILE, "w") as f:
                f.writelines(lines)
            
            flash(f'🗑️ Expense deleted successfully!', 'success')
        else:
            flash('❌ Invalid expense index!', 'danger')
            
    except FileNotFoundError:
        flash('🚨 No expenses found!', 'danger')
    
    return redirect(url_for('view_expenses'))

# ✅ Route to manage custom categories
@app.route('/categories', methods=['GET', 'POST'])
def manage_categories():
    # ✅ Use the global CATEGORIES_FILE constant instead of redefining
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add':
            category_name = request.form.get('category_name')
            category_icon = request.form.get('category_icon')
            
            if category_name and category_icon:
                with open(CATEGORIES_FILE, "a", encoding='utf-8') as f:
                    f.write(f"\n{category_name},{category_icon}")
                flash(f'✅ Category "{category_name}" added successfully!', 'success')
            else:
                flash('❌ Please provide both name and icon!', 'danger')
        
        elif action == 'delete':
            category_to_delete = request.form.get('category_delete')
            
            with open(CATEGORIES_FILE, "r", encoding='utf-8') as f:
                lines = f.readlines()
            
            with open(CATEGORIES_FILE, "w", encoding='utf-8') as f:
                for line in lines:
                    if not line.startswith(category_to_delete + ","):
                        f.write(line)
            
            flash(f'🗑️ Category "{category_to_delete}" deleted!', 'success')
        
        return redirect(url_for('manage_categories'))
    
    # Read categories
    categories = get_categories()
    return render_template("categories.html", categories=categories)

# ✅ Helper function to get categories
def get_categories():
    categories = []
    
    try:
        with open(CATEGORIES_FILE, "r", encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split(",")
                    if len(parts) == 2:
                        categories.append({"name": parts[0], "icon": parts[1]})
    except FileNotFoundError:
        # Default categories if file doesn't exist
        categories = [
            {"name": "Food", "icon": "🍔"},
            {"name": "Entertainment", "icon": "🎭"},
            {"name": "Shopping", "icon": "🛍️"},
            {"name": "Bills", "icon": "📑"},
            {"name": "Other", "icon": "💼"}
        ]
    
    return categories



@app.route('/insights')
def generate_insights():
    category_totals = defaultdict(int)
    monthly_totals=defaultdict(int)
    total_expenses = 0
    max_expense = 0
    highest_category = "None"
    ai_warnings = [] # ✅ NEW: Store AI warnings

    # Define spending thresholds
    thresholds = {
        "Food": 0.3,
        "Entertainment": 0.15,
        "Shopping": 0.2,
        "Bills": 0.25,
        "Other": 0.1
    }

    try:
        with open(EXPENSE_FILE, "r") as f:
            lines = f.readlines()
            
            if lines and "Date" in lines[0]:  
                lines = lines[1:]  

            for line in lines:
                data = line.strip().split(",")

                if len(data) < 3:
                    continue  
                
                category, amount, date_str = data  
                try:
                    amount = int(amount)
                except ValueError:
                    continue  
                
                try:
                     date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        continue
                
                month = date_obj.strftime("%Y-%m")

                total_expenses += amount
                category_totals[category] += amount
                monthly_totals[month] += amount  

                if amount > max_expense:
                    max_expense = amount
                    highest_category = category

    except FileNotFoundError:
        pass

    # ✅ AI-BASED INSIGHTS
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
    
    # Calculate savings recommendation
    savings_recommendation = total_expenses * 0.2  # 20% of expenses
    
    # ✅ Ensure max_expense and highest_category have default values
    if not category_totals:
         category_totals = {"No Data": 1}
    
    # ✅ Generate Chart Images
    category_chart = generate_pie_chart(category_totals) if len(category_totals) > 1 else None
    trend_chart = generate_line_chart(monthly_totals) if monthly_totals else None
    
    #print("Category Chart:", category_chart)
    #print("Trend Chart:", trend_chart)
    
    return render_template("insights.html", 
                           total_expenses=total_expenses, 
                           max_expense=max_expense, 
                           highest_category=highest_category,
                           category_totals=category_totals, 
                           category_chart=category_chart, 
                           trend_chart=trend_chart,
                           ai_warnings=ai_warnings,  # ✅ Pass AI insights
                           savings_recommendation=savings_recommendation)

# 🔥 Function to Generate Pie Chart (Category-wise Spending)
# 🔥 Function to Generate Pie Chart (Category-wise Spending)
def generate_pie_chart(data):
    if not data:
        return None
    
    # ✅ Increase figure size and add padding
    fig, ax = plt.subplots(figsize=(8, 8))
    
    # ✅ Set white background
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    amounts = [int(v) for v in data.values()]
    labels = list(data.keys())
    
    # ✅ Improve chart appearance with better colors
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F']
    explode = [0.05] * len(labels)  # Slightly separate slices
    
    ax.pie(amounts, labels=labels, autopct='%1.1f%%', startangle=140, 
           colors=colors, explode=explode, shadow=True,
           textprops={'fontsize': 11, 'weight': 'bold', 'color': 'black'})
    
    ax.axis('equal')
    
    # ✅ Add title with black color
    plt.title('Category-wise Spending Distribution', fontsize=14, weight='bold', pad=20, color='black')
    
    # ✅ Tight layout to prevent cut-off
    plt.tight_layout()
    
    return save_chart(fig)


# 🔥 Function to Generate Line Chart (Monthly Spending Trends)
def generate_line_chart(data):
    if not data:
        return None
    
    # ✅ Increase figure size
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # ✅ Set white background for the figure
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    months = list(data.keys())
    amounts = list(data.values())
    
    # ✅ Improve line chart appearance
    ax.plot(months, amounts, marker='o', linestyle='-', color='#4ECDC4', 
            linewidth=2.5, markersize=8, markerfacecolor='#FF6B6B', 
            markeredgecolor='#fff', markeredgewidth=2)
    
    ax.set_title("Monthly Spending Trends", fontsize=14, weight='bold', pad=15, color='black')
    ax.set_xlabel("Month", fontsize=12, weight='bold', color='black')
    ax.set_ylabel("Total Spent (₹)", fontsize=12, weight='bold', color='black')
    
    # ✅ Set tick colors to black so they're visible
    ax.tick_params(axis='x', colors='black', labelsize=10)
    ax.tick_params(axis='y', colors='black', labelsize=10)
    
    # ✅ Rotate x-axis labels for better readability
    plt.xticks(rotation=45, ha='right')
    
    # ✅ Add grid with better visibility
    ax.grid(True, alpha=0.3, linestyle='--', color='gray')
    
    # ✅ Add value labels on points
    for i, (month, amount) in enumerate(zip(months, amounts)):
        ax.annotate(f'₹{amount}', (month, amount), 
                   textcoords="offset points", xytext=(0,10), 
                   ha='center', fontsize=9, weight='bold', color='black')
    
    # ✅ Set spine colors
    for spine in ax.spines.values():
        spine.set_edgecolor('black')
    
    # ✅ Tight layout to prevent cut-off
    plt.tight_layout()
    
    return save_chart(fig)

# ✅ Save Chart as Base64 Image (to Embed in HTML)
def save_chart(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png")
    buffer.seek(0)
    encoded = base64.b64encode(buffer.read()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{encoded}"

    

@app.route('/debug')
def debug_file():
    try:
        with open(EXPENSE_FILE, "r") as f:
            content = f.readlines()
        return "<br>".join(content)
    except FileNotFoundError:
        return "🚨 No expenses recorded yet!"

@app.route('/clear')
def clear_expenses():
    with open(EXPENSE_FILE, "w") as f:
        f.write("Category,Amount,Date\n")  
    
    flash('🗑️ All expenses have been deleted!', 'info')
    return redirect(url_for('view_expenses'))

@app.route('/download')
def download_expenses():
    try:
        return send_file(EXPENSE_FILE, as_attachment=True, download_name="expenses.csv", mimetype="text/csv")
    except FileNotFoundError:
        return "🚨 No expenses recorded yet!"

if __name__ == '__main__':
    app.run()

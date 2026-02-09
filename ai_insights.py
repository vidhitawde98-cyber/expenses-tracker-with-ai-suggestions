import os
from collections import defaultdict

EXPENSE_FILE = "expenses.txt"

# Function to analyze and provide AI-based insights
def generate_insights():
    if not os.path.exists(EXPENSE_FILE) or os.stat(EXPENSE_FILE).st_size == 0:
        print("❌ No expenses found!")
        return
    
    expense_data = defaultdict(float)

    # Read expenses from file
    with open(EXPENSE_FILE, "r") as f:
        for line in f:
            category, amount, _ = line.strip().split(",")
            expense_data[category] += float(amount)

    total_spent = sum(expense_data.values())

    # Define spending limits (example)
    thresholds = {
        "Food": 0.3,   # 30% of total budget
        "Entertainment": 0.15,  # 15%
        "Shopping": 0.2,  # 20%
        "Bills": 0.25,  # 25%
        "Other": 0.1   # 10%
    }

    # Analyze spending
    print("\n📊 **AI-Based Expense Insights** 📊\n")
    for category, spent in expense_data.items():
        percentage = spent / total_spent

        if category in thresholds:
            if percentage > thresholds[category]:
                print(f"⚠️ **Warning:** You are overspending on {category} ({percentage:.1%} of total budget). Consider reducing it!")
            else:
                print(f"✅ Good job! Your {category} spending is within limits.")
        else:
            print(f"ℹ️ Note: Your spending on {category} is {percentage:.1%} of total expenses.")

    print("\n💡 **Tip:** Try to save at least 20% of your total income every month! 💰")

# Main function to test
if __name__ == "__main__":
    generate_insights()

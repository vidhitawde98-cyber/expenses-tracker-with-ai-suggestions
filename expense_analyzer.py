import os
import matplotlib.pyplot as plt
from collections import defaultdict

EXPENSE_FILE = "expenses.txt"

# Function to analyze and visualize expenses
def analyze_expenses():
    if not os.path.exists(EXPENSE_FILE) or os.stat(EXPENSE_FILE).st_size == 0:
        print("❌ No expenses found!")
        return
    
    expense_data = defaultdict(float)

    # Read expenses from file
    with open(EXPENSE_FILE, "r") as f:
        for line in f:
            category, amount, _ = line.strip().split(",")
            expense_data[category] += float(amount)
    
    # Pie chart visualization
    categories = list(expense_data.keys())
    amounts = list(expense_data.values())

    plt.figure(figsize=(6, 6))
    plt.pie(amounts, labels=categories, autopct="%1.1f%%", startangle=140, colors=['#ff9999','#66b3ff','#99ff99','#ffcc99'])
    plt.title("💰 Expense Distribution")
    plt.show()

# Main function to test
if __name__ == "__main__":
    analyze_expenses()

import os
from datetime import datetime
from ai_insights import generate_insights

EXPENSE_FILE = "expenses.txt"

# Function to add an expense
def add_expense():
    category = input("Enter expense category (Food, Entertainment, Shopping, Bills, Other): ")
    amount = input("Enter amount spent: ₹")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(EXPENSE_FILE, "a") as f:
        f.write(f"{category},{amount},{date}\n")
    
    print("✅ Expense added successfully!\n")

# Function to view all expenses
def view_expenses():
    if not os.path.exists(EXPENSE_FILE) or os.stat(EXPENSE_FILE).st_size == 0:
        print("❌ No expenses recorded yet!\n")
        return

    print("\n📄 **Your Expenses:**")
    with open(EXPENSE_FILE, "r") as f:
        for line in f:
            category, amount, date = line.strip().split(",")
            print(f"📌 {category} | ₹{amount} | {date}")
    print("\n")

# Function to delete an expense
def delete_expense():
    confirm = input("⚠️ Are you sure you want to delete all expenses? (yes/no): ").lower()
    if confirm == "yes":
        open(EXPENSE_FILE, "w").close()
        print("✅ All expenses deleted successfully!\n")
    else:
        print("❌ Action canceled!\n")

# Main function to test
def main():
    while True:
        print("\n💰 **Personal Expense Tracker** 💰")
        print("1️⃣ Add Expense")
        print("2️⃣ View Expenses")
        print("3️⃣ Generate AI Insights")
        print("4️⃣ Delete All Expenses")
        print("5️⃣ Exit")
        
        choice = input("Enter your choice: ")

        if choice == "1":
            add_expense()
        elif choice == "2":
            view_expenses()
        elif choice == "3":
            generate_insights()  # Call AI insights function
        elif choice == "4":
            delete_expense()
        elif choice == "5":
            print("👋 Goodbye! Stay financially smart. 💡")
            break
        else:
            print("❌ Invalid choice! Please enter a number from 1 to 5.\n")

# Run the program
if __name__ == "__main__":
    main()
users = {}
expenses = []
goals = {}

def create_user():
    username = input("Enter username: ")
    if username in users:
        print("User already exists!")
    else:
        email = input("Enter email: ")
        users[username] = {"email": email}
        print("User created successfully!")

def add_expense():
    username = input("Enter username: ")
    if username not in users:
        print("User not found!")
        return

    amount = float(input("Enter amount: "))
    category = input("Enter category: ")
    expenses.append({
        "user": username,
        "amount": amount,
        "category": category
    })
    print("Expense added!")

def set_goal():
    username = input("Enter username: ")
    if username not in users:
        print("User not found!")
        return

    budget = float(input("Enter monthly budget: "))
    savings = float(input("Enter savings goal: "))
    goals[username] = {"budget": budget, "savings": savings}
    print("Goals set!")
def view_expenses():
    username = input("Enter username: ")
    user_expenses = [e for e in expenses if e["user"] == username]

    if not user_expenses:
        print("No expenses found.")
        return

    for i, e in enumerate(user_expenses, 1):
        print(f"{i}. {e['category']} - RM{e['amount']}")

def view_dashboard():
    username = input("Enter username: ")
    total = sum(e["amount"] for e in expenses if e["user"] == username)
    print(f"Total Expenses: RM{total}")

    if username in goals:
        print(f"Budget: RM{goals[username]['budget']}")

def view_savings_progress():
    username = input("Enter username: ")
    total = sum(e["amount"] for e in expenses if e["user"] == username)

    if username in goals:
        savings_goal = goals[username]["savings"]
        progress = max(0, savings_goal - total)
        print(f"Remaining to save: RM{progress}")
    else:
        print("No goals set.")

def edit_user():
    username = input("Enter username: ")
    if username in users:
        new_email = input("Enter new email: ")
        users[username]["email"] = new_email
        print("Profile updated!")
    else:
        print("User not found!")

def update_expense():
    username = input("Enter username: ")
    user_expenses = [e for e in expenses if e["user"] == username]

    if not user_expenses:
        print("No expenses found.")
        return

    view_expenses()
    idx = int(input("Select expense number to update: ")) - 1

    if 0 <= idx < len(user_expenses):
        user_expenses[idx]["amount"] = float(input("New amount: "))
        user_expenses[idx]["category"] = input("New category: ")
        print("Expense updated!")
    else:
        print("Invalid selection.")

def modify_goal():
    username = input("Enter username: ")
    if username in goals:
        goals[username]["budget"] = float(input("New budget: "))
        goals[username]["savings"] = float(input("New savings goal: "))
        print("Goals updated!")
    else:
        print("No goals found.")

def delete_expense():
    username = input("Enter username: ")
    user_expenses = [e for e in expenses if e["user"] == username]

    if not user_expenses:
        print("No expenses to delete.")
        return

    view_expenses()
    idx = int(input("Select expense number to delete: ")) - 1

    if 0 <= idx < len(user_expenses):
        expenses.remove(user_expenses[idx])
        print("Expense deleted!")
    else:
        print("Invalid selection.")

def delete_account():
    username = input("Enter username: ")
    if username in users:
        del users[username]
        print("Account deleted!")
    else:
        print("User not found!")

def menu():
    while True:
        print("\n=== Personal Finance System ===")
        print("1. Create User")
        print("2. Add Expense")
        print("3. Set Goals")
        print("4. View Expenses")
        print("5. View Dashboard")
        print("6. View Savings Progress")
        print("7. Edit User")
        print("8. Update Expense")
        print("9. Modify Goals")
        print("10. Delete Expense")
        print("11. Delete Account")
        print("0. Exit")

        choice = input("Enter choice: ")

        if choice == "1": create_user()
        elif choice == "2": add_expense()
        elif choice == "3": set_goal()
        elif choice == "4": view_expenses()
        elif choice == "5": view_dashboard()
        elif choice == "6": view_savings_progress()
        elif choice == "7": edit_user()
        elif choice == "8": update_expense()
        elif choice == "9": modify_goal()
        elif choice == "10": delete_expense()
        elif choice == "11": delete_account()
        elif choice == "0":
            print("Goodbye!")
            break
        else:
            print("Invalid choice!")
menu()
# Budget Tracker
user_name = input("How can we call you?")
transaction = []

while True:
    try:
        balance = float(input("Please enter your starting balance:"))
        if balance <= 0:
                print ("Please enter a number more than 0")
        else: 
                break
    except ValueError:
        print("Invalid Value. Please enter a number")

print("Welcome to BudgetBee", user_name)
print("Your starting balance is $", balance)

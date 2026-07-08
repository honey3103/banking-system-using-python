import sys
from database import init_db
from utils import clear_screen, get_valid_pin
import auth
import customer
import admin

def print_header(title):
    clear_screen()
    print("=" * 50)
    print(f"{title:^50}")
    print("=" * 50)

def customer_menu(account_info):
    while True:
        print_header(f"Welcome, {account_info['name']}")
        print("1. Check Balance")
        print("2. Deposit Money")
        print("3. Withdraw Money")
        print("4. Transfer Money")
        print("5. Transaction History")
        print("6. Change PIN")
        print("7. Logout")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            customer.check_balance(account_info['account_no'])
        elif choice == '2':
            customer.deposit(account_info['account_no'])
        elif choice == '3':
            customer.withdraw(account_info['account_no'])
        elif choice == '4':
            customer.transfer(account_info['account_no'])
        elif choice == '5':
            customer.view_history(account_info['account_no'])
        elif choice == '6':
            customer.change_pin(account_info['account_no'])
        elif choice == '7':
            print("Logging out...")
            break
        else:
            print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")

def admin_menu():
    while True:
        print_header("Admin Dashboard")
        print("1. View All Customers")
        print("2. Search Customer")
        print("3. Freeze/Unfreeze Account")
        print("4. Delete Account")
        print("5. View Total Bank Balance")
        print("6. View All Bank Transactions")
        print("7. Logout")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            admin.view_all_customers()
        elif choice == '2':
            admin.search_customer()
        elif choice == '3':
            admin.toggle_account_status()
        elif choice == '4':
            admin.delete_account()
        elif choice == '5':
            admin.view_total_bank_balance()
        elif choice == '6':
            admin.view_all_bank_transactions()
        elif choice == '7':
            print("Logging out...")
            break
        else:
            print("Invalid choice. Please try again.")
        input("\nPress Enter to continue...")

def main():
    init_db()
    
    while True:
        print_header("Bank Management System")
        print("1. Customer Login")
        print("2. Customer Registration")
        print("3. Admin Login")
        print("4. Exit")
        
        choice = input("\nEnter your choice: ")
        
        if choice == '1':
            account_no = input("Enter Account Number: ")
            pin = get_valid_pin()
            account_info, msg = auth.login_customer(account_no, pin)
            print(f"\n{msg}")
            if account_info:
                input("Press Enter to continue...")
                customer_menu(account_info)
            else:
                input("Press Enter to try again...")
                
        elif choice == '2':
            print_header("Customer Registration")
            name = input("Enter Name: ")
            mobile = input("Enter Mobile Number: ")
            email = input("Enter Email (optional): ")
            address = input("Enter Address: ")
            print("Set your PIN:")
            pin = get_valid_pin()
            
            account_no, msg = auth.register_customer(name, mobile, email, address, pin)
            print(f"\n{msg}")
            if account_no:
                print(f"Your generated Account Number is: {account_no}")
            input("\nPress Enter to continue...")
            
        elif choice == '3':
            username = input("Enter Admin Username: ")
            pin = input("Enter Admin PIN: ")
            success, msg = auth.login_admin(username, pin)
            print(f"\n{msg}")
            if success:
                input("Press Enter to continue...")
                admin_menu()
            else:
                input("Press Enter to try again...")
                
        elif choice == '4':
            print("\nThank you for using Bank Management System. Goodbye!")
            sys.exit(0)
            
        else:
            print("\nInvalid choice. Please try again.")
            input("Press Enter to continue...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nExiting application...")
        sys.exit(0)

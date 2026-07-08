from database import get_connection
from transaction import log_transaction, get_transactions
from utils import get_valid_amount, get_valid_pin, clear_screen, hash_pin

def deposit(account_no):
    amount = get_valid_amount("Enter amount to deposit: ₹")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE customers SET balance = balance + ? WHERE account_no = ?", (amount, account_no))
    cursor.execute("SELECT balance FROM customers WHERE account_no = ?", (account_no,))
    new_balance = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    log_transaction(account_no, "DEPOSIT", amount, new_balance)
    print(f"\nSuccessfully deposited ₹{amount:.2f}. New Balance: ₹{new_balance:.2f}")

def withdraw(account_no):
    amount = get_valid_amount("Enter amount to withdraw: ₹")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT balance FROM customers WHERE account_no = ?", (account_no,))
    current_balance = cursor.fetchone()[0]
    
    if current_balance < amount:
        print("\nInsufficient balance!")
        conn.close()
        return
        
    new_balance = current_balance - amount
    cursor.execute("UPDATE customers SET balance = ? WHERE account_no = ?", (new_balance, account_no))
    conn.commit()
    conn.close()
    
    log_transaction(account_no, "WITHDRAW", amount, new_balance)
    print(f"\nSuccessfully withdrew ₹{amount:.2f}. New Balance: ₹{new_balance:.2f}")

def transfer(account_no):
    target_account = input("Enter recipient account number: ")
    if target_account == account_no:
        print("\nCannot transfer to your own account.")
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT status FROM customers WHERE account_no = ?", (target_account,))
    target = cursor.fetchone()
    
    if not target:
        print("\nRecipient account not found.")
        conn.close()
        return
    if target[0] != 'ACTIVE':
        print("\nRecipient account is frozen.")
        conn.close()
        return
        
    amount = get_valid_amount("Enter amount to transfer: ₹")
    
    cursor.execute("SELECT balance FROM customers WHERE account_no = ?", (account_no,))
    current_balance = cursor.fetchone()[0]
    
    if current_balance < amount:
        print("\nInsufficient balance!")
        conn.close()
        return
        
    sender_new_balance = current_balance - amount
    cursor.execute("UPDATE customers SET balance = ? WHERE account_no = ?", (sender_new_balance, account_no))
    cursor.execute("UPDATE customers SET balance = balance + ? WHERE account_no = ?", (amount, target_account))
    
    cursor.execute("SELECT balance FROM customers WHERE account_no = ?", (target_account,))
    receiver_new_balance = cursor.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    log_transaction(account_no, f"TRANSFER TO {target_account}", amount, sender_new_balance)
    log_transaction(target_account, f"TRANSFER FROM {account_no}", amount, receiver_new_balance)
    
    print(f"\nSuccessfully transferred ₹{amount:.2f} to {target_account}. New Balance: ₹{sender_new_balance:.2f}")

def check_balance(account_no):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM customers WHERE account_no = ?", (account_no,))
    balance = cursor.fetchone()[0]
    conn.close()
    print(f"\nYour current balance is: ₹{balance:.2f}")

def view_history(account_no):
    records = get_transactions(account_no)
    if not records:
        print("\nNo transactions found.")
        return
        
    print("\n--- Transaction History ---")
    print(f"{'ID':<5} | {'Type':<25} | {'Amount':<10} | {'Balance':<10} | {'Date & Time'}")
    print("-" * 75)
    for r in records:
        print(f"{r[0]:<5} | {r[1]:<25} | ₹{r[2]:<9.2f} | ₹{r[3]:<9.2f} | {r[4]}")

def change_pin(account_no):
    conn = get_connection()
    cursor = conn.cursor()
    
    print("For verification:")
    old_pin = get_valid_pin()
    cursor.execute("SELECT pin_hash FROM customers WHERE account_no = ?", (account_no,))
    current_hash = cursor.fetchone()[0]
    
    from utils import verify_pin
    if not verify_pin(old_pin, current_hash):
        print("\nIncorrect old PIN.")
        conn.close()
        return
        
    print("Enter new PIN:")
    new_pin = get_valid_pin()
    print("Confirm new PIN:")
    confirm_pin = get_valid_pin()
    
    if new_pin != confirm_pin:
        print("\nPINs do not match!")
        conn.close()
        return
        
    cursor.execute("UPDATE customers SET pin_hash = ? WHERE account_no = ?", (hash_pin(new_pin), account_no))
    conn.commit()
    conn.close()
    print("\nPIN changed successfully.")

def request_loan(account_no):
    amount = get_valid_amount("Enter amount for loan request: ₹")
    
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO loans (account_no, amount, status) 
        VALUES (?, ?, 'PENDING')
    ''', (account_no, amount))
    
    conn.commit()
    conn.close()
    
    print(f"\nLoan request for ₹{amount:.2f} submitted successfully. Awaiting admin approval.")

def download_statement(account_no):
    from utils import generate_pdf_statement
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM customers WHERE account_no = ?", (account_no,))
    name = cursor.fetchone()[0]
    conn.close()
    
    transactions = get_transactions(account_no)
    filename = f"statement_{account_no}.pdf"
    
    if generate_pdf_statement(account_no, name, transactions, filename):
        print(f"\nStatement downloaded successfully as {filename}")
    else:
        print("\nFailed to generate statement. Ensure fpdf is installed.")

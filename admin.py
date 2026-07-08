from database import get_connection
from transaction import get_all_transactions

def view_all_customers():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT account_no, name, mobile, balance, status FROM customers")
    records = cursor.fetchall()
    conn.close()
    
    if not records:
        print("\nNo customers found.")
        return
        
    print("\n--- All Customers ---")
    print(f"{'Account No':<12} | {'Name':<20} | {'Mobile':<15} | {'Balance':<10} | {'Status'}")
    print("-" * 75)
    for r in records:
        print(f"{r[0]:<12} | {r[1]:<20} | {r[2]:<15} | ₹{r[3]:<9.2f} | {r[4]}")

def search_customer():
    search_term = input("Enter Account Number or Mobile: ")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT account_no, name, mobile, email, address, balance, status 
        FROM customers 
        WHERE account_no = ? OR mobile = ?
    ''', (search_term, search_term))
    record = cursor.fetchone()
    conn.close()
    
    if not record:
        print("\nCustomer not found.")
        return
        
    print("\n--- Customer Details ---")
    print(f"Account No : {record[0]}")
    print(f"Name       : {record[1]}")
    print(f"Mobile     : {record[2]}")
    print(f"Email      : {record[3]}")
    print(f"Address    : {record[4]}")
    print(f"Balance    : ₹{record[5]:.2f}")
    print(f"Status     : {record[6]}")

def toggle_account_status():
    account_no = input("Enter Account Number to Freeze/Unfreeze: ")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM customers WHERE account_no = ?", (account_no,))
    record = cursor.fetchone()
    
    if not record:
        print("\nCustomer not found.")
        conn.close()
        return
        
    new_status = 'FROZEN' if record[0] == 'ACTIVE' else 'ACTIVE'
    cursor.execute("UPDATE customers SET status = ? WHERE account_no = ?", (new_status, account_no))
    conn.commit()
    conn.close()
    
    print(f"\nAccount {account_no} is now {new_status}.")

def delete_account():
    account_no = input("Enter Account Number to delete: ")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM customers WHERE account_no = ?", (account_no,))
    if not cursor.fetchone():
        print("\nCustomer not found.")
        conn.close()
        return
        
    confirm = input(f"Are you sure you want to delete account {account_no}? (y/n): ")
    if confirm.lower() == 'y':
        cursor.execute("DELETE FROM transactions WHERE account_no = ?", (account_no,))
        cursor.execute("DELETE FROM customers WHERE account_no = ?", (account_no,))
        conn.commit()
        print("\nAccount deleted successfully.")
    else:
        print("\nDeletion cancelled.")
    conn.close()

def view_total_bank_balance():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(balance) FROM customers")
    total = cursor.fetchone()[0]
    conn.close()
    
    total = total if total else 0.0
    print(f"\nTotal Bank Balance (Customer Deposits): ₹{total:.2f}")
    
def view_all_bank_transactions():
    records = get_all_transactions()
    if not records:
        print("\nNo transactions found.")
        return
        
    print("\n--- All Bank Transactions ---")
    print(f"{'ID':<5} | {'Account No':<12} | {'Type':<20} | {'Amount':<10} | {'Date & Time'}")
    print("-" * 75)
    for r in records:
        print(f"{r[0]:<5} | {r[1]:<12} | {r[2]:<20} | ₹{r[3]:<9.2f} | {r[5]}")

def review_loan_requests():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, account_no, amount, status, date_time FROM loans WHERE status = 'PENDING'")
    records = cursor.fetchall()
    
    if not records:
        print("\nNo pending loan requests.")
        conn.close()
        return
        
    print("\n--- Pending Loan Requests ---")
    print(f"{'ID':<5} | {'Account No':<12} | {'Amount':<10} | {'Date & Time'}")
    print("-" * 60)
    for r in records:
        print(f"{r[0]:<5} | {r[1]:<12} | ₹{r[2]:<9.2f} | {r[4]}")
        
    loan_id = input("\nEnter Loan ID to approve/reject (or press enter to skip): ")
    if not loan_id.isdigit():
        conn.close()
        return
        
    action = input("Enter 'A' to Approve, 'R' to Reject: ").upper()
    if action == 'A':
        # Approve
        cursor.execute("SELECT account_no, amount FROM loans WHERE id = ?", (loan_id,))
        loan = cursor.fetchone()
        if loan:
            account_no, amount = loan
            cursor.execute("UPDATE loans SET status = 'APPROVED' WHERE id = ?", (loan_id,))
            cursor.execute("UPDATE customers SET balance = balance + ?, loan_balance = loan_balance + ? WHERE account_no = ?", (amount, amount, account_no))
            from transaction import log_transaction
            cursor.execute("SELECT balance FROM customers WHERE account_no = ?", (account_no,))
            new_balance = cursor.fetchone()[0]
            conn.commit()
            log_transaction(account_no, "LOAN APPROVED", amount, new_balance)
            print("\nLoan approved and amount credited.")
        else:
            print("\nInvalid Loan ID.")
    elif action == 'R':
        cursor.execute("UPDATE loans SET status = 'REJECTED' WHERE id = ?", (loan_id,))
        conn.commit()
        print("\nLoan rejected.")
    else:
        print("\nInvalid action.")
        
    conn.close()

from database import get_connection

def log_transaction(account_no, type, amount, balance_after):
    """Logs a transaction in the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO transactions (account_no, type, amount, balance_after)
        VALUES (?, ?, ?, ?)
    ''', (account_no, type, amount, balance_after))
    conn.commit()
    conn.close()

def get_transactions(account_no):
    """Retrieves all transactions for a specific account."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, type, amount, balance_after, date_time
        FROM transactions
        WHERE account_no = ?
        ORDER BY date_time DESC
    ''', (account_no,))
    records = cursor.fetchall()
    conn.close()
    return records
    
def get_all_transactions():
    """Admin function to retrieve all transactions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, account_no, type, amount, balance_after, date_time
        FROM transactions
        ORDER BY date_time DESC
    ''')
    records = cursor.fetchall()
    conn.close()
    return records

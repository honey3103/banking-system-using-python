import sqlite3
import os

DB_FILE = "bank.db"

def get_connection():
    return sqlite3.connect(DB_FILE)

def init_db():
    if os.path.exists(DB_FILE):
        try:
            os.remove(DB_FILE)
            print(f"Removed old {DB_FILE} for clean schema migration.")
        except Exception as e:
            print(f"Error removing {DB_FILE}: {e}")

    conn = get_connection()
    cursor = conn.cursor()
    
    # Create customers table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            account_no TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            email TEXT,
            address TEXT,
            pin_hash TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            loan_balance REAL DEFAULT 0.0,
            status TEXT DEFAULT 'ACTIVE'
        )
    ''')
    
    # Create transactions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            balance_after REAL NOT NULL,
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(account_no) REFERENCES customers(account_no)
        )
    ''')
    
    # Create loans table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'PENDING',
            date_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(account_no) REFERENCES customers(account_no)
        )
    ''')
    
    # Create credit cards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_no TEXT NOT NULL UNIQUE,
            credit_limit REAL DEFAULT 50000.0,
            spent REAL DEFAULT 0.0,
            status TEXT DEFAULT 'ACTIVE',
            FOREIGN KEY(account_no) REFERENCES customers(account_no)
        )
    ''')
    
    # Create crypto wallets table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_wallets (
            account_no TEXT PRIMARY KEY,
            btc_balance REAL DEFAULT 0.0,
            FOREIGN KEY(account_no) REFERENCES customers(account_no)
        )
    ''')
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")

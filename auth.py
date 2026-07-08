from database import get_connection
from utils import hash_pin, verify_pin, generate_otp, send_mock_otp
import random

OTP_STORE = {}

def register_customer(name, mobile, email, address, pin):
    """Registers a new customer and returns their generated account number."""
    # Generate a random 10 digit account number
    account_no = str(random.randint(1000000000, 9999999999))
    
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if mobile already exists
    cursor.execute("SELECT mobile FROM customers WHERE mobile = ? ", (mobile,))
    if cursor.fetchone():
        conn.close()
        return None, "Mobile number already registered."
        
    try:
        cursor.execute('''
            INSERT INTO customers (account_no, name, mobile, email, address, pin_hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (account_no, name, mobile, email, address, hash_pin(pin)))
        conn.commit()
    except Exception as e:
        conn.close()
        return None, str(e)
        
    conn.close()
    return account_no, "Registration successful."

def login_customer(account_no, pin):
    """Authenticates a customer and returns customer data if successful."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT account_no, name, pin_hash, status, balance 
        FROM customers WHERE account_no = ?
    ''', (account_no,))
    customer = cursor.fetchone()
    conn.close()
    
    if not customer:
        return None, "Invalid Account Number."
        
    if customer[3] != 'ACTIVE':
        return None, "Account is frozen. Please contact admin."
        
    if not verify_pin(pin, customer[2]):
        return None, "Invalid PIN."
        
    return {
        "account_no": customer[0],
        "name": customer[1],
        "status": customer[3],
        "balance": customer[4]
    }, "Login successful."

def login_admin(username, pin):
    """Simple admin authentication."""
    if username == "admin" and pin == "admin123":
        return True, "Login successful."
    return False, "Invalid Admin credentials."

def request_login_otp(account_no):
    """Generates an OTP and sends it to the customer's email."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM customers WHERE account_no = ?", (account_no,))
    row = cursor.fetchone()
    conn.close()
    
    if row and row[0]:
        email = row[0]
        otp = generate_otp()
        OTP_STORE[account_no] = otp
        send_mock_otp(email, otp)
        return True, otp
    return False, "Email not found for account."

def validate_login_otp(account_no, otp):
    """Validates the OTP for a given account."""
    if account_no in OTP_STORE and OTP_STORE[account_no] == otp:
        del OTP_STORE[account_no]
        return True, "OTP verified successfully."
    return False, "Invalid or expired OTP."

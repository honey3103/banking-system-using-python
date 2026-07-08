import hashlib
import os
import random

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

try:
    import qrcode
except ImportError:
    qrcode = None

def hash_pin(pin):
    """Returns SHA-256 hash of the PIN."""
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin, hashed_pin):
    """Verifies if the provided PIN matches the hashed PIN."""
    return hash_pin(pin) == hashed_pin

def clear_screen():
    """Clears the console screen."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_valid_amount(prompt):
    """Helper to get a valid positive amount."""
    while True:
        try:
            amount = float(input(prompt))
            if amount < 0:
                print("Amount cannot be negative. Try again.")
                continue
            return amount
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def get_valid_pin():
    """Helper to get a valid 4-digit PIN."""
    while True:
        pin = input("Enter 4-digit PIN: ")
        if len(pin) == 4 and pin.isdigit():
            return pin
        print("PIN must be exactly 4 digits. Try again.")

def generate_otp():
    """Generates a 6-digit OTP."""
    return str(random.randint(100000, 999999))

def send_mock_otp(email, otp):
    """Mocks sending an OTP to an email by writing it to a file and printing."""
    msg = f"\n--- MOCK EMAIL ---\nTo: {email}\nSubject: Your Bank OTP\nMessage: Your One-Time Password is {otp}. Do not share this.\n------------------\n"
    print(msg, flush=True)
    with open("otp.txt", "w") as f:
        f.write(msg)

def generate_pdf_statement(account_no, name, transactions, filename="statement.pdf"):
    """Generates a PDF statement of transactions."""
    if not FPDF:
        print("fpdf library not installed. Cannot generate PDF.")
        return False
        
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.cell(200, 10, txt=f"Bank Statement for Account: {account_no}", ln=1, align='C')
    pdf.cell(200, 10, txt=f"Name: {name}", ln=1, align='C')
    pdf.cell(200, 10, txt="---------------------------------------------------------", ln=1, align='C')
    
    pdf.set_font("Arial", size=10)
    pdf.cell(40, 10, "Date", 1)
    pdf.cell(30, 10, "Type", 1)
    pdf.cell(40, 10, "Amount", 1)
    pdf.cell(40, 10, "Balance After", 1)
    pdf.ln()
    
    for tx in transactions:
        pdf.cell(40, 10, str(tx[4])[:10], 1)
        pdf.cell(30, 10, str(tx[1]), 1)
        pdf.cell(40, 10, f"${float(tx[2]):.2f}", 1)
        pdf.cell(40, 10, f"${float(tx[3]):.2f}", 1)
        pdf.ln()
        
    pdf.output(filename)
    return True

def generate_qr_code(data, filename="qr.png"):
    """Generates a QR code image for receiving payments."""
    if not qrcode:
        print("qrcode library not installed. Cannot generate QR.")
        return False
        
    img = qrcode.make(data)
    img.save(filename)
    return True

import tkinter as tk
from tkinter import messagebox, simpledialog
from auth import login_customer, login_admin, request_login_otp, validate_login_otp
from database import get_connection, init_db
from customer import download_statement
from utils import generate_qr_code

class BankApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bank Management System - GUI")
        self.geometry("600x400")
        self.current_user = None
        
        # Configure layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.frames = {}
        for F in (LoginFrame, CustomerFrame, AdminFrame):
            page_name = F.__name__
            frame = F(parent=self, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
            
        self.show_frame("LoginFrame")

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        if hasattr(frame, 'on_show'):
            frame.on_show()
        frame.tkraise()
        
class LoginFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="Welcome to the Bank", font=("Helvetica", 18)).pack(pady=20)
        
        tk.Label(self, text="Account No / Username").pack()
        self.acc_entry = tk.Entry(self)
        self.acc_entry.pack(pady=5)
        
        tk.Label(self, text="PIN").pack()
        self.pin_entry = tk.Entry(self, show="*")
        self.pin_entry.pack(pady=5)
        
        tk.Button(self, text="Login", command=self.login, bg="blue", fg="white").pack(pady=10)
        
    def login(self):
        acc = self.acc_entry.get()
        pin = self.pin_entry.get()
        
        if not acc or not pin:
            messagebox.showwarning("Warning", "Fields cannot be empty.")
            return
            
        if acc == "admin":
            success, msg = login_admin(acc, pin)
            if success:
                self.controller.current_user = "admin"
                self.controller.show_frame("AdminFrame")
            else:
                messagebox.showerror("Error", msg)
        else:
            customer, msg = login_customer(acc, pin)
            if customer:
                success, otp_msg = request_login_otp(acc)
                if success:
                    otp = simpledialog.askstring("OTP Verification", f"Enter OTP sent to your email (Check Console):")
                    if not otp:
                        return
                    valid, val_msg = validate_login_otp(acc, otp)
                    if valid:
                        self.controller.current_user = customer
                        self.controller.show_frame("CustomerFrame")
                    else:
                        messagebox.showerror("Error", val_msg)
                else:
                    messagebox.showerror("Error", otp_msg)
            else:
                messagebox.showerror("Error", msg)

class CustomerFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.welcome_label = tk.Label(self, text="Customer Dashboard", font=("Helvetica", 16))
        self.welcome_label.pack(pady=10)
        
        tk.Button(self, text="Check Balance & Loans", command=self.check_bal).pack(pady=5)
        tk.Button(self, text="Request Loan", command=self.req_loan).pack(pady=5)
        tk.Button(self, text="Download Statement PDF", command=self.dl_pdf).pack(pady=5)
        tk.Button(self, text="Generate Receive QR", command=self.gen_qr).pack(pady=5)
        tk.Button(self, text="Logout", command=self.logout, bg="red", fg="white").pack(pady=20)
        
    def on_show(self):
        if self.controller.current_user and isinstance(self.controller.current_user, dict):
            self.welcome_label.config(text=f"Welcome, {self.controller.current_user['name']}")

    def check_bal(self):
        acc = self.controller.current_user["account_no"]
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT balance, loan_balance FROM customers WHERE account_no=?", (acc,))
        bal, loan = c.fetchone()
        conn.close()
        messagebox.showinfo("Balance Info", f"Available Balance: ₹{bal:.2f}\nOutstanding Loan: ₹{loan:.2f}")

    def req_loan(self):
        amount = simpledialog.askfloat("Loan Request", "Enter loan amount: ₹")
        if amount and amount > 0:
            acc = self.controller.current_user["account_no"]
            conn = get_connection()
            c = conn.cursor()
            c.execute("INSERT INTO loans (account_no, amount, status) VALUES (?, ?, 'PENDING')", (acc, amount))
            conn.commit()
            conn.close()
            messagebox.showinfo("Success", "Loan request submitted for admin approval.")

    def dl_pdf(self):
        acc = self.controller.current_user["account_no"]
        try:
            download_statement(acc)
            messagebox.showinfo("Success", f"Statement downloaded as statement_{acc}.pdf")
        except Exception as e:
            messagebox.showerror("Error", f"Could not generate PDF: {e}")

    def gen_qr(self):
        acc = self.controller.current_user["account_no"]
        data = f"upi://pay?pa={acc}@bank&pn={self.controller.current_user['name']}"
        filename = f"qr_{acc}.png"
        try:
            if generate_qr_code(data, filename):
                messagebox.showinfo("Success", f"QR Code generated as {filename}")
            else:
                messagebox.showerror("Error", "qrcode library not installed.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def logout(self):
        self.controller.current_user = None
        self.controller.show_frame("LoginFrame")

class AdminFrame(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="Admin Dashboard", font=("Helvetica", 16)).pack(pady=20)
        
        tk.Button(self, text="View Pending Loans", command=self.view_loans).pack(pady=5)
        tk.Button(self, text="Logout", command=self.logout, bg="red", fg="white").pack(pady=20)

    def view_loans(self):
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, account_no, amount FROM loans WHERE status = 'PENDING'")
        records = c.fetchall()
        conn.close()
        
        if not records:
            messagebox.showinfo("Loans", "No pending loan requests.")
            return
            
        loans_str = "\n".join([f"ID: {r[0]} | Acc: {r[1]} | ₹{r[2]:.2f}" for r in records])
        loan_id = simpledialog.askinteger("Approve Loan", f"Pending Loans:\n{loans_str}\n\nEnter Loan ID to APPROVE:")
        
        if loan_id:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT account_no, amount FROM loans WHERE id = ? AND status='PENDING'", (loan_id,))
            loan = c.fetchone()
            if loan:
                acc, amt = loan
                c.execute("UPDATE loans SET status = 'APPROVED' WHERE id = ?", (loan_id,))
                c.execute("UPDATE customers SET balance = balance + ?, loan_balance = loan_balance + ? WHERE account_no = ?", (amt, amt, acc))
                conn.commit()
                messagebox.showinfo("Success", f"Loan ID {loan_id} approved. ₹{amt:.2f} credited to {acc}.")
            else:
                messagebox.showerror("Error", "Invalid or already processed Loan ID.")
            conn.close()

    def logout(self):
        self.controller.current_user = None
        self.controller.show_frame("LoginFrame")

if __name__ == "__main__":
    init_db()
    app = BankApp()
    app.mainloop()

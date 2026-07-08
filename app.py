import os
import threading
import time
import csv
import io
from flask import Flask, render_template, request, jsonify, session, send_file, Response
from database import get_connection, init_db
from auth import login_admin, login_customer, register_customer, request_login_otp, validate_login_otp
from transaction import log_transaction, get_transactions, get_all_transactions
from utils import generate_pdf_statement

app = Flask(__name__)
app.secret_key = "super_secret_bank_key_123"

# Initialize DB if not exists
if not os.path.exists("bank.db"):
    init_db()

# --- Page Routes ---
@app.route('/')
def index():
    if 'user' in session:
        if session['user'] == 'admin':
            return render_template('admin.html')
        return render_template('dashboard.html')
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session or session['user'] == 'admin':
        return render_template('index.html')
    return render_template('dashboard.html')

@app.route('/admin')
def admin():
    if 'user' not in session or session['user'] != 'admin':
        return render_template('index.html')
    return render_template('admin.html')

# --- API Routes ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    acc = data.get('account_no')
    pin = data.get('pin')
    
    if acc == 'admin':
        success, msg = login_admin(acc, pin)
        if success:
            session['user'] = 'admin'
            return jsonify({'role': 'admin', 'message': msg})
        return jsonify({'error': msg}), 401
    
    customer, msg = login_customer(acc, pin)
    if customer:
        success, otp_val = request_login_otp(acc)
        if success:
            return jsonify({'require_otp': True, 'message': 'OTP sent', 'otp': otp_val})
        return jsonify({'error': otp_val}), 500
    return jsonify({'error': msg}), 401

@app.route('/api/verify_otp', methods=['POST'])
def api_verify_otp():
    data = request.json
    acc = data.get('account_no')
    otp = data.get('otp')
    
    valid, msg = validate_login_otp(acc, otp)
    if valid:
        session['user'] = acc
        return jsonify({'message': msg})
    return jsonify({'error': msg}), 401

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    acc, msg = register_customer(data.get('name'), data.get('mobile'), data.get('email'), '', data.get('pin'))
    if acc:
        return jsonify({'account_no': acc, 'message': msg})
    return jsonify({'error': msg}), 400

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out'})

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    if 'user' not in session or session['user'] == 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
        
    acc = session['user']
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT name, balance, loan_balance FROM customers WHERE account_no = ?", (acc,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'User not found'}), 404
        
    txs = get_transactions(acc)
    # Format transactions for JSON
    tx_list = [{'id': t[0], 'type': t[1], 'amount': t[2], 'balance_after': t[3], 'date_time': t[4]} for t in txs]
    
    return jsonify({
        'account_no': acc,
        'name': row[0],
        'balance': row[1],
        'loan_balance': row[2],
        'transactions': tx_list
    })

@app.route('/api/deposit', methods=['POST'])
def api_deposit():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    acc = session['user']
    amt = float(request.json.get('amount', 0))
    if amt <= 0: return jsonify({'error': 'Invalid amount'}), 400
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE customers SET balance = balance + ? WHERE account_no = ?", (amt, acc))
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    new_bal = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    log_transaction(acc, "DEPOSIT", amt, new_bal)
    return jsonify({'message': f'Deposited ₹{amt}'})

@app.route('/api/withdraw', methods=['POST'])
def api_withdraw():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    acc = session['user']
    amt = float(request.json.get('amount', 0))
    if amt <= 0: return jsonify({'error': 'Invalid amount'}), 400
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    bal = c.fetchone()[0]
    
    if bal < amt:
        conn.close()
        return jsonify({'error': 'Insufficient balance'}), 400
        
    new_bal = bal - amt
    c.execute("UPDATE customers SET balance = ? WHERE account_no = ?", (new_bal, acc))
    conn.commit()
    conn.close()
    
    log_transaction(acc, "WITHDRAW", amt, new_bal)
    return jsonify({'message': f'Withdrew ₹{amt}'})

@app.route('/api/transfer', methods=['POST'])
def api_transfer():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    acc = session['user']
    target = request.json.get('target_account')
    amt = float(request.json.get('amount', 0))
    
    if amt <= 0 or target == acc: return jsonify({'error': 'Invalid transfer'}), 400
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT status FROM customers WHERE account_no = ?", (target,))
    t_status = c.fetchone()
    
    if not t_status or t_status[0] != 'ACTIVE':
        conn.close()
        return jsonify({'error': 'Invalid or frozen target account'}), 400
        
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    bal = c.fetchone()[0]
    if bal < amt:
        conn.close()
        return jsonify({'error': 'Insufficient balance'}), 400
        
    c.execute("UPDATE customers SET balance = balance - ? WHERE account_no = ?", (amt, acc))
    c.execute("UPDATE customers SET balance = balance + ? WHERE account_no = ?", (amt, target))
    
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    sender_bal = c.fetchone()[0]
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (target,))
    receiver_bal = c.fetchone()[0]
    
    conn.commit()
    conn.close()
    
    log_transaction(acc, f"TRANSFER TO {target}", amt, sender_bal)
    log_transaction(target, f"TRANSFER FROM {acc}", amt, receiver_bal)
    
    return jsonify({'message': f'Transferred ₹{amt} to {target}'})

@app.route('/api/loan', methods=['POST'])
def api_loan():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    acc = session['user']
    amt = float(request.json.get('amount', 0))
    if amt <= 0: return jsonify({'error': 'Invalid amount'}), 400
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO loans (account_no, amount, status) VALUES (?, ?, 'PENDING')", (acc, amt))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Loan requested successfully.'})

@app.route('/api/download_statement', methods=['GET'])
def api_download_statement():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    
    acc = session['user']
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT name FROM customers WHERE account_no = ?", (acc,))
    name = c.fetchone()[0]
    conn.close()
    
    txs = get_transactions(acc)
    filename = f"statement_{acc}.pdf"
    
    if generate_pdf_statement(acc, name, txs, filename):
        return send_file(filename, as_attachment=True)
    return jsonify({'error': 'Failed to generate PDF. Ensure fpdf is installed.'}), 500

@app.route('/api/download_csv', methods=['GET'])
def api_download_csv():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    acc = session['user']
    txs = get_transactions(acc)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Type', 'Amount (INR)', 'Balance After (INR)', 'Date Time'])
    for tx in txs:
        writer.writerow([tx[0], tx[1], tx[2], tx[3], tx[4]])
        
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename=statement_{acc}.csv'
    return response

# --- Crypto Routes ---
BTC_MOCK_PRICE_INR = 5000000.0 # 1 BTC = ₹50 Lakhs

@app.route('/api/crypto/info', methods=['GET'])
def api_crypto_info():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    acc = session['user']
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT btc_balance FROM crypto_wallets WHERE account_no = ?", (acc,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO crypto_wallets (account_no, btc_balance) VALUES (?, 0.0)", (acc,))
        conn.commit()
        btc_balance = 0.0
    else:
        btc_balance = row[0]
    conn.close()
    
    return jsonify({
        'btc_balance': btc_balance,
        'btc_price_inr': BTC_MOCK_PRICE_INR,
        'portfolio_value_inr': btc_balance * BTC_MOCK_PRICE_INR
    })

@app.route('/api/crypto/buy', methods=['POST'])
def api_crypto_buy():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    acc = session['user']
    inr_amount = float(request.json.get('amount', 0))
    if inr_amount <= 0: return jsonify({'error': 'Invalid amount'}), 400
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    bal = c.fetchone()[0]
    
    if bal < inr_amount:
        conn.close()
        return jsonify({'error': 'Insufficient savings balance'}), 400
        
    btc_to_add = inr_amount / BTC_MOCK_PRICE_INR
    
    c.execute("UPDATE customers SET balance = balance - ? WHERE account_no = ?", (inr_amount, acc))
    c.execute("UPDATE crypto_wallets SET btc_balance = btc_balance + ? WHERE account_no = ?", (btc_to_add, acc))
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    new_bal = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    log_transaction(acc, "BUY CRYPTO", inr_amount, new_bal)
    return jsonify({'message': f'Bought {btc_to_add:.6f} BTC for ₹{inr_amount}'})

@app.route('/api/crypto/sell', methods=['POST'])
def api_crypto_sell():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    acc = session['user']
    btc_amount = float(request.json.get('amount', 0)) # amount in BTC
    if btc_amount <= 0: return jsonify({'error': 'Invalid amount'}), 400
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT btc_balance FROM crypto_wallets WHERE account_no = ?", (acc,))
    row = c.fetchone()
    btc_bal = row[0] if row else 0.0
    
    if btc_bal < btc_amount:
        conn.close()
        return jsonify({'error': 'Insufficient BTC balance'}), 400
        
    inr_to_add = btc_amount * BTC_MOCK_PRICE_INR
    
    c.execute("UPDATE crypto_wallets SET btc_balance = btc_balance - ? WHERE account_no = ?", (btc_amount, acc))
    c.execute("UPDATE customers SET balance = balance + ? WHERE account_no = ?", (inr_to_add, acc))
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    new_bal = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    log_transaction(acc, "SELL CRYPTO", inr_to_add, new_bal)
    return jsonify({'message': f'Sold {btc_amount:.6f} BTC for ₹{inr_to_add}'})

@app.route('/api/admin/dashboard', methods=['GET'])
def api_admin_dashboard():
    if 'user' not in session or session['user'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
        
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(balance) FROM customers")
    total_dep = c.fetchone()[0] or 0.0
    
    c.execute("SELECT id, account_no, amount, status, date_time FROM loans WHERE status='PENDING'")
    loans = c.fetchall()
    loan_list = [{'id': l[0], 'account_no': l[1], 'amount': l[2], 'date_time': l[4]} for l in loans]
    conn.close()
    
    all_tx = get_all_transactions()
    all_tx_list = [{'id': t[0], 'account_no': t[1], 'type': t[2], 'amount': t[3], 'date_time': t[5]} for t in all_tx]
    
    return jsonify({
        'total_deposits': total_dep,
        'pending_loans': loan_list,
        'all_transactions': all_tx_list
    })

@app.route('/api/admin/approve_loan', methods=['POST'])
def api_admin_approve_loan():
    if 'user' not in session or session['user'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
        
    loan_id = request.json.get('loan_id')
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT account_no, amount FROM loans WHERE id = ? AND status='PENDING'", (loan_id,))
    loan = c.fetchone()
    
    if not loan:
        conn.close()
        return jsonify({'error': 'Invalid or already processed loan'}), 400
        
    acc, amt = loan
    c.execute("UPDATE loans SET status='APPROVED' WHERE id=?", (loan_id,))
    c.execute("UPDATE customers SET balance=balance+?, loan_balance=loan_balance+? WHERE account_no=?", (amt, amt, acc))
    
    c.execute("SELECT balance FROM customers WHERE account_no=?", (acc,))
    new_bal = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    log_transaction(acc, "LOAN APPROVED", amt, new_bal)
    return jsonify({'message': 'Loan approved.'})

@app.route('/api/analytics', methods=['GET'])
def api_analytics():
    if 'user' not in session or session['user'] == 'admin':
        return jsonify({'error': 'Unauthorized'}), 401
    
    acc = session['user']
    txs = get_transactions(acc)
    # We want to return data for chart.js
    # dates, balances, income, expense
    dates = []
    balances = []
    income = 0
    expense = 0
    
    # tx format: id, type, amount, balance_after, date_time
    for t in reversed(txs): # oldest first
        dates.append(t[4][:10])
        balances.append(t[3])
        if t[1] == 'DEPOSIT' or 'FROM' in t[1] or 'APPROVED' in t[1] or t[1] == 'INTEREST':
            income += t[2]
        else:
            expense += t[2]
            
    return jsonify({
        'dates': dates,
        'balances': balances,
        'income': income,
        'expense': expense
    })

@app.route('/api/cc/info', methods=['GET'])
def api_cc_info():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT credit_limit, spent, status FROM credit_cards WHERE account_no = ?", (session['user'],))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({'has_card': True, 'limit': row[0], 'spent': row[1], 'status': row[2]})
    return jsonify({'has_card': False})

@app.route('/api/cc/request', methods=['POST'])
def api_cc_request():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO credit_cards (account_no) VALUES (?)", (session['user'],))
        conn.commit()
    except Exception:
        conn.close()
        return jsonify({'error': 'Card already exists'}), 400
    conn.close()
    return jsonify({'message': 'Credit card issued with a ₹50,000 limit.'})

@app.route('/api/cc/spend', methods=['POST'])
def api_cc_spend():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    amt = float(request.json.get('amount', 0))
    if amt <= 0: return jsonify({'error': 'Invalid amount'}), 400
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT credit_limit, spent FROM credit_cards WHERE account_no = ?", (session['user'],))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'No credit card found'}), 400
        
    limit, spent = row
    if spent + amt > limit:
        conn.close()
        return jsonify({'error': 'Credit limit exceeded'}), 400
        
    c.execute("UPDATE credit_cards SET spent = spent + ? WHERE account_no = ?", (amt, session['user']))
    conn.commit()
    conn.close()
    
    # Log this as a CC transaction in normal history or keep separate. 
    # For simplicity, we just keep it out of normal tx or log it. Let's log it.
    log_transaction(session['user'], "CC SPEND", amt, limit - (spent + amt))
    return jsonify({'message': f'Spent ₹{amt} on Credit Card'})

@app.route('/api/cc/pay', methods=['POST'])
def api_cc_pay():
    if 'user' not in session: return jsonify({'error': 'Unauthorized'}), 401
    amt = float(request.json.get('amount', 0))
    if amt <= 0: return jsonify({'error': 'Invalid amount'}), 400
    
    acc = session['user']
    conn = get_connection()
    c = conn.cursor()
    
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    bal = c.fetchone()[0]
    if bal < amt:
        conn.close()
        return jsonify({'error': 'Insufficient savings balance'}), 400
        
    c.execute("SELECT spent FROM credit_cards WHERE account_no = ?", (acc,))
    row = c.fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'No credit card found'}), 400
        
    spent = row[0]
    if amt > spent:
        amt = spent # Only pay what is owed
        
    c.execute("UPDATE customers SET balance = balance - ? WHERE account_no = ?", (amt, acc))
    c.execute("UPDATE credit_cards SET spent = spent - ? WHERE account_no = ?", (amt, acc))
    c.execute("SELECT balance FROM customers WHERE account_no = ?", (acc,))
    new_bal = c.fetchone()[0]
    conn.commit()
    conn.close()
    
    log_transaction(acc, "CC BILL PAYMENT", amt, new_bal)
    return jsonify({'message': f'Paid ₹{amt} towards Credit Card bill'})

def interest_accrual_job():
    """Background job that accrues 1% interest every 60 seconds (Simulation)."""
    while True:
        time.sleep(60)
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT account_no, balance FROM customers WHERE status = 'ACTIVE' AND balance > 0")
            customers = c.fetchall()
            
            for acc, bal in customers:
                interest = bal * 0.01 # 1% interest per minute for simulation
                new_bal = bal + interest
                c.execute("UPDATE customers SET balance = ? WHERE account_no = ?", (new_bal, acc))
                c.execute('''
                    INSERT INTO transactions (account_no, type, amount, balance_after)
                    VALUES (?, ?, ?, ?)
                ''', (acc, 'INTEREST', interest, new_bal))
            
            conn.commit()
            conn.close()
            print("[System] Interest accrued for active accounts.")
        except Exception as e:
            print(f"[System] Error in interest accrual: {e}")

if __name__ == '__main__':
    # Start background thread
    t = threading.Thread(target=interest_accrual_job, daemon=True)
    t.start()
    app.run(debug=True, port=5000, use_reloader=False)

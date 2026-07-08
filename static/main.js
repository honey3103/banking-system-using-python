// UI Navigation
const loginPanel = document.getElementById('loginPanel');
const registerPanel = document.getElementById('registerPanel');
const otpModal = document.getElementById('otpModal');

if (document.getElementById('showRegister')) {
    document.getElementById('showRegister').addEventListener('click', (e) => {
        e.preventDefault();
        loginPanel.classList.add('hidden');
        registerPanel.classList.remove('hidden');
    });
}

if (document.getElementById('showLogin')) {
    document.getElementById('showLogin').addEventListener('click', (e) => {
        e.preventDefault();
        registerPanel.classList.add('hidden');
        loginPanel.classList.remove('hidden');
    });
}

// Modals
function showModal(id) {
    document.getElementById(id).classList.add('active');
}

function closeModal(id) {
    document.getElementById(id).classList.remove('active');
}

// Authentication
let pendingLoginAcc = null;

if (document.getElementById('loginForm')) {
    document.getElementById('loginForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const accountNo = document.getElementById('accountNo').value;
        const pin = document.getElementById('pin').value;
        
        try {
            const res = await fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ account_no: accountNo, pin: pin })
            });
            const data = await res.json();
            
            if (res.ok) {
                if (data.role === 'admin') {
                    window.location.href = '/admin';
                } else if (data.require_otp) {
                    pendingLoginAcc = accountNo;
                    if (data.otp) {
                        document.getElementById('otpInput').value = data.otp;
                    }
                    showModal('otpModal');
                }
            } else {
                alert(data.error || 'Login failed');
            }
        } catch (err) {
            alert('Server error');
        }
    });
}

if (document.getElementById('verifyOtpBtn')) {
    document.getElementById('verifyOtpBtn').addEventListener('click', async () => {
        const otp = document.getElementById('otpInput').value;
        if (!otp) return;
        
        try {
            const res = await fetch('/api/verify_otp', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ account_no: pendingLoginAcc, otp: otp })
            });
            const data = await res.json();
            
            if (res.ok) {
                window.location.href = '/dashboard';
            } else {
                alert(data.error || 'Invalid OTP');
            }
        } catch (err) {
            alert('Server error');
        }
    });
    
    document.getElementById('cancelOtpBtn').addEventListener('click', () => {
        closeModal('otpModal');
        pendingLoginAcc = null;
    });
}

if (document.getElementById('registerForm')) {
    document.getElementById('registerForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const payload = {
            name: document.getElementById('regName').value,
            mobile: document.getElementById('regMobile').value,
            email: document.getElementById('regEmail').value,
            pin: document.getElementById('regPin').value
        };
        
        try {
            const res = await fetch('/api/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            
            if (res.ok) {
                alert(`Registration successful! Your Account No is: ${data.account_no}`);
                document.getElementById('showLogin').click();
            } else {
                alert(data.error || 'Registration failed');
            }
        } catch (err) {
            alert('Server error');
        }
    });
}

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    window.location.href = '/';
}

// Dashboard Functions
let balChart = null;
let pChart = null;

async function loadDashboard() {
    try {
        const res = await fetch('/api/dashboard');
        if (!res.ok) {
            window.location.href = '/';
            return;
        }
        const data = await res.json();
        
        document.getElementById('welcomeMessage').innerText = `Welcome back, ${data.name}`;
        document.getElementById('balanceAmount').innerText = `₹${data.balance.toFixed(2)}`;
        document.getElementById('loanAmount').innerText = `₹${data.loan_balance.toFixed(2)}`;
        
        const tbody = document.getElementById('transactionTableBody');
        tbody.innerHTML = '';
        data.transactions.forEach(tx => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${tx.date_time.substring(0, 10)}</td>
                <td><span class="badge ${tx.type === 'DEPOSIT' || tx.type.includes('FROM') || tx.type.includes('APPROVED') || tx.type === 'INTEREST' ? 'badge-success' : 'badge-danger'}">${tx.type}</span></td>
                <td>₹${tx.amount.toFixed(2)}</td>
                <td>₹${tx.balance_after.toFixed(2)}</td>
            `;
            tbody.appendChild(tr);
        });
        
        // Load CC info
        const ccRes = await fetch('/api/cc/info');
        if (ccRes.ok) {
            const ccData = await ccRes.json();
            if (ccData.has_card) {
                document.getElementById('ccStatus').innerText = `Spent: ₹${ccData.spent.toFixed(2)}`;
                document.getElementById('ccLimit').innerText = `Limit: ₹${ccData.limit.toFixed(2)}`;
                document.getElementById('ccOptions').classList.add('hidden');
                document.getElementById('ccActive').classList.remove('hidden');
            } else {
                document.getElementById('ccOptions').classList.remove('hidden');
                document.getElementById('ccActive').classList.add('hidden');
            }
        }
        

    } catch (err) {
        console.error(err);
    }
}


async function submitAction(endpoint, payload, modalId) {
    try {
        const res = await fetch(`/api/${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (res.ok) {
            alert(data.message || 'Success');
            closeModal(modalId);
            loadDashboard(); // Reload data
        } else {
            alert(data.error || 'Operation failed');
        }
    } catch (err) {
        alert('Server error');
    }
}

function submitDeposit() {
    const amt = parseFloat(document.getElementById('depositAmt').value);
    if (!amt || amt <= 0) return alert('Invalid amount');
    submitAction('deposit', { amount: amt }, 'depositModal');
}

function submitWithdraw() {
    const amt = parseFloat(document.getElementById('withdrawAmt').value);
    if (!amt || amt <= 0) return alert('Invalid amount');
    submitAction('withdraw', { amount: amt }, 'withdrawModal');
}

function submitTransfer() {
    const acc = document.getElementById('transferAcc').value;
    const amt = parseFloat(document.getElementById('transferAmt').value);
    if (!acc || !amt || amt <= 0) return alert('Invalid input');
    submitAction('transfer', { target_account: acc, amount: amt }, 'transferModal');
}

function submitLoan() {
    const amt = parseFloat(document.getElementById('loanAmt').value);
    if (!amt || amt <= 0) return alert('Invalid amount');
    submitAction('loan', { amount: amt }, 'loanModal');
}

async function requestCard() {
    try {
        const res = await fetch('/api/cc/request', { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
            alert(data.message);
            loadDashboard();
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert('Server error');
    }
}

function spendCC() {
    const amt = parseFloat(document.getElementById('ccSpendAmt').value);
    if (!amt || amt <= 0) return alert('Invalid amount');
    submitAction('cc/spend', { amount: amt }, 'ccModal');
}

function payCC() {
    const amt = parseFloat(document.getElementById('ccPayAmt').value);
    if (!amt || amt <= 0) return alert('Invalid amount');
    submitAction('cc/pay', { amount: amt }, 'ccModal');
}

function buyCrypto() {
    const amt = parseFloat(document.getElementById('buyCryptoAmt').value);
    if (!amt || amt <= 0) return alert('Invalid amount');
    submitAction('crypto/buy', { amount: amt }, 'cryptoModal');
}

function sellCrypto() {
    const amt = parseFloat(document.getElementById('sellCryptoAmt').value);
    if (!amt || amt <= 0) return alert('Invalid amount');
    submitAction('crypto/sell', { amount: amt }, 'cryptoModal');
}

async function downloadStatement() {
    window.location.href = '/api/download_statement';
}

async function downloadStatementCSV() {
    window.location.href = '/api/download_csv';
}

// Admin Dashboard Functions
async function loadAdminDashboard() {
    try {
        const res = await fetch('/api/admin/dashboard');
        if (!res.ok) {
            window.location.href = '/';
            return;
        }
        const data = await res.json();
        
        document.getElementById('totalDeposits').innerText = `₹${data.total_deposits.toFixed(2)}`;
        document.getElementById('pendingLoanCount').innerText = data.pending_loans.length;
        
        const lbody = document.getElementById('loanTableBody');
        lbody.innerHTML = '';
        data.pending_loans.forEach(loan => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${loan.id}</td>
                <td>${loan.account_no}</td>
                <td>₹${loan.amount.toFixed(2)}</td>
                <td>${loan.date_time.substring(0, 10)}</td>
                <td>
                    <button class="btn" style="padding: 0.25rem 0.5rem; width: auto;" onclick="approveLoan(${loan.id})">Approve</button>
                </td>
            `;
            lbody.appendChild(tr);
        });

        const tbody = document.getElementById('allTxTableBody');
        tbody.innerHTML = '';
        data.all_transactions.forEach(tx => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${tx.id}</td>
                <td>${tx.account_no}</td>
                <td><span class="badge ${tx.type === 'DEPOSIT' || tx.type.includes('FROM') ? 'badge-success' : 'badge-danger'}">${tx.type}</span></td>
                <td>₹${tx.amount.toFixed(2)}</td>
                <td>${tx.date_time.substring(0, 10)}</td>
            `;
            tbody.appendChild(tr);
        });
    } catch (err) {
        console.error(err);
    }
}

async function approveLoan(loanId) {
    if (!confirm('Approve this loan?')) return;
    try {
        const res = await fetch('/api/admin/approve_loan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ loan_id: loanId })
        });
        const data = await res.json();
        
        if (res.ok) {
            alert('Loan approved successfully');
            loadAdminDashboard();
        } else {
            alert(data.error || 'Failed to approve loan');
        }
    } catch (err) {
        alert('Server error');
    }
}

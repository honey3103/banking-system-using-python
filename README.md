# Bank Management System

A CLI-based Bank Management System built with Python 3 and SQLite. This project simulates a real-world console banking application with secure user authentication, transactional histories, and a fully functional admin dashboard.

## Features
- **Customer Operations**: Register, Login, Deposit, Withdraw, Transfer, Check Balance, Transaction History, and Change PIN.
- **Admin Operations**: View all customers, search by account/mobile, freeze/unfreeze accounts, delete accounts, view total bank balance and global transactions.
- **Security**: User PINs are stored securely using SHA-256 hashes. Inputs are validated properly.
- **Persistence**: SQLite database (`bank.db`) seamlessly manages data persistence across restarts.

## Tech Stack
- **Language**: Python 3
- **Database**: SQLite (built-in)
- **Encryption**: `hashlib` (built-in)

## How to Run
1. Make sure you have Python 3 installed.
2. Open your terminal or command prompt.
3. Navigate to the project folder.
4. Run the application:
   ```bash
   python main.py
   ```

## Default Credentials
For administrative tasks, use the following credentials:
- **Admin Username**: `admin`
- **Admin PIN**: `admin123`

## File Structure
- `main.py`: Entry point, contains the interactive menus and navigation.
- `database.py`: Handles database initialization and connection routing.
- `auth.py`: Authentication, PIN validation, and registration logic.
- `customer.py`: Customer dashboard operations (deposit, withdraw, transfer).
- `admin.py`: Administrative operations (freeze, view transactions).
- `transaction.py`: Transaction logging and retrieval handlers.
- `utils.py`: Shared utilities (hashing, terminal clearing, input validation).

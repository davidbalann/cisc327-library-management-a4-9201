"""
Library Service Module - Business Logic Functions
Contains all the core business logic for the Library Management System
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from services.payment_service import PaymentGateway
from database import (
    get_book_by_id, get_book_by_isbn, get_patron_borrow_count,
    insert_book, insert_borrow_record, update_book_availability,
    update_borrow_record_return_date, get_all_books,
    get_patron_borrowed_books, get_db_connection
)

def add_book_to_catalog(title: str, author: str, isbn: str, total_copies: int) -> Tuple[bool, str]:
    """
    Add a new book to the catalog.
    Implements R1: Book Catalog Management

    Args:
        title: Book title (max 200 chars)
        author: Book author (max 100 chars)
        isbn: 13-digit ISBN
        total_copies: Number of copies (positive integer)

    Returns:
        tuple: (success: bool, message: str)
    """
    # Input validation
    if not title or not title.strip():
        return False, "Title is required."

    if len(title.strip()) > 200:
        return False, "Title must be less than 200 characters."

    if not author or not author.strip():
        return False, "Author is required."

    if len(author.strip()) > 100:
        return False, "Author must be less than 100 characters."

    if len(isbn) != 13:
        return False, "ISBN must be exactly 13 digits."

    if not isinstance(total_copies, int) or total_copies <= 0:
        return False, "Total copies must be a positive integer."

    # Check for duplicate ISBN
    existing = get_book_by_isbn(isbn)
    if existing:
        return False, "A book with this ISBN already exists."

    # Insert new book
    success = insert_book(title.strip(), author.strip(), isbn, total_copies, total_copies)
    if success:
        return True, f'Book "{title.strip()}" has been successfully added to the catalog.'
    else:
        return False, "Database error occurred while adding the book."

def borrow_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    """
    Allow a patron to borrow a book.
    Implements R3 as per requirements

    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book to borrow

    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."

    # Check if book exists and is available
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."

    if book['available_copies'] <= 0:
        return False, "This book is currently not available."

    # Check patron's current borrowed books count
    current_borrowed = get_patron_borrow_count(patron_id)

    if current_borrowed > 5:
        return False, "You have reached the maximum borrowing limit of 5 books."

    # Create borrow record
    borrow_date = datetime.now()
    due_date = borrow_date + timedelta(days=14)

    # Insert borrow record and update availability
    borrow_success = insert_borrow_record(patron_id, book_id, borrow_date, due_date)
    if not borrow_success:
        return False, "Database error occurred while creating borrow record."

    availability_success = update_book_availability(book_id, -1)
    if not availability_success:
        return False, "Database error occurred while updating book availability."

    return True, f'Successfully borrowed "{book["title"]}". Due date: {due_date.strftime("%Y-%m-%d")}.'

def return_book_by_patron(patron_id: str, book_id: int) -> Tuple[bool, str]:
    # Goal: mark a book as returned by a specific patron and compute any late fee.
    # Assumptions:
    #  - patron_id is a 6-digit string (e.g., "123456")
    #  - there is exactly one active borrow per (patron, book) at a time
    #  - helper DB functions handle their own errors where appropriate

    # 1) Basic input validation for patron_id (course spec: exactly 6 digits)
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits."

    # 2) Check that the book actually exists before we do anything else
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found."

    # 3) Verify that THIS patron currently has THIS book borrowed
    #    (avoid returning books that aren't out or belong to someone else)
    active_borrows = get_patron_borrowed_books(patron_id)
    active = next((r for r in active_borrows if r['book_id'] == book_id), None)
    if not active:
        return False, "No active borrow record for this patron and book."

    # 4) Compute the late fee BEFORE we write the return date,
    #    so the calculation uses the "still borrowed" state.
    fee_info = calculate_late_fee_for_book(patron_id, book_id)
    fee = float(fee_info.get('fee_amount', 0.0))
    days_overdue = int(fee_info.get('days_overdue', 0))

    # 5) Set the return date on the borrow record (marks it as closed)
    now = datetime.now()
    if not update_borrow_record_return_date(patron_id, book_id, now):
        # If this fails, bail out early to keep data consistent
        return False, "Database error occurred while updating return record."

    # 6) Increment availability carefully:
    #    Only increment if available_copies < total_copies to avoid overflows
    refreshed = get_book_by_id(book_id)
    if refreshed and refreshed['available_copies'] < refreshed['total_copies']:
        if not update_book_availability(book_id, +1):
            # Return is recorded, but inventory didn't bump — report partial success
            return False, "Return recorded but failed to update book availability."
    # else: if counts already maxed out, we skip to avoid exceeding total copies

    # 7) Build a user-friendly message including fee details if overdue
    if days_overdue > 0 and fee > 0:
        msg = (f'Book "{book["title"]}" returned successfully. '
               f'Late fee: ${fee:.2f} for {days_overdue} day(s) overdue.')
    else:
        msg = f'Book "{book["title"]}" returned successfully. No late fee.'
    return True, msg


def calculate_late_fee_for_book(patron_id: str, book_id: int) -> Dict:
    """
    Purpose: Given a patron and a book, figure out if it's overdue and how much the fee is.
    Spec (R5):
      • Due 14 days after borrow (the due_date is already stored in DB)
      • $0.50/day for first 7 overdue days; $1.00/day thereafter
      • Hard cap: $15.00 per book
      • Return a dict with 'days_overdue', 'fee_amount', and 'status'
    """

    # 1) Validate inputs early so we don't do unnecessary DB work
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Invalid patron ID'}

    book = get_book_by_id(book_id)
    if not book:
        return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Book not found'}

    # 2) Find the active borrow record for this (patron, book)
    #    If there isn't one, there's nothing to charge.
    active_borrows = get_patron_borrowed_books(patron_id)
    record = next((r for r in active_borrows if r['book_id'] == book_id), None)
    if not record:
        return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'No active borrow for this patron and book'}

    # 3) Compute days overdue based on today's date vs stored due_date
    now = datetime.now().date()
    due = record['due_date'].date()
    days_overdue = (now - due).days

    # Not overdue → no fee
    if days_overdue <= 0:
        return {'fee_amount': 0.00, 'days_overdue': 0, 'status': 'Not overdue'}

    # 4) Apply fee formula with the $15 cap:
    #    - First 7 days at $0.50/day
    #    - After that at $1.00/day
    first7 = min(days_overdue, 7) * 0.50
    rest = max(days_overdue - 7, 0) * 1.00
    fee = min(first7 + rest, 15.00)

    return {'fee_amount': round(fee, 2), 'days_overdue': days_overdue, 'status': 'Overdue'}


def search_books_in_catalog(search_term: str, search_type: str) -> List[Dict]:
    """
    Purpose: Basic catalog search for title/author/isbn.
    Spec (R6):
      • search_type ∈ {"title","author","isbn"}
      • title/author: partial, case-insensitive
      • isbn: exact match
      • blank/empty search returns all books
    """

    # 1) Pull all books first (small dataset assumption for course project).
    books = get_all_books()

    # 2) If user gives us an empty or whitespace-only query, return everything.
    if not search_term or not str(search_term).strip():
        return books

    # 3) Normalize inputs
    q = str(search_term).strip()
    stype = (search_type or 'title').lower()
    if stype not in {'title', 'author', 'isbn'}:
        # default to title search if the type is invalid
        stype = 'title'

    # 4) ISBN is exact match (no lowercase needed; stored format should match input)
    if stype == 'isbn':
        return [b for b in books if (b.get('isbn') or '') == q]

    # 5) Title/author partial match (case-insensitive)
    key = 'title' if stype == 'title' else 'author'
    ql = q.lower()
    return [b for b in books if ql in (b.get(key) or '').lower()]


def get_patron_status_report(patron_id: str) -> Dict:
    """
    Purpose: Summarize everything a patron cares about right now.
    Spec (R7) includes:
      • List of currently borrowed books with due dates
      • Total current late fees owed (based on today's date)
      • Count of currently borrowed books
      • Full borrowing history (past + present)
    """

    # 1) Validate the patron ID format (exactly 6 digits)
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return {'error': 'Invalid patron ID. Must be exactly 6 digits.'}

    # 2) Get the *current* borrow records for this patron (no return_date yet)
    current = get_patron_borrowed_books(patron_id)

    # 3) For each currently borrowed item, compute today's overdue days and fee
    now_date = datetime.now().date()
    current_items: List[Dict] = []
    total_fee = 0.0

    for r in current:
        # Derive days overdue from due_date (if not past due, it's zero)
        days_overdue = max(0, (now_date - r['due_date'].date()).days)

        # Same fee rules as R5, kept inline here to avoid extra DB calls
        if days_overdue > 0:
            first7 = min(days_overdue, 7) * 0.50
            rest = max(days_overdue - 7, 0) * 1.00
            fee = min(first7 + rest, 15.00)
        else:
            fee = 0.0

        total_fee += fee

        # Save a lightly formatted snapshot for the report
        current_items.append({
            'book_id': r['book_id'],
            'title': r['title'],
            'author': r['author'],
            'borrow_date': r['borrow_date'].strftime('%Y-%m-%d'),
            'due_date': r['due_date'].strftime('%Y-%m-%d'),
            'days_overdue': days_overdue,
            'late_fee': round(fee, 2),
        })

    # 4) Borrowing history: include everything (returned and still out)
    #    We JOIN to books so we can show title/author without another roundtrip.
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT br.*, b.title, b.author
        FROM borrow_records br
        JOIN books b ON br.book_id = b.id
        WHERE br.patron_id = ?
        ORDER BY datetime(br.borrow_date) DESC
    ''', (patron_id,)).fetchall()
    conn.close()

    # 5) Normalize date strings to YYYY-MM-DD for consistency in the API
    history: List[Dict] = []
    for row in rows:
        history.append({
            'book_id': row['book_id'],
            'title': row['title'],
            'author': row['author'],
            'borrow_date': row['borrow_date'][:10],               # stored as text in DB
            'due_date': row['due_date'][:10],                     # stored as text in DB
            'return_date': row['return_date'][:10] if row['return_date'] else None,
        })

    # 6) Final payload for the UI or API consumer
    return {
        'patron_id': patron_id,
        'currently_borrowed_count': len(current_items),
        'currently_borrowed': current_items,
        'total_late_fees_owed': round(total_fee, 2),
        'borrowing_history': history
    }


def pay_late_fees(patron_id: str, book_id: int, payment_gateway: PaymentGateway = None) -> Tuple[
    bool, str, Optional[str]]:
    """
    Process payment for late fees using external payment gateway.

    NEW FEATURE FOR ASSIGNMENT 3: Demonstrates need for mocking/stubbing
    This function depends on an external payment service that should be mocked in tests.

    Args:
        patron_id: 6-digit library card ID
        book_id: ID of the book with late fees
        payment_gateway: Payment gateway instance (injectable for testing)

    Returns:
        tuple: (success: bool, message: str, transaction_id: Optional[str])

    Example for you to mock:
        # In tests, mock the payment gateway:
        mock_gateway = Mock(spec=PaymentGateway)
        mock_gateway.process_payment.return_value = (True, "txn_123", "Success")
        success, msg, txn = pay_late_fees("123456", 1, mock_gateway)
    """
    # Validate patron ID
    if not patron_id or not patron_id.isdigit() or len(patron_id) != 6:
        return False, "Invalid patron ID. Must be exactly 6 digits.", None

    # Calculate late fee first
    fee_info = calculate_late_fee_for_book(patron_id, book_id)

    # Check if there's a fee to pay
    if not fee_info or 'fee_amount' not in fee_info:
        return False, "Unable to calculate late fees.", None

    fee_amount = fee_info.get('fee_amount', 0.0)

    if fee_amount <= 0:
        return False, "No late fees to pay for this book.", None

    # Get book details for payment description
    book = get_book_by_id(book_id)
    if not book:
        return False, "Book not found.", None

    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()

    # Process payment through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN THEIR TESTS!
    try:
        success, transaction_id, message = payment_gateway.process_payment(
            patron_id=patron_id,
            amount=fee_amount,
            description=f"Late fees for '{book['title']}'"
        )

        if success:
            return True, f"Payment successful! {message}", transaction_id
        else:
            return False, f"Payment failed: {message}", None

    except Exception as e:
        # Handle payment gateway errors
        return False, f"Payment processing error: {str(e)}", None


def refund_late_fee_payment(transaction_id: str, amount: float, payment_gateway: PaymentGateway = None) -> Tuple[
    bool, str]:
    """
    Refund a late fee payment (e.g., if book was returned on time but fees were charged in error).

    NEW FEATURE FOR ASSIGNMENT 3: Another function requiring mocking

    Args:
        transaction_id: Original transaction ID to refund
        amount: Amount to refund
        payment_gateway: Payment gateway instance (injectable for testing)

    Returns:
        tuple: (success: bool, message: str)
    """
    # Validate inputs
    if not transaction_id or not transaction_id.startswith("txn_"):
        return False, "Invalid transaction ID."

    if amount <= 0:
        return False, "Refund amount must be greater than 0."

    if amount > 15.00:  # Maximum late fee per book
        return False, "Refund amount exceeds maximum late fee."

    # Use provided gateway or create new one
    if payment_gateway is None:
        payment_gateway = PaymentGateway()

    # Process refund through external gateway
    # THIS IS WHAT YOU SHOULD MOCK IN YOUR TESTS!
    try:
        success, message = payment_gateway.refund_payment(transaction_id, amount)

        if success:
            return True, message
        else:
            return False, f"Refund failed: {message}"

    except Exception as e:
        return False, f"Refund processing error: {str(e)}"

# tests/test_r5_late_fee_service.py
import sys
import os
from datetime import datetime, timedelta
import pytest

# Import from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.library_service import calculate_late_fee_for_book


def _patch_book_exists(monkeypatch, book_id=1, title="Any Book"):
    """Ensure calculate_late_fee_for_book sees a real book."""
    monkeypatch.setattr(
        "services.library_service.get_book_by_id",
        lambda bid: {"id": bid, "title": title, "available_copies": 1, "total_copies": 1} if bid == book_id else None
    )


def test_no_overdue_book(monkeypatch):
    """Due date in the future => no fee, 0 overdue days."""
    _patch_book_exists(monkeypatch, book_id=1, title="Fresh Loan")

    borrow_date = datetime.now() - timedelta(days=2)
    due_date = datetime.now() + timedelta(days=5)

    # Active (unreturned) borrow list
    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda patron_id: [{
            "book_id": 1,
            "title": "Fresh Loan",
            "author": "AA",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": False
        }]
    )

    result = calculate_late_fee_for_book("012345", 1)
    assert result["fee_amount"] == 0.00
    assert result["days_overdue"] == 0
    assert result["status"].lower() == "not overdue"


def test_overdue_within_7_days(monkeypatch):
    """5 days overdue => 5 * $0.50 = $2.50."""
    _patch_book_exists(monkeypatch, book_id=2, title="Seven Window")

    borrow_date = datetime.now() - timedelta(days=18)
    due_date = datetime.now() - timedelta(days=5)

    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda patron_id: [{
            "book_id": 2,
            "title": "Seven Window",
            "author": "BB",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": True
        }]
    )

    result = calculate_late_fee_for_book("012345", 2)
    assert result["fee_amount"] == 2.50
    assert result["days_overdue"] == 5
    assert result["status"].lower() == "overdue"


def test_book_already_returned(monkeypatch):
    """
    Returned books are not in get_patron_borrowed_books (it only lists active borrows).
    Service should report no active borrow and $0 fee.
    """
    _patch_book_exists(monkeypatch, book_id=5, title="Returned One")

    monkeypatch.setattr("services.library_service.get_patron_borrowed_books", lambda patron_id: [])

    result = calculate_late_fee_for_book("012345", 5)
    assert result["fee_amount"] == 0.00
    assert result["days_overdue"] == 0
    assert "no active borrow" in result["status"].lower()


def test_overdue_more_than_7_days(monkeypatch):
    """10 days overdue => 7*$0.50 + 3*$1.00 = $6.50."""
    _patch_book_exists(monkeypatch, book_id=3, title="Ten Late")

    borrow_date = datetime.now() - timedelta(days=24)
    due_date = datetime.now() - timedelta(days=10)

    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda patron_id: [{
            "book_id": 3,
            "title": "Ten Late",
            "author": "CC",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": True
        }]
    )

    result = calculate_late_fee_for_book("012345", 3)
    assert result["fee_amount"] == 6.50
    assert result["days_overdue"] == 10
    assert result["status"].lower() == "overdue"


def test_overdue_fee_capped(monkeypatch):
    """Cap at $15. 40 days overdue would cost $36.50, but must return $15.00."""
    _patch_book_exists(monkeypatch, book_id=4, title="Very Late")

    borrow_date = datetime.now() - timedelta(days=60)
    due_date = datetime.now() - timedelta(days=40)  # explicitly 40 days overdue

    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda patron_id: [{
            "book_id": 4,
            "title": "Very Late",
            "author": "DD",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": True
        }]
    )

    result = calculate_late_fee_for_book("012345", 4)
    assert result["days_overdue"] == 40
    assert result["fee_amount"] == 15.00  # capped
    assert result["status"].lower() == "overdue"

def test_invalid_patron_id_returns_zero_and_error():
    """Patron ID must be exactly 6 digits; on invalid, return 0 fee and error status."""
    result = calculate_late_fee_for_book("ABC123", 1)
    assert result["fee_amount"] == 0.00
    assert result["days_overdue"] == 0
    assert "invalid patron id" in result["status"].lower()

def test_fee_exactly_seven_days_overdue(monkeypatch):
    """Exactly 7 days overdue => 7 * $0.50 = $3.50."""
    _patch_book_exists(monkeypatch, book_id=6, title="Boundary Book")

    borrow_date = datetime.now() - timedelta(days=21)  # due 14 days later => 7 days ago
    due_date = borrow_date + timedelta(days=14)

    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda patron_id: [{
            "book_id": 6,
            "title": "Boundary Book",
            "author": "Edge Case",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": True
        }]
    )

    result = calculate_late_fee_for_book("012345", 6)
    assert result["days_overdue"] == 7
    assert result["fee_amount"] == 3.50
    assert result["status"].lower() == "overdue"

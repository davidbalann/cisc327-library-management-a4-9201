# tests/test_r4_returns_service.py
import sys
import os
from datetime import datetime, timedelta
import pytest

# Allow imports from project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.library_service import return_book_by_patron

def test_return_book_valid_input(monkeypatch):
    # Book exists
    monkeypatch.setattr("services.library_service.get_book_by_id",
                        lambda book_id: {"id": book_id, "title": "Book X", "available_copies": 2, "total_copies": 5})

    # Patron has an active borrow of this book
    borrow_date = datetime.now() - timedelta(days=10)
    due_date = borrow_date + timedelta(days=14)
    monkeypatch.setattr("services.library_service.get_patron_borrowed_books",
                        lambda patron_id: [{
                            "book_id": 1,
                            "title": "Book X",
                            "author": "AA",
                            "borrow_date": borrow_date,
                            "due_date": due_date,
                            "is_overdue": False
                        }])

    # DB updates succeed
    monkeypatch.setattr("services.library_service.update_borrow_record_return_date", lambda *args, **kwargs: True)
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *args, **kwargs: True)

    # Fee calculation reports none
    monkeypatch.setattr("services.library_service.calculate_late_fee_for_book",
                        lambda patron_id, book_id: {"fee_amount": 0.00, "days_overdue": 0})

    success, message = return_book_by_patron("123456", 1)
    assert success is True
    assert "returned successfully" in message.lower()
    assert "no late fee" in message.lower()


def test_return_book_updates_late_fee(monkeypatch):
    """Overdue return should mention fee and days overdue."""
    # Book exists
    monkeypatch.setattr("services.library_service.get_book_by_id",
                        lambda book_id: {"id": book_id, "title": "Book Y", "available_copies": 0, "total_copies": 1})

    # Patron has active overdue borrow
    borrow_date = datetime.now() - timedelta(days=30)
    due_date = borrow_date + timedelta(days=14)
    monkeypatch.setattr("services.library_service.get_patron_borrowed_books",
                        lambda patron_id: [{
                            "book_id": 2,
                            "title": "Book Y",
                            "author": "BB",
                            "borrow_date": borrow_date,
                            "due_date": due_date,
                            "is_overdue": True
                        }])

    # DB updates succeed
    monkeypatch.setattr("services.library_service.update_borrow_record_return_date", lambda *args, **kwargs: True)
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *args, **kwargs: True)

    # Fee calculation returns a non-zero fee (e.g., 7.50 for 11 days overdue)
    monkeypatch.setattr("services.library_service.calculate_late_fee_for_book",
                        lambda patron_id, book_id: {"fee_amount": 7.50, "days_overdue": 11})

    success, message = return_book_by_patron("123456", 2)
    assert success is True
    assert "late fee" in message.lower()
    assert "7.50" in message


def test_return_book_invalid_patron_id():
    """Invalid ID should fail fast."""
    success, message = return_book_by_patron("12AB", 1)
    assert success is False
    assert "invalid patron id" in message.lower()


def test_return_book_not_borrowed(monkeypatch):
    """If the patron doesn’t have an active borrow for that book, return should fail."""
    # Book exists
    monkeypatch.setattr("services.library_service.get_book_by_id",
                        lambda book_id: {"id": book_id, "title": "Book Z", "available_copies": 1, "total_copies": 3})

    # Patron has no active borrows of this book
    monkeypatch.setattr("services.library_service.get_patron_borrowed_books", lambda patron_id: [])

    success, message = return_book_by_patron("123456", 3)
    assert success is False
    assert "no active borrow record" in message.lower()

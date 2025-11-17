import os
from datetime import datetime, timedelta

import pytest

# Make parent directory importable
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import database as db


@pytest.fixture()
def temp_db(monkeypatch, tmp_path):
    temp_path = tmp_path / "test_library.db"
    monkeypatch.setattr(db, "DATABASE", str(temp_path))
    db.init_database()
    return temp_path


def test_insert_and_get_book(temp_db):
    ok = db.insert_book("Book A", "Author A", "1111111111111", 3, 3)
    assert ok is True

    # get_all_books returns list of dicts sorted by title
    books = db.get_all_books()
    assert isinstance(books, list) and len(books) == 1
    assert books[0]["title"] == "Book A"
    assert books[0]["available_copies"] == 3

    # by id
    book_id = books[0]["id"]
    fetched = db.get_book_by_id(book_id)
    assert fetched is not None
    assert fetched["isbn"] == "1111111111111"

    # by isbn
    fetched_isbn = db.get_book_by_isbn("1111111111111")
    assert fetched_isbn is not None
    assert fetched_isbn["author"] == "Author A"


def test_insert_duplicate_isbn_returns_false(temp_db):
    assert db.insert_book("B", "Auth", "2222222222222", 1, 1) is True
    # Duplicate ISBN violates UNIQUE, function should return False
    assert db.insert_book("B2", "Auth2", "2222222222222", 2, 2) is False


def test_borrow_flow_and_counts(temp_db):
    # seed a book with 2 copies
    assert db.insert_book("C", "Auth C", "3333333333333", 2, 2) is True
    book = db.get_book_by_isbn("3333333333333")
    patron = "p123"
    now = datetime.now()
    due = now + timedelta(days=7)

    # insert borrow record and update availability
    assert db.insert_borrow_record(patron, book["id"], now, due) is True
    assert db.update_book_availability(book["id"], -1) is True

    # count and list
    assert db.get_patron_borrow_count(patron) == 1
    borrowed = db.get_patron_borrowed_books(patron)
    assert len(borrowed) == 1
    assert borrowed[0]["book_id"] == book["id"]
    assert borrowed[0]["is_overdue"] in (True, False)  # sanity

    # verify availability decreased
    updated = db.get_book_by_id(book["id"])
    assert updated["available_copies"] == 1


def test_return_updates_record_and_counts(temp_db):
    assert db.insert_book("D", "Auth D", "4444444444444", 1, 1) is True
    book = db.get_book_by_isbn("4444444444444")
    patron = "p999"
    now = datetime.now()
    due = now + timedelta(days=3)
    assert db.insert_borrow_record(patron, book["id"], now, due) is True

    # Before return: count 1
    assert db.get_patron_borrow_count(patron) == 1

    # Mark as returned and increase availability
    assert db.update_borrow_record_return_date(patron, book["id"], datetime.now()) is True
    assert db.update_book_availability(book["id"], +1) is True

    # After return: count 0 and no current borrowed books
    assert db.get_patron_borrow_count(patron) == 0
    assert db.get_patron_borrowed_books(patron) == []


def test_overdue_flag(temp_db):
    assert db.insert_book("E", "Auth E", "5555555555555", 1, 1) is True
    book = db.get_book_by_isbn("5555555555555")
    patron = "p_overdue"

    borrow_date = datetime.now() - timedelta(days=10)
    due_date = datetime.now() - timedelta(days=5)  # in the past
    assert db.insert_borrow_record(patron, book["id"], borrow_date, due_date) is True
    # Not altering availability here since it's not relevant to overdue flag

    borrowed = db.get_patron_borrowed_books(patron)
    assert len(borrowed) == 1
    assert borrowed[0]["is_overdue"] is True


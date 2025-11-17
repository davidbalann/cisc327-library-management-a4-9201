import sys
import os

# Add the parent directory of tests to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from services.library_service import (
    borrow_book_by_patron,)


#tests for R3
def test_borrow_book_valid_input(monkeypatch):

    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 2})
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda patron_id: 2)
    monkeypatch.setattr("services.library_service.insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)

    assert success is True
    assert "successfully borrowed" in message.lower()


def test_borrow_book_invalid_patron_id():

    success, message = borrow_book_by_patron("00AA", 1)

    assert success is False
    assert "invalid patron id" in message.lower()


def test_borrow_book_not_found(monkeypatch):
    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: None)

    success, message = borrow_book_by_patron("123456", 99)

    assert success is False
    assert "book not found" in message.lower()


def test_borrow_book_not_available(monkeypatch):

    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 0})

    success, message = borrow_book_by_patron("111222", 1)

    assert success is False
    assert "not available" in message.lower()


def test_borrow_book_patron_limit(monkeypatch):

    monkeypatch.setattr("services.library_service.get_book_by_id", lambda book_id: {"id": book_id, "title": "Book", "available_copies": 2})
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda patron_id: 6)

    success, message = borrow_book_by_patron("111222", 1)

    assert success is False
    assert "maximum borrowing limit" in message.lower()

def test_borrow_book_fails_when_insert_record_errors(monkeypatch):
    """If inserting the borrow record fails, return an error and do not claim success."""
    monkeypatch.setattr("services.library_service.get_book_by_id",
                        lambda book_id: {"id": book_id, "title": "DB Error Book", "available_copies": 1})
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda patron_id: 1)
    monkeypatch.setattr("services.library_service.insert_borrow_record", lambda *args, **kwargs: False)
    # Even if called, make it harmless
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *args, **kwargs: True)

    success, message = borrow_book_by_patron("123456", 1)

    assert success is False
    assert "creating borrow record" in message.lower()


def test_borrow_book_fails_when_availability_update_errors(monkeypatch):
    """If availability update fails after insert, return an error."""
    monkeypatch.setattr("services.library_service.get_book_by_id",
                        lambda book_id: {"id": book_id, "title": "Post-Insert Fail", "available_copies": 2})
    monkeypatch.setattr("services.library_service.get_patron_borrow_count", lambda patron_id: 0)
    monkeypatch.setattr("services.library_service.insert_borrow_record", lambda *args, **kwargs: True)
    monkeypatch.setattr("services.library_service.update_book_availability", lambda *args, **kwargs: False)

    success, message = borrow_book_by_patron("123456", 42)

    assert success is False
    assert "updating book availability" in message.lower()

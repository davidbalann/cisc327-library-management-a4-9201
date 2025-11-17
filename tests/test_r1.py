# tests/test_library_service_monkeypatched.py
import pytest
import sys
import os
import random
import string

# allow importing services from parent dir
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import services.library_service as libsvc
from services.library_service import add_book_to_catalog

# --- helpers ---------------------------------------------------------------

def unique_isbn():
    """Generate a 13-digit numeric ISBN not present in DB (best-effort)."""
    # Use the service's get_book_by_isbn (which will be monkeypatched)
    for _ in range(100):
        isbn = f"{random.randint(0, 10**13 - 1):013d}"
        if libsvc.get_book_by_isbn(isbn) is None:
            return isbn
    # fallback (very unlikely)
    return f"{random.randint(0, 10**13 - 1):013d}"

# ------------------------
# Global monkeypatch fixture (single place to mock DB)
# ------------------------
@pytest.fixture(autouse=True)
def mock_db(monkeypatch):
    """
    Autouse fixture that replaces libsvc.get_book_by_isbn and libsvc.insert_book
    with in-memory stubs backed by a simple dict. This gives deterministic,
    isolated behavior for all tests while preserving DB-like semantics
    (insertion, duplicate-check, retrieval).
    """
    storage = {}

    def get_book_by_isbn_stub(isbn):
        # Return a dict-like row or None
        return storage.get(isbn)

    def insert_book_stub(title, author, isbn, total_copies, available_copies):
        # Return False if duplicate, True on success
        if isbn in storage:
            return False
        storage[isbn] = {
            "title": title,
            "author": author,
            "isbn": isbn,
            "total_copies": total_copies,
            "available_copies": available_copies,
        }
        return True

    # Patch the functions on the module where add_book_to_catalog will call them
    monkeypatch.setattr(libsvc, "get_book_by_isbn", get_book_by_isbn_stub)
    monkeypatch.setattr(libsvc, "insert_book", insert_book_stub)

    yield
    # teardown: clear storage (not strictly necessary due to fixture scope)
    storage.clear()

# ------------------------
# Tests (kept structure & intent)
# ------------------------

def test_add_book_valid_input():
    """Happy path: valid fields create a real DB row."""
    isbn = unique_isbn()
    success, message = add_book_to_catalog("Test Book", "Test Author", isbn, 5)
    assert success is True
    assert "successfully added" in message.lower()

    row = libsvc.get_book_by_isbn(isbn)
    assert row is not None


def test_add_book_missing_title():
    """Title is required."""
    isbn = unique_isbn()
    success, message = add_book_to_catalog("", "Author", isbn, 1)
    assert success is False
    assert "title is required" in message.lower()


def test_add_book_author_required():
    """Author is required."""
    isbn = unique_isbn()
    success, message = add_book_to_catalog("Some Title", "   ", isbn, 1)
    assert success is False
    assert "author is required" in message.lower()


def test_add_book_invalid_isbn_length():
    """ISBN must be exactly 13 digits (implementation checks length)."""
    success, message = add_book_to_catalog("T", "A", "123456789", 1)
    assert success is False
    assert "exactly 13" in message.lower()


def test_add_book_invalid_total_copies_nonpositive():
    """Total copies must be a positive integer (zero should fail)."""
    isbn = unique_isbn()
    success, message = add_book_to_catalog("T", "A", isbn, -1)
    assert success is False
    assert "positive integer" in message.lower()


def test_add_book_duplicate_isbn():
    """Duplicate ISBN must be rejected. Set up real row first, then call service."""
    isbn = unique_isbn()
    ok = libsvc.insert_book("Seed Title", "Seed Author", isbn, 1, 1)
    assert ok is True

    success, message = add_book_to_catalog("New Title", "New Author", isbn, 2)
    assert success is False
    assert "already exists" in message.lower()


def test_add_book_title_too_long():
    """Title > 200 chars should be rejected."""
    isbn = unique_isbn()
    long_title = "A" * 201  # 201 chars
    success, message = add_book_to_catalog(long_title, "Author", isbn, 1)
    assert success is False
    assert "less than 200" in message.lower()


def test_add_book_author_too_long():
    """Author > 100 chars should be rejected."""
    isbn = unique_isbn()
    long_author = "B" * 101  # 101 chars
    success, message = add_book_to_catalog("Some Title", long_author, isbn, 1)
    assert success is False
    assert "less than 100" in message.lower()

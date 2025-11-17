# tests/test_r6_search_service.py
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from services.library_service import search_books_in_catalog


def _patch_catalog(monkeypatch, books):
    """Monkeypatch the service to return a controlled catalog."""
    monkeypatch.setattr("services.library_service.get_all_books", lambda: books)


def test_search_by_title_partial_case_insensitive(monkeypatch):
    fake_catalog = [
        {"id": 1, "title": "The Great Gatsby", "author": "F. Scott Fitzgerald",
         "isbn": "9780743273565", "total_copies": 3, "available_copies": 2},
        {"id": 2, "title": "GREAT Expectations", "author": "Charles Dickens",
         "isbn": "9780141439563", "total_copies": 2, "available_copies": 1},
        {"id": 3, "title": "To Kill a Mockingbird", "author": "Harper Lee",
         "isbn": "9780061120084", "total_copies": 2, "available_copies": 2},
    ]
    _patch_catalog(monkeypatch, fake_catalog)

    results = search_books_in_catalog("great", "title")
    assert len(results) == 2
    assert all("great" in b["title"].lower() for b in results)


def test_search_by_author_partial_case_insensitive(monkeypatch):
    fake_catalog = [
        {"id": 10, "title": "Pride and Prejudice", "author": "Jane Austen",
         "isbn": "1111111111111", "total_copies": 4, "available_copies": 2},
        {"id": 11, "title": "Emma", "author": "Austen & Co.",
         "isbn": "2222222222222", "total_copies": 2, "available_copies": 2},
        {"id": 12, "title": "The Hobbit", "author": "J.R.R. Tolkien",
         "isbn": "3333333333333", "total_copies": 1, "available_copies": 0},
    ]
    _patch_catalog(monkeypatch, fake_catalog)

    results = search_books_in_catalog("aUsTeN", "author")
    assert len(results) == 2
    assert all("austen" in b["author"].lower() for b in results)


def test_search_by_isbn_exact_match(monkeypatch):
    fake_catalog = [
        {"id": 20, "title": "Book One", "author": "A",
         "isbn": "0000000000000", "total_copies": 4, "available_copies": 2},
        {"id": 21, "title": "Book Two", "author": "B",
         "isbn": "1234567890123", "total_copies": 2, "available_copies": 2},
    ]
    _patch_catalog(monkeypatch, fake_catalog)

    results = search_books_in_catalog("1234567890123", "isbn")
    assert len(results) == 1
    assert results[0]["isbn"] == "1234567890123"


def test_search_by_isbn_no_partial_match(monkeypatch):
    fake_catalog = [
        {"id": 30, "title": "Any", "author": "Any",
         "isbn": "9876543210987", "total_copies": 1, "available_copies": 1},
    ]
    _patch_catalog(monkeypatch, fake_catalog)

    # Partial should not match for ISBN searches
    results = search_books_in_catalog("9876543", "isbn")
    assert results == []


def test_search_no_results(monkeypatch):
    fake_catalog = [
        {"id": 40, "title": "Alpha", "author": "X",
         "isbn": "4444444444444", "total_copies": 2, "available_copies": 2},
        {"id": 41, "title": "Beta", "author": "Y",
         "isbn": "5555555555555", "total_copies": 2, "available_copies": 2},
    ]
    _patch_catalog(monkeypatch, fake_catalog)

    results = search_books_in_catalog("nonexistent", "title")
    assert results == []


def test_blank_query_returns_all(monkeypatch):
    fake_catalog = [
        {"id": 50, "title": "One", "author": "A", "isbn": "1010101010101",
         "total_copies": 1, "available_copies": 1},
        {"id": 51, "title": "Two", "author": "B", "isbn": "2020202020202",
         "total_copies": 1, "available_copies": 1},
    ]
    _patch_catalog(monkeypatch, fake_catalog)

    results = search_books_in_catalog("   ", "title")
    assert results == fake_catalog


def test_invalid_search_type_defaults_to_title(monkeypatch):
    fake_catalog = [
        {"id": 60, "title": "Book Two", "author": "Z",
         "isbn": "3030303030303", "total_copies": 1, "available_copies": 1},
        {"id": 61, "title": "Another Two", "author": "Z2",
         "isbn": "4040404040404", "total_copies": 1, "available_copies": 0},
        {"id": 62, "title": "Different", "author": "Y",
         "isbn": "5050505050505", "total_copies": 1, "available_copies": 1},
    ]
    _patch_catalog(monkeypatch, fake_catalog)

    # 'publisher' is invalid → default to title search
    results = search_books_in_catalog("two", "publisher")
    assert len(results) == 2
    assert all("two" in b["title"].lower() for b in results)


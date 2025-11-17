# tests/test_r7_patron_status_service.py
import os
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.library_service import get_patron_status_report  # noqa: E402


def _patch_history(monkeypatch, rows):
    """
    Monkeypatch library_service.get_db_connection() so that
    .execute(...).fetchall() returns `rows`, and .close() is a no-op.
    `rows` must be a list[dict] with keys used by the service:
      book_id, title, author, borrow_date, due_date, return_date
    """
    cursor = SimpleNamespace(fetchall=lambda: rows)
    conn = SimpleNamespace(execute=lambda *a, **k: cursor, close=lambda: None)
    monkeypatch.setattr("services.library_service.get_db_connection", lambda: conn)


def test_status_no_history(monkeypatch):
    monkeypatch.setattr("services.library_service.get_patron_borrowed_books", lambda _pid: [])
    _patch_history(monkeypatch, rows=[])

    report = get_patron_status_report("123456")

    assert report["patron_id"] == "123456"
    assert report["currently_borrowed"] == []
    assert report["borrowing_history"] == []
    assert report["currently_borrowed_count"] == 0
    assert report["total_late_fees_owed"] == 0.00


def test_status_active_loans_only(monkeypatch):
    borrow_date = datetime.now() - timedelta(days=3)
    due_date = datetime.now() + timedelta(days=11)

    # One active loan, not overdue
    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda _pid: [{
            "book_id": 101,
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": False,
        }],
    )
    _patch_history(monkeypatch, rows=[{
        "book_id": 101,
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "borrow_date": borrow_date.isoformat(),
        "due_date": due_date.isoformat(),
        "return_date": None,
    }])

    report = get_patron_status_report("654321")

    assert report["currently_borrowed_count"] == 1
    assert len(report["currently_borrowed"]) == 1
    assert report["currently_borrowed"][0]["title"] == "The Great Gatsby"
    assert report["total_late_fees_owed"] == 0.00
    assert len(report["borrowing_history"]) == 1


def test_status_overdue_generates_fees(monkeypatch):
    # 16 days overdue -> $0.50*7 + $1.00*9 = $12.50
    borrow_date = datetime.now() - timedelta(days=30)
    due_date = datetime.now() - timedelta(days=16)

    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda _pid: [{
            "book_id": 202,
            "title": "Moby Dick",
            "author": "Herman Melville",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": True,
        }],
    )
    _patch_history(monkeypatch, rows=[{
        "book_id": 202,
        "title": "Moby Dick",
        "author": "Herman Melville",
        "borrow_date": borrow_date.isoformat(),
        "due_date": due_date.isoformat(),
        "return_date": None,
    }])

    report = get_patron_status_report("111222")

    assert report["currently_borrowed_count"] == 1
    assert report["total_late_fees_owed"] == 12.50
    assert report["currently_borrowed"][0]["title"] == "Moby Dick"
    assert any(r["title"] == "Moby Dick" for r in report["borrowing_history"])


def test_status_mixed_active_and_returned(monkeypatch):
    # Active: 1 day overdue -> $0.50
    active_borrow = {
        "book_id": 303,
        "title": "Book One",
        "author": "Author A",
        "borrow_date": datetime.now() - timedelta(days=15),
        "due_date": datetime.now() - timedelta(days=1),
        "is_overdue": True,
    }
    returned_borrow = {
        "book_id": 404,
        "title": "Book Two",
        "author": "Author B",
        "borrow_date": (datetime.now() - timedelta(days=20)).isoformat(),
        "due_date": (datetime.now() - timedelta(days=6)).isoformat(),
        "return_date": (datetime.now() - timedelta(days=5)).isoformat(),
    }

    monkeypatch.setattr("services.library_service.get_patron_borrowed_books", lambda _pid: [active_borrow])
    _patch_history(monkeypatch, rows=[
        {
            "book_id": active_borrow["book_id"],
            "title": active_borrow["title"],
            "author": active_borrow["author"],
            "borrow_date": active_borrow["borrow_date"].isoformat(),
            "due_date": active_borrow["due_date"].isoformat(),
            "return_date": None,
        },
        returned_borrow,
    ])

    report = get_patron_status_report("333444")

    assert report["currently_borrowed_count"] == 1
    assert len(report["currently_borrowed"]) == 1
    assert report["currently_borrowed"][0]["title"] == "Book One"
    assert len(report["borrowing_history"]) == 2
    assert report["total_late_fees_owed"] == 0.50  # 1 day overdue


def test_status_fee_cap(monkeypatch):
    # 46 days overdue -> would be $42.50, but cap at $15.00
    borrow_date = datetime.now() - timedelta(days=60)
    due_date = datetime.now() - timedelta(days=46)

    monkeypatch.setattr(
        "services.library_service.get_patron_borrowed_books",
        lambda _pid: [{
            "book_id": 505,
            "title": "Epic Novel",
            "author": "Author X",
            "borrow_date": borrow_date,
            "due_date": due_date,
            "is_overdue": True,
        }],
    )
    _patch_history(monkeypatch, rows=[{
        "book_id": 505,
        "title": "Epic Novel",
        "author": "Author X",
        "borrow_date": borrow_date.isoformat(),
        "due_date": due_date.isoformat(),
        "return_date": None,
    }])

    report = get_patron_status_report("999888")

    assert report["currently_borrowed_count"] == 1
    assert report["currently_borrowed"][0]["title"] == "Epic Novel"
    assert report["total_late_fees_owed"] == 15.00  # capped

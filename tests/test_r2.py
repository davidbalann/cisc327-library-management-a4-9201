# tests/test_r2_catalog_routes.py
"""
R2 — Catalog UI/Route tests (refreshed wording)

Scope: verify the /catalog page renders correctly:
- 200 OK + HTML
- Table includes the expected headers
- Each row prints id/title/author/isbn
- Availability shows "X/Y Available" or "Not Available"
- Borrow form appears only when copies remain (POST, hidden book_id, 6-digit patron_id)
- Empty state message and "Add New Book" link when there are no books
"""

import os
import sys
import re
from datetime import datetime, timedelta  # kept if you later expand tests
import pytest

# Allow imports from project root (prefer pytest.ini in real projects)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402


# ---------------------------
# Test client (Flask)
# ---------------------------
@pytest.fixture
def client():
    """Lightweight Flask test client for hitting /catalog."""
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


# ---------------------------
# Helper to inject catalog data
# ---------------------------
def _inject_books(monkeypatch, books):
    """
    Swap out the data source that the /catalog handler uses.
    Prefer routes.catalog_routes.get_all_books; if unavailable, fall back to database.get_all_books.
    """
    try:
        import routes.catalog_routes as catalog_mod
        monkeypatch.setattr(catalog_mod, "get_all_books", lambda: books)
        return
    except Exception:
        pass
    import database as db
    monkeypatch.setattr(db, "get_all_books", lambda: books)


# ---------------------------
# Tests
# ---------------------------
def test_catalog_renders_headers_and_rows(monkeypatch, client):
    """Table headers are present; each row prints the core fields."""
    books = [
        {"id": 10, "title": "Alpha Tales", "author": "Writer X",
         "isbn": "5555555555555", "available_copies": 3, "total_copies": 7},
        {"id": 11, "title": "Beta Notes", "author": "Writer Y",
         "isbn": "4444444444444", "available_copies": 0, "total_copies": 4},
    ]
    _inject_books(monkeypatch, books)

    resp = client.get("/catalog")
    assert resp.status_code == 200
    assert resp.mimetype == "text/html"

    html = resp.get_data(as_text=True)

    expected_headers = ("ID", "Title", "Author", "ISBN", "Availability", "Actions")
    for h in expected_headers:
        assert f"<th>{h}</th>" in html

    for b in books:
        assert f">{b['id']}<" in html
        assert b["title"] in html
        assert b["author"] in html
        assert b["isbn"] in html

    # Availability badges/text
    assert 'class="status-available"' in html and "3/7 Available" in html
    assert 'class="status-unavailable"' in html and "Not Available" in html


def test_catalog_shows_borrow_form_when_available(monkeypatch, client):
    """If copies remain, the borrow form/button should appear with proper constraints."""
    seeded = [
        {"id": 99, "title": "Gamma Book", "author": "ZZ",
         "isbn": "3333333333333", "available_copies": 2, "total_copies": 5},
    ]
    _inject_books(monkeypatch, seeded)

    html = client.get("/catalog").get_data(as_text=True)

    assert ">Borrow<" in html
    # Hidden book_id with correct value
    assert 'type="hidden"' in html and 'name="book_id"' in html and 'value="99"' in html
    # Patron field validation
    assert 'name="patron_id"' in html
    assert 'pattern="[0-9]{6}"' in html
    assert 'maxlength="6"' in html
    assert "required" in html
    # Must POST
    assert re.search(r'<form[^>]*method="POST"', html, flags=re.IGNORECASE)


def test_catalog_hides_borrow_form_when_unavailable(monkeypatch, client):
    """When no copies remain, show 'Not Available' and omit borrow controls."""
    _inject_books(monkeypatch, [
        {"id": 15, "title": "Delta Work", "author": "YY",
         "isbn": "2222222222222", "available_copies": 0, "total_copies": 6},
    ])

    html = client.get("/catalog").get_data(as_text=True)
    assert "Not Available" in html
    assert "Borrow</button>" not in html
    assert "<form" not in html


def test_catalog_empty_state(monkeypatch, client):
    """No records: show the empty-state text and a link to add a new book."""
    _inject_books(monkeypatch, [])

    html = client.get("/catalog").get_data(as_text=True)
    assert "No books in catalog" in html
    assert "Add New Book" in html

def test_catalog_mixed_rows_only_available_have_borrow_controls(monkeypatch, client):
    """Only rows with available copies should render a Borrow form/button."""
    books = [
        {"id": 71, "title": "Avail Book", "author": "AA",
         "isbn": "1111111111111", "available_copies": 1, "total_copies": 3},
        {"id": 72, "title": "No Copies", "author": "BB",
         "isbn": "2222222222222", "available_copies": 0, "total_copies": 3},
    ]
    _inject_books(monkeypatch, books)

    html = client.get("/catalog").get_data(as_text=True)

    # Exactly one borrow button present (for the available row)
    assert len(re.findall(r'>\s*Borrow\s*<', html)) == 1
    # Hidden book_id must correspond to the available book only
    assert 'name="book_id"' in html and 'value="71"' in html
    assert 'value="72"' not in html  # no form for unavailable row
    # Unavailable row should display "Not Available"
    assert "Not Available" in html


def test_catalog_escapes_html_in_titles_and_authors(monkeypatch, client):
    """Titles/authors with special characters must be HTML-escaped in output."""
    books = [
        {"id": 81, "title": "War & Peace <Annotated>", "author": "Tom > Jerry & Co",
         "isbn": "3333333333333", "available_copies": 2, "total_copies": 2},
    ]
    _inject_books(monkeypatch, books)

    html = client.get("/catalog").get_data(as_text=True)

    # Jinja2 auto-escaping should render these entities
    assert "War &amp; Peace &lt;Annotated&gt;" in html
    assert "Tom &gt; Jerry &amp; Co" in html

    # Raw, unescaped strings should not appear
    assert "War & Peace <Annotated>" not in html
    assert "Tom > Jerry & Co" not in html
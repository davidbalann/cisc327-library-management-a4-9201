import os
import sys
import json
import pytest

# Ensure imports from project root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    with app.test_client() as c:
        yield c


# ----------------------------
# Borrowing: /borrow
# ----------------------------
def test_borrow_invalid_book_id_redirects_with_flash(client):
    resp = client.post(
        "/borrow",
        data={"patron_id": "123456", "book_id": "abc"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Invalid book ID" in html


def test_borrow_calls_service_and_redirects(monkeypatch, client):
    # Patch the function as imported in the route module
    monkeypatch.setattr(
        "routes.borrowing_routes.borrow_book_by_patron",
        lambda patron_id, book_id: (True, "Borrowed OK"),
    )

    resp = client.post(
        "/borrow",
        data={"patron_id": "123456", "book_id": 42},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Borrowed OK" in html  # flashed message appears on catalog page


# ----------------------------
# Returning: /return
# ----------------------------
def test_return_get_renders_form(client):
    resp = client.get("/return")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Return Book" in html


def test_return_invalid_book_id_stays_on_page_with_flash(client):
    resp = client.post(
        "/return",
        data={"patron_id": "123456", "book_id": "xyz"},
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Invalid book ID" in html


def test_return_success_flashes_success(monkeypatch, client):
    monkeypatch.setattr(
        "routes.borrowing_routes.return_book_by_patron",
        lambda patron_id, book_id: (True, "Returned OK"),
    )
    resp = client.post(
        "/return",
        data={"patron_id": "123456", "book_id": 7},
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Returned OK" in html


def test_return_failure_flashes_error(monkeypatch, client):
    monkeypatch.setattr(
        "routes.borrowing_routes.return_book_by_patron",
        lambda patron_id, book_id: (False, "Could not return"),
    )
    resp = client.post(
        "/return",
        data={"patron_id": "123456", "book_id": 7},
    )
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Could not return" in html


# ----------------------------
# Search (HTML): /search
# ----------------------------
def test_search_without_query_renders_page(client):
    resp = client.get("/search")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Search" in html  # page renders without results


def test_search_with_query_calls_service_and_renders(monkeypatch, client):
    monkeypatch.setattr(
        "routes.search_routes.search_books_in_catalog",
        lambda term, typ: [
            {"id": 1, "title": "T1", "author": "A1", "isbn": "111", "available_copies": 1, "total_copies": 1}
        ],
    )
    resp = client.get("/search?q=python&type=title")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "T1" in html


def test_search_with_query_no_results_flashes(monkeypatch, client):
    monkeypatch.setattr(
        "routes.search_routes.search_books_in_catalog", lambda term, typ: []
    )
    resp = client.get("/search?q=none&type=title")
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert "Search functionality is not yet implemented" in html


# ----------------------------
# API: /api/search and /api/late_fee
# ----------------------------
def test_api_search_requires_query(client):
    resp = client.get("/api/search")
    assert resp.status_code == 400
    payload = json.loads(resp.get_data(as_text=True))
    assert payload.get("error")


def test_api_search_returns_results(monkeypatch, client):
    monkeypatch.setattr(
        "routes.api_routes.search_books_in_catalog",
        lambda term, typ: [
            {"id": 5, "title": "Alpha", "author": "Anon", "isbn": "123", "available_copies": 1, "total_copies": 1}
        ],
    )
    resp = client.get("/api/search?q=alpha&type=title")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["count"] == 1
    assert data["results"][0]["title"] == "Alpha"


def test_api_late_fee_not_implemented_returns_501(monkeypatch, client):
    monkeypatch.setattr(
        "routes.api_routes.calculate_late_fee_for_book",
        lambda patron_id, book_id: {"status": "not implemented"},
    )
    resp = client.get("/api/late_fee/123456/9")
    assert resp.status_code == 501


def test_api_late_fee_success_returns_200(monkeypatch, client):
    monkeypatch.setattr(
        "routes.api_routes.calculate_late_fee_for_book",
        lambda patron_id, book_id: {"status": "ok", "fee_amount": 0.0},
    )
    resp = client.get("/api/late_fee/123456/9")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"


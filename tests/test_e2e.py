# tests/test_e2e.py

import os
import signal
import subprocess
import time
import requests

import pytest
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://127.0.0.1:5000"  # change if your app runs on another port

headless_bool = False

# ---------- Fixtures ----------
def wait_for_server(url, timeout=10):
    start = time.time()
    while time.time() - start < timeout:
        try:
            requests.get(url)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("Flask server did not start in time")


@pytest.fixture(scope="session")
def flask_server():
    """
    Start the Flask app in a separate process for the duration of the test session.
    Assumes `app.py` runs the server when executed directly.
    """
    env = os.environ.copy()
    env["FLASK_ENV"] = "testing"

    # Start the app: adjust command if you use `flask run` or a different entrypoint
    proc = subprocess.Popen(
        ["python", "app.py"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    wait_for_server(BASE_URL)



    yield

    # Tear down
    if proc.poll() is None:
        if os.name == "nt":
            proc.terminate()
        else:
            os.kill(proc.pid, signal.SIGTERM)
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture
def page(flask_server):
    """
    Launch a Chromium browser for each test.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless_bool)  # set False while debugging
        page = browser.new_page()
        yield page
        browser.close()


# ---------- Helper ----------

def add_test_book(page, title, author, isbn=None, total_copies="3"):
    """
    Reusable helper to add a book via the UI.
    """
    page.goto(f"{BASE_URL}/add_book")

    # Generate unique 13-digit ISBN if not provided
    if isbn is None:
        ts = int(time.time() * 1000) % 1000000000000  # 12 digits
        suffix = (abs(hash(title)) % 9) + 1          # 1..9 for 13th digit
        isbn = f"{ts:012d}{suffix}"

    page.fill('input[name="title"]', title)
    page.fill('input[name="author"]', author)
    page.fill('input[name="isbn"]', isbn)
    page.fill('input[name="total_copies"]', str(total_copies))

    page.click('button[type="submit"]')
    # tiny wait to let redirect/render finish
    page.wait_for_timeout(300)


# ---------- Test 1: Add + Borrow flow ----------

def test_add_and_borrow_book_flow(page):
    """
    i.   Add a new book to the catalog
    ii.  Verify it appears in the catalog
    iii. Navigate to borrow page
    iv.  Borrow the book using a patron ID
    v.   Verify a borrow confirmation message appears
    """
    test_title = "E2E Test Book"
    test_author = "E2E Author"
    patron_id = "123456"

    # Step i: add book
    add_test_book(page, test_title, test_author)

    # Step ii: verify in catalog
    page.goto(f"{BASE_URL}/catalog")
    # Ensure catalog page and table are rendered
    expect(page.locator("h2")).to_contain_text("Book Catalog")
    expect(page.locator("table")).to_be_visible()

    # Example: if catalog is a table containing the title text
    expect(page.locator("body")).to_contain_text(test_title)

    # Step iii: borrow inline from the catalog by using the first visible patron input
    # (catalog is sorted by title; '1984' has no input, our new book 'E2E...' comes next)
    patron_input = page.locator("tbody input[name='patron_id']").first
    expect(patron_input).to_be_visible()
    patron_input.fill(patron_id)
    # Click the Borrow button within the same form as the input
    patron_input.locator("xpath=ancestor::form[1]//button[contains(., 'Borrow')]").click()

    # Step iv: borrow submitted via inline form above

    # Step v: verify confirmation message
    body = page.locator("body")
    expect(body).to_contain_text("Successfully borrowed")
    expect(body).to_contain_text(test_title)


# ---------- Test 2: Search flow (example) ----------

def test_search_catalog_flow(page):
    """
    Second realistic user flow:
      1. Add a book
      2. Go to search page
      3. Search by title
      4. Verify search result shows the book
    """

    test_title = "Searchable E2E Book"
    test_author = "Search Author"

    # Reuse helper to ensure the book exists (unique ISBN to avoid collisions)
    add_test_book(page, test_title, test_author, isbn="9780000000001")

    # Step 2: go to search page
    page.goto(f"{BASE_URL}/search")

    # Step 3: fill in search form
    page.fill('input[name="q"]', test_title)
    page.click('button[type="submit"]')

    # Step 4: assert the results contain our book
    expect(page.locator("body")).to_contain_text(test_title)
    expect(page.locator("body")).to_contain_text(test_author)

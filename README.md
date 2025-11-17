# Library Management System - Flask Web Application with SQLite
[![Tests](https://img.shields.io/github/actions/workflow/status/davidbalann/cisc327-library-management-a2-9201/main.yml?branch=main&label=Tests)](https://github.com/davidbalann/cisc327-library-management-a2-9201/actions/workflows/main.yml) [![codecov](https://codecov.io/gh/davidbalann/cisc327-library-management-a3-9201/branch/main/graph/badge.svg?token=vo2w8e24Bc)](https://codecov.io/gh/davidbalann/cisc327-library-management-a3-9201)

Simplified library app used for CISC 327 Software Quality Assurance coursework. Includes a Flask web UI, SQLite persistence, and a test suite focused on business logic and routes.

## Overview

This repository contains a partial implementation of a Library Management System built with Flask and SQLite. It is intentionally scoped for testing exercises and includes blueprints, templates, and a services layer.

Provided components:

- [`requirements_specification.md`](requirements_specification.md): Requirements R1–R7
- [`app.py`](app.py): Application factory, registers blueprints
- [`routes/`](routes/): Flask blueprints
  - [`catalog_routes.py`](routes/catalog_routes.py): Catalog display and add-book form
  - [`borrowing_routes.py`](routes/borrowing_routes.py): Borrow and return endpoints
  - [`api_routes.py`](routes/api_routes.py): JSON API for search and late fees
  - [`search_routes.py`](routes/search_routes.py): Search page
- [`database.py`](database.py): SQLite helpers and schema initialization
- [`services/`](services/): Business logic
  - [`library_service.py`](services/library_service.py)
  - [`payment_service.py`](services/payment_service.py)
- [`templates/`](templates/): Jinja2 templates
- [`tests/`](tests/): Pytest suite (service and route coverage)
- [`requirements.txt`](requirements.txt): Dependencies

## Known Issues
The implemented functions may contain intentional bugs. Students should discover these through unit testing (to be covered in later assignments).

## Database Schema
**Books Table:**
- `id` (INTEGER PRIMARY KEY)
- `title` (TEXT NOT NULL)
- `author` (TEXT NOT NULL)
- `isbn` (TEXT UNIQUE NOT NULL)
- `total_copies` (INTEGER NOT NULL)
- `available_copies` (INTEGER NOT NULL)

**Borrow Records Table:**
- `id` (INTEGER PRIMARY KEY)
- `patron_id` (TEXT NOT NULL)
- `book_id` (INTEGER FOREIGN KEY)
- `borrow_date` (TEXT NOT NULL)
- `due_date` (TEXT NOT NULL)
- `return_date` (TEXT NULL)

## Setup

Python 3.10+ recommended.

1) Create and activate a virtual environment
- Windows PowerShell
  - `python -m venv venv`
  - `./venv/Scripts/Activate.ps1`

2) Install dependencies
- `pip install -U pip`
- `pip install -r requirements.txt`

## Running

- Start the app: `python app.py`
- App factory: `create_app()` in `app.py` registers all blueprints under `routes/`.

## Testing

- Run all tests: `pytest -q`
- Routes-only coverage: `pytest --cov=routes --cov-report=term-missing -q`
- Full coverage (HTML + XML): `pytest --cov=. --cov-report=html --cov-report=xml -q`
- Open HTML coverage report: `./htmlcov/index.html`

New tests were added to increase coverage for the routes package (see `tests/test_routes.py`). These tests stub service-layer calls at the route modules to validate HTTP status codes, redirects, flashed messages, and JSON payloads.

## Assignment Instructions
See [`student_instructions.md`](student_instructions.md) for complete assignment details.

**Resources for students:**

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Test Driven Development](https://www.datacamp.com/tutorial/test-driven-development-in-python)
- [Pytest framework](https://realpython.com/pytest-python-testing/)
- [Python Blueprint](https://flask.palletsprojects.com/en/stable/blueprints)

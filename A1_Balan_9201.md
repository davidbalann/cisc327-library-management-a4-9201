# Library Management System Assignment 1
**David Balan**

## Part 1
 - Working in *Pycharm*, I cloned the repository to local directories
 - A virtual enviroment was made and the dependencies were installed
 - Application was ran
 - The banner was changed from *Your Name* to my name: David Balan
 - The application was shut off and re-ran
## Part 2: Implementation Status

| Requirement ID | Requirement               | Implementation Status (Complete/Partial)                                                                                                                                                                                                                                                                                                                                                         | What Is Missing                                                                                                                                                                                    |
|----------------|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| R1             | Add Book To Catalog       | Title (required, max 200 characters): PASS<br/>Author (required, max 100 characters): PASS<br/>ISBN (required, exactly 13 digits): PASS<br/>Total copies (required, positive integer): PASS<br/>The system shall display success/error messages and redirect to the catalog view after successful addition: PASS <br/>Implementation: Complete                                                   |                                                                                                                                                                                                    |
| R2             | Book Catalog Display      | Book ID, Title, Author, ISBN: PASS<br/>Available copies / Total copies: PASS <br/>Actions (Borrow button for available books): PASS<br/>Implementation: Complete                                                                                                                                                                                                                                 |                                                                                                                                                                                                    |
| R3             | Book Borrowing Interface  | Accepts patron ID and book ID as the form parameters: PASS<br/>Validates patron ID (6-digit format): PASS<br/> Checks book availability and patron borrowing limits (max 5 books): PASS<br/>Creates borrowing record and updates available copies: PASS<br/>Displays appropriate success/error messages: PASS<br/>Implementation: Complete                                                       |                                                                                                                                                                                                    |
| R4             | Book Return Processing    | Accepts patron ID and book ID as form parameters: PASS<br/>Verifies the book was borrowed by the patron: FAIL<br/>Updates available copies and records return date: FAIL<br/>Calculates and displays any late fees owed: FAIL<br/> Implementation: Partial                                                                                                                                       | - Verifies the book was borrowed by the patron<br/> - Updates available copies and records return date <br/> - Calculates and displays any late fees owed                                          |
| R5             | Late Fee Calculation API  | Calculates late fees for overdue books based on: <br/>    Books due 14 days after borrowing:Calculated At Borrowing:PASS <br/>    \$0.50/day for first 7 days overdue: FAIL <br/>    $1.00/day for each additional day after 7 days: FAIL <br/>Maximum \$15.00 per book: FAIL <br/>Returns JSON response with fee amount and days overdue: FAIL <br/> Implementation: Partial                    | -     \$0.50/day for first 7 days overdue<br/> - $1.00/day for each additional day after 7 days<br/> - Maximum \$15.00 per book<br/> - Returns JSON response with fee amount and days overdue<br/> |
| R6             | Book Search Functionality | The system shall provide search functionality with the following parameters:<br/> q: search term <br/> type: search type (title, author, isbn)<br/>Support partial matching for title/author (case-insensitive): FAIL<br/>Support exact matching for ISBN: FAIL<br/>Return results in same format as catalog display: FAIL <br/> Implementation: Partial                                         | - Support partial matching for title/author (case-insensitive)<br/> - Support exact matching for ISBN<br/> - Return results in same format as catalog display                                      |
| R7             | Patron Status Report      | The system shall display patron status for a particular patron that includes the following:<br/> Currently borrowed books with due dates: FAIL<br/> Total late fees owed: FAIL<br/> Number of books currently borrowed: FAIL<br/> Borrowing history: FAIL<br/> There should be a menu option created for showing the patron status in the main interface: FAIL<br/> Implementation: Non-Existant | - All Implementation                                                                                                                                                                               |

## Part 3: Writing Unit Tests

### R1 — Add Book To Catalog
`pytest -q -vv tests/test_r1.py`

| Test case                                     | Result (expected) |
|-----------------------------------------------|-------------------|
| test_add_book_valid_input                     | PASSED            |
| test_add_book_missing_title                   | PASSED            |
| test_add_book_author_required                 | PASSED            |
| test_add_book_invalid_isbn_length             | PASSED            |
| test_add_book_invalid_total_copies_nonpositive| PASSED            |
| test_add_book_duplicate_isbn                  | PASSED            |

**R1: Passed**

---

### R2 — Book Catalog Display
`pytest -q -vv tests/test_r2.py`

| Test case                                       | Result (expected) |
|-------------------------------------------------|-------------------|
| test_catalog_renders_headers_and_rows           | PASSED            |
| test_catalog_shows_borrow_form_when_available   | PASSED            |
| test_catalog_hides_borrow_form_when_unavailable | PASSED            |
| test_catalog_empty_state                        | PASSED            |

**R2: Passed**

---

### R3 — Book Borrowing Interface
`pytest -q -vv tests/test_r3.py`

| Test case                           | Result (expected) |
|-------------------------------------|-------------------|
| test_borrow_book_valid_input        | PASSED            |
| test_borrow_book_invalid_patron_id  | PASSED            |
| test_borrow_book_not_found          | PASSED            |
| test_borrow_book_not_available      | PASSED            |
| test_borrow_book_patron_limit       | PASSED            |

**R3: Passed**

---

### R4 — Book Return Processing
`pytest -q -vv tests/test_r4.py`

| Test case                          | Result (expected)          |
|------------------------------------|----------------------------|
| test_return_book_valid_input       | XFAIL (R4 not implemented) |
| test_return_book_updates_late_fee  | XFAIL (R4 not implemented) |
| test_return_book_invalid_patron_id | XFAIL (R4 not implemented) |
| test_return_book_not_borrowed      | XFAIL (R4 not implemented) |

**R4: Pending (XFAIL — not implemented)**

---

### R5 — Late Fee Calculation API
`pytest -q -vv tests/test_r5.py`

| Test case                     | Result (expected)          |
|------------------------------|----------------------------|
| test_no_overdue_book         | XFAIL (R5 not implemented) |
| test_overdue_within_7_days   | XFAIL (R5 not implemented) |
| test_book_already_returned   | XFAIL (R5 not implemented) |
| test_overdue_more_than_7_days| XFAIL (R5 not implemented) |
| test_overdue_fee_capped      | XFAIL (R5 not implemented) |

**R5: Pending (XFAIL — not implemented)**

---

### R6 — Book Search Functionality
`pytest -q -vv tests/test_r6.py`

| Test case                                   | Result (expected)          |
|---------------------------------------------|----------------------------|
| test_search_by_title_partial_case_insensitive  | XFAIL (R6 not implemented) |
| test_search_by_author_partial_case_insensitive | XFAIL (R6 not implemented) |
| test_search_by_isbn_exact_match               | XFAIL (R6 not implemented) |
| test_search_by_isbn_no_partial_match          | XFAIL (R6 not implemented) |
| test_search_no_results                        | XFAIL (R6 not implemented) |

**R6: Pending (XFAIL — not implemented)**

---

### R7 — Patron Status Report
`pytest -q -vv tests/test_r7.py`

| Test case                          | Result (expected)          |
|------------------------------------|----------------------------|
| test_status_no_history             | XFAIL (R7 not implemented) |
| test_status_active_loans_only      | XFAIL (R7 not implemented) |
| test_status_overdue_generates_fees | XFAIL (R7 not implemented) |
| test_status_mixed_active_and_returned | XFAIL (R7 not implemented) |
| test_status_fee_cap                | XFAIL (R7 not implemented) |

**R7: Pending (XFAIL — not implemented)**





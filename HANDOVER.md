# ClearLedger Track A — Handover

## Candidate

Sankar Ayudham

## Track

Track A — Product Engineering

## Summary

Repaired the ClearLedger invoice application while preserving the existing fixture records and public API routes.

The work focused on correctness, import reliability, payment matching, reporting, browser workflows, regression testing, and verification.

## Fixes Completed

### 1. Payment matching

Fixed payment matching so that a payment is matched using the required invoice identity:

`(customer_id, invoice_number)`

Previously, matching could use payment amount first. This could attach a payment to the wrong invoice when multiple invoices had the same amount.

The corrected behavior only matches a payment when both the customer ID and invoice number identify the invoice.

### 2. Import row isolation

Fixed CSV importing so that an invalid data row is rejected individually while other valid rows continue to import.

Previously, normalization happened before the per-row error handling, so one invalid row could prevent the remaining valid rows from being processed.

The corrected behavior processes and validates each row independently.

### 3. Duplicate invoice handling

Implemented the required invoice identity and duplicate behavior.

Invoice identity is:

`(customer_id, invoice_number)`

Behavior:

- Identical duplicate invoice → skipped.
- Same invoice identity with different amount or due date → rejected.
- Existing invoice records are preserved.

### 4. Open / paid invoice filtering

Fixed the invoice status filter so that:

- `all` returns all invoices.
- `open` returns only open invoices.
- `paid` returns only paid invoices.

Previously, the filtering logic mapped the requested status incorrectly.

### 5. Browser import error handling

Fixed the browser import workflow so HTTP errors are no longer reported as successful imports.

Previously, the browser called the import API but did not check whether the HTTP response was successful. A server-side HTTP 400 could therefore still produce the message:

`Import complete. Your records are ready.`

The browser now checks the HTTP response and displays the actual error.

Partial imports also display:

- imported count
- skipped count
- rejected count
- rejected line number
- rejection reason

### 6. CSV money precision

Fixed CSV export so monetary values are formatted to two decimal places without truncating floating-point values.

Previously, export used truncation logic that could convert a value such as `19.99` to `19.98`.

The export now formats the numeric value directly to two decimal places.

Example verified with the fixture:

Before:

`19.98,10,9.98`

After:

`19.99,10,9.99`

## Useful Improvement

1.Improved browser import feedback.

The import workflow now distinguishes between successful, partial, and failed imports.

For partial imports, the UI shows:

- imported count
- skipped count
- rejected count
- rejected CSV line number
- rejection reason

For failed requests, the browser now displays the actual API error instead of incorrectly presenting the import as successful.

This makes import results clearer to the user and reduces the chance of assuming that records were imported when the request actually failed.

2.Improved the browser import form so that after a successful or partial import, the selected CSV file is automatically cleared from the file input.

This reduces accidental re-submission of the same CSV and leaves the import form ready for the next import.

### Verification

Imported `samples/invoices-new.csv` through the browser.

Result:

- 2 invoices imported
- import result displayed correctly
- selected CSV filename was cleared from the file input
- invoice register refreshed

The official fixture was then restored with:

`python restore_fixture.py --replace`

## Verification

### Automated tests

Command:

`python -m unittest discover -s tests -v`

Final result:

`Ran 12 tests in 0.888s`

`OK`

All 12 tests passed.

### Payment matching reproduction

Created invoices with the same amount but different customer/invoice identities and verified that the payment attaches using customer ID and invoice number rather than amount alone.

Before the fix, the matching logic could select an invoice based only on payment amount.

After the fix, the payment is attached to the invoice identified by the matching customer ID and invoice number.

A dedicated regression test was added:

`test_payment_matches_customer_and_invoice_not_amount_only`

### Invalid-row reproduction

Tested an invoice CSV containing two valid rows and one invalid negative-amount row.

Result:

`2 imported, 0 skipped, and 1 rejected.`

`Line 3: amount must be a positive decimal with at most two decimal places`

The valid rows were imported successfully while only the invalid row was rejected.

Regression test:

`test_bad_invoice_row_does_not_block_good_rows`

### Duplicate invoice reproduction

Tested an identical duplicate invoice.

The first invoice was imported and the duplicate was skipped.

Regression test:

`test_duplicate_invoice_is_skipped`

Also tested the same invoice identity with different details.

The conflicting invoice was rejected and the original record was preserved.

Regression test:

`test_changed_duplicate_invoice_is_rejected`

### Status filter reproduction

Tested the invoice register using:

- All invoices
- Open invoices
- Paid invoices

Verified that each filtered result contains only invoices with the requested status.

Regression test:

`test_status_filters_separate_open_and_paid`

### Browser import error reproduction

Submitted an invalid CSV header through the browser.

Before the fix, the browser could report the import as successful even when the API returned an error.

After the fix, the browser correctly displayed:

`Import failed: Expected CSV header: customer_id,invoice_number,amount,due_date`

The browser therefore no longer reports a failed import as successful.

### Partial import browser reproduction

Submitted a CSV containing valid and invalid invoice rows through the browser.

The browser correctly displayed:

`Import finished with 2 imported, 0 skipped, and 1 rejected.`

and:

`Line 3: amount must be a positive decimal with at most two decimal places`

### CSV export reproduction

Compared the browser invoice register with the exported CSV.

For:

`NORTH / INV-300`

Browser:

`Amount: ₹19.99`

`Paid: ₹10.00`

`Balance: ₹9.99`

CSV:

`19.99,10,9.99,open`

The monetary values now agree between the browser and downloaded CSV.

Regression test:

`test_export_preserves_money_to_two_decimals`

## Regression Tests Added

The test suite covers:

- invalid-row isolation
- duplicate invoice skipping
- changed duplicate invoice rejection
- payment matching by customer and invoice
- open/paid filtering
- money precision
- CSV export
- fixture/seed behavior
- valid invoice import
- payment reference matching
- CSV export header

Final result:

`12/12 tests passing`

## Fixture Verification

The supplied assessment fixture was restored before final verification.

Expected fixture:

- 9 invoices
- 5 payments
- 7 open invoices
- Outstanding balance: INR 3698.19

The fixture records and identities were preserved during the repair work.

The public API routes were preserved:

- `GET /api/overview`
- `GET /api/invoices?status=all|open|paid`
- `GET /api/export`
- `POST /api/import?kind=invoices`
- `POST /api/import?kind=payments`

## Remaining Issues

No known issue was found that prevents the assessed Track A workflows from operating correctly.

The application remains a local synthetic-data assessment application.

No authentication, deployment, tax, FX, or production infrastructure changes were required.

## Run Commands

Start the application:

`python app.py`

Open:

`http://127.0.0.1:8787`

Run the automated tests:

`python -m unittest discover -s tests -v`

Restore the original assessment fixture if needed:

`python restore_fixture.py --replace`

## AI / Tool-Use Summary

AI assistance was used during the assessment for:

- understanding the supplied business rules
- inspecting the existing code
- identifying likely defect locations
- suggesting targeted code fixes
- designing regression tests
- interpreting test failures and verification results
- preparing the handover documentation

All code changes were run and verified locally against the supplied assessment application.

No external packages were added.

The final verification was performed locally using the supplied application, fixture data, browser workflow, and automated test suite.

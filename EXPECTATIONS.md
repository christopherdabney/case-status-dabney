# Technical Interview Exercise

## Overview

In this exercise you will work across the existing Flask backend (this repo) and the companion frontend repo `case-status-interview-fe`. The backend already exposes:

- GET /clients  (list all clients)
- PATCH /clients (upsert / import a client via `ImportCaseHelper.import_client_handler`)

Automated tests cover creation and update logic for client imports. Your goal is to safely extend usage without breaking tests.

## Required Tasks

1. Frontend Consumption

    - Fetch and render the client list from GET /clients on initial load.
    - Display core fields: id, first_name, last_name, email, cell_phone, integration_id.
    - Implement polling OR a manual refresh button (your choice) minimally.

2. Client Import / Update Form
    - Build a form that allows entering (at least): first_name, last_name, email, cell_phone, integration_id, birth_date (optional).
    - On submit, issue a PATCH /clients request with JSON shaped similarly to what `import_client_handler` expects:

    ```json
        {
        "firm_id": 1,
        "field_names": {
            "first_name": "...",
            "last_name": "...",
            "email": "...",
            "phone_numbers": ["..."],
            "integration_id": "...",
            "birth_date": "...",
            "ssn": "...optional..."
        },
        "integration_type": "CSV_IMPORT"
        }
    ```

    - After a successful response, optimistically update the local client list (do not wait for a refetch). Reconcile with server response once it returns (e.g. replace temp row with authoritative data).

3. State & Optimistic UI
   - Show pending state (spinner / subtle indicator) while PATCH in flight.
   - Handle error rollback: if optimistic add/update fails, revert UI and show a user-friendly error.
   - Avoid full-list reload flashes—incrementally adjust state.

4. Backend Hardening (Server)
   - Add basic validation & defensive checks to PATCH /clients:
     - Reject payloads missing required keys with 400.
     - Constrain `phone_numbers` to list of strings.
     - Enforce max lengths consistent with model columns.
     - Return structured JSON errors: { "errors": [ { "field": "...", "message": "..." } ] }.
   - Add try/except to prevent unhandled exceptions leaking stack traces.
   - Ensure idempotency where possible (same payload should not create duplicates).
   - Consider adding simple rate limiting or request size guard (describe if not implemented).
   - Do NOT break existing tests (extend or add new tests if you adjust logic).

5. Tests Integrity
   - If you modify `import_client_handler`, keep current tests passing. Add new tests to cover any new validation branches you introduce.

## Stretch / Optional (Choose if Time Remains)

- Refactor `import_client_handler`:
  - Extract pure functions (e.g. derive_names, select_primary_phone, build_client_update_dict).
  - Introduce a small service class or functional pipeline that makes decision points explicit.
  - Add type hints.
  - Maintain 100% backward compatibility for existing tests.
  - Add new focused unit tests for the extracted functions.

- Improve phone parsing logic (currently stubbed).

## Non-Goals / What Not To Spend Time On

- Full authentication / authorization (you may stub a Firm).
- Complex UI styling—clarity over polish.
- Full encryption implementation for SSN (function is a stub).

## Deliverables

Provide (in PR description or separate doc):

- Short architecture / reasoning notes (1–2 paragraphs).
- Any trade-offs or assumptions.
- Follow-up improvements you would make with more time.

## Evaluation Criteria

| Area | Focus |
|------|-------|
| Correctness | Endpoints function, tests pass, form works |
| Code Quality | Clear decomposition, naming, minimal duplication |
| Robustness | Validation, error handling, edge cases |
| UX State Handling | Optimistic updates, error rollback |
| Refactor Quality (if done) | Smaller testable units, readability |
| Communication | Clarity of assumptions & next steps |

### Running Locally

1. Create / activate env:
   uv venv .venv
   source .venv/bin/activate
2. Install deps:
   uv pip install -r requirements.txt
3. Initialize DB (first run):

   ```python
   >>> from app import db
   >>> db.create_all()
   >>> exit()
   ```

4. Start server:

   `flask --app app run --reload`
5. Run tests:

   `python -m pytest -q`

   or

   `python test_import_client_handler.py`

### Example PATCH Payload

```json
    {
    "firm_id": 1,
    "field_names": {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada@example.com",
        "phone_numbers": ["+15551234567"],
        "integration_id": "ext-123",
        "birth_date": "1815-12-10"
    },
    "integration_type": "CSV_IMPORT"
    }
```

### Tips

- Keep refactor commits isolated; verify tests after each small step.
- For optimistic UI, consider generating a temporary negative id or using a UUID to reconcile.
- Log (or surface) server validation messages clearly in the form.

Good luck!

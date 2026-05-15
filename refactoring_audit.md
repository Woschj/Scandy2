# Codebase Audit & Refactoring Proposals

## 1. Identify Largest Files
The largest Python files in the repository are:
1. `app/plugins/tickets/routes.py` (1777 lines)
2. `app/utils/unified_backup_manager.py` (1424 lines)
3. `app/utils/email_utils.py` (1289 lines)
4. `app/plugins/workers/routes.py` (1229 lines)

## 2. Audit Findings & Proposals

### File 1: `app/plugins/tickets/routes.py`
- **Issue:** Monolithic God-File mixing internal API endpoints, public endpoints, and HTML views.
- **Complex Functions:** `update_details` (220 lines), `_handle_auftrag_creation` (166 lines), `export_ticket` (141 lines), `create` (137 lines).
- **Proposals:**
  - Extract public/external routes (`public_create_order`, `external_create_order`, `_handle_auftrag_creation`) into a new `public_routes.py` submodule.
  - Extract API endpoint routes (e.g., `update_status`, `update_assignment`) into `api_routes.py`.
  - Move complex database updates/business logic from `update_details` and `create` to `TicketService` or helper utilities.

### File 2: `app/utils/unified_backup_manager.py`
- **Issue:** Large centralized backup utility handling multiple responsibilities (JSON import/export, MongoDB binary backup, specific module scoped backups).
- **Complex Functions:** `import_json_backup_scoped_report` (185 lines), `import_json_backup_scoped` (172 lines).
- **Proposals:**
  - Separate import/export logic from backup creation logic.
  - Break down scoped JSON import functions into smaller, modular helper functions per scope.
  - Extract MongoDB native backup execution logic into its own module to separate concern from generic JSON operations.

### File 3: `app/utils/email_utils.py`
- **Issue:** Large utility file with HTML templates inline or extensive data structure mapping and configuration retrieval.
- **Complex Functions:** `send_auftrag_confirmation_email` (196 lines), `send_password_reset_mail` (115 lines).
- **Proposals:**
  - Ensure templates use `render_template` strictly instead of raw strings to reduce size.
  - Delegate email generation details (subject lines, recipient finding) to dedicated email builder classes or `EmailService`.
  - Extract diagnostic/test endpoints (e.g., `diagnose_smtp_connection`) to a separate admin or diagnostic module.

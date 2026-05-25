1. **app/plugins/tickets/routes.py:** (1565 lines)
   - Extract API logic, public handlers, and view logic into separate modules (`api_routes.py`, `view_routes.py`, `public_routes.py`) similar to how `debug_routes.py` is extracted.
   - Refactor massive route handlers like `create`, `update_details`, `export_ticket` by moving their business logic to `TicketService`.
   - Remove redundant checks or consolidate with utility functions if possible.

2. **app/utils/unified_backup_manager.py:** (1423 lines)
   - Separate `UnifiedBackupManager` into logically smaller managers or separate out the scoped JSON export/import and standard zip backup functionalities into distinct components/modules (e.g., `backup_importer.py`, `backup_exporter.py`).
   - Reduce complexity in large nested methods like `_create_final_backup` by breaking out internal helper methods to class level.

3. **app/plugins/workers/routes.py:** (1228 lines)
   - Isolate the timesheet module logic (e.g. `timesheet_list`, `timesheet_create`, `timesheet_edit`, etc.) into a dedicated `timesheet_routes.py` module.
   - Move administrative/migration scripts (`admin_migrate_timesheets`, `admin_migrate_all_dates`) into a separate `admin_routes.py` or `scripts.py` under the plugin, or remove them if no longer needed.
   - Shift business logic involving worker lending counts into a service layer (e.g., `WorkerService`).

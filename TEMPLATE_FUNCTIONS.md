# Scandy Template Functions (Restructured)

This file documents the functions and purposes of all templates in the Scandy application, organized according to the new logical layout.

## Core Templates (`app/templates/`)

- `base.html`: The main base layout for the application, including the sidebar and navbar.

## Feature-Specific Directories

### Main and Index (`app/templates/index/`, `app/templates/main/`)
- `index/public.html`: Landing page for non-authenticated users.
- `index/normal.html`: Main staff homepage with system statistics.
- `index/teilnehmer.html`: Participant-specific homepage.
- `main/about.html`: Information about Scandy and user manual.

### Setup (`app/templates/setup/`)
- `setup/index.html`: Initial setup entry page.
- `setup/admin.html`: Create the first administrator account.
- `setup/settings.html`: Configure core system labels and icons.
- `setup/optional.html`: Configure initial categories, locations, and departments.

### Admin (`app/templates/admin/`)
- `admin/dashboard.html`: Central administration dashboard.
- `admin/sync.html`: (Legacy) Synchronization status for client/server mode.
- `admin/trash.html`: Current trash bin implementation.
- `admin/trash_legacy.html`: Alternative/Old trash bin implementation.
- `admin/users.html`: User management list.
- `admin/user_form.html`: Form for creating or editing users.
- `admin/system.html`: System configuration and maintenance.
- `admin/departments.html`: Department management.
- `admin/feature_settings.html`: Toggle features per department.
- `admin/email_settings.html`: SMTP and email template configuration.
- `admin/notices.html`: Manage homepage notices.

### Auth (`app/templates/auth/`)
- `auth/login.html`: Login form.
- `auth/profile.html`: User profile management.
- `auth/reset_password.html`: Request password reset.
- `auth/reset_with_token.html`: Fulfill password reset.

### Tools (`app/templates/tools/`)
- `tools/index.html`: List of tools.
- `tools/detail.html`: Detailed tool view.
- `tools/add.html`: Form to add tools.
- `tools/statistics.html`: Tool usage statistics.

### Consumables (`app/templates/consumables/`)
- `consumables/index.html`: List of consumables.
- `consumables/details.html`: Consumable details and stock.
- `consumables/add.html`: Form to add consumables.

### Workers (`app/templates/workers/`)
- `workers/index.html`: List of workers.
- `workers/details.html`: Worker details.
- `workers/timesheet.html`: Daily timesheet entry.
- `workers/timesheet_list.html`: Worker's timesheet overview.

### Tickets & Orders (`app/templates/tickets/`)
- `tickets/view.html`: List of tickets.
- `tickets/detail.html`: Ticket details and messaging.
- `tickets/create.html`: Ticket creation form.
- `tickets/public_success.html`: Success message after public ticket creation.

### QuickScan (`app/templates/quick_scan/`)
- `quick_scan/index.html`: Main QuickScan interface.

### Shared & Components (`app/templates/shared/`, `app/templates/components/`)
- `shared/base_embed.html`: Base for embedded views.
- `shared/nav_legacy.html`: (Legacy) Navbar fragment.
- `shared/list_base.html`: Base template for list views.
- `components/`: UI fragments (modals, galleries, scan steps).

### Errors (`app/templates/errors/`)
- `errors/error.html`: Generic error page.
- `errors/404.html`, `errors/500.html`, etc.: Standard HTTP error pages.

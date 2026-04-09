# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-05-15 - [Unified List Filtering Pattern]
**Learning:** Decoupled search and dropdown filters in list views often lead to inconsistent states (e.g., search term remains while dropdown filter changes but doesn't respect the search). A centralized filtering function in the base template that aggregates all active filter states (search + dropdowns) ensures a consistent "source of truth" and reduces boilerplate in child templates.
**Action:** Use a centralized `applyFilters` function in base list templates that matches dropdown IDs (e.g., `departmentFilter`) with data-attributes on items (e.g., `data-department`).

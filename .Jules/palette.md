# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-04 - [Unified List Filtering & Sorting Accessibility]
**Learning:** Client-side list views benefit greatly from a "Unified Filtering Pattern" that automatically syncs search inputs and dropdown filters. Table sorting accessibility requires not just icons, but semantic roles, keyboard listeners, and `aria-sort` updates to be meaningful to all users.
**Action:** Use the `select[id$="Filter"]` pattern for automatic filter integration and wrap sortable headers in interactive, labeled containers with focus indicators.

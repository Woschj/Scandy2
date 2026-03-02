# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-02 - [Unified List Filtering and Accessibility]
**Learning:** Centralizing list search, dropdown filtering, and accessible sorting in a shared base template (`list_base.html`) ensures a consistent UX across different modules (Tools, Consumables, Workers). By using a generic `updateTableVisibility` function that matches dropdown IDs to row data-attributes, we eliminate redundant code and prevent logic regressions in sub-pages.
**Action:** Use the unified `join` search component and generic filter logic in `list_base.html` for all tabular views in the system.

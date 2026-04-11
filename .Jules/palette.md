# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-11 - [Dynamic Table Empty States & Accessibility]
**Learning:** When adding a "No results" row to a client-side filtered table, the sorting function must be updated to exclude this row from the sortable array and ensure it remains at the bottom of the `tbody` to prevent UI glitches. Additionally, providing an `aria-live` region for result counts ensures that screen reader users are informed of dynamic list changes.
**Action:** Always verify that client-side sorting and filtering logic accounts for placeholder/empty-state rows and include an announcement for the number of results found.

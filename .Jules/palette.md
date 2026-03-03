# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-03 - [Enhanced List Interactions & Accessibility]
**Learning:** Client-side search and sorting components require explicit feedback (like a "No results" row) and clear-actions (like a "Clear" button) to feel robust. Accessibility for sortable headers is best achieved by wrapping content in a semantic `div` with `role="button"`, `tabindex="0"`, and `aria-sort` attributes.
**Action:** Incorporate empty states and keyboard-accessible sorting as a standard pattern for data-heavy list views.

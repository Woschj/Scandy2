# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-02-25 - [Table Sorting Accessibility]
**Learning:** Enhancing JavaScript-generated table headers with `role="button"`, `tabindex="0"`, and `onkeydown` handlers significantly improves keyboard accessibility. Using `aria-sort` on the parent `th` provides essential feedback to screen reader users about the current sort state.
**Action:** Always include keyboard support and ARIA sort attributes when implementing client-side table sorting.

# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-02 - [Table Sorting Accessibility]
**Learning:** Dynamic table headers used for sorting must be enhanced with `role="button"`, `tabindex="0"`, and keyboard listeners (Enter/Space) to be accessible. Screen reader feedback via `aria-sort` and descriptive `aria-label`s is crucial for an inclusive experience.
**Action:** Always wrap interactive header content in a keyboard-accessible element and provide ARIA state updates when sorting.

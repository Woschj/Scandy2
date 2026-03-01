# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-01 - [Table Row Selection for Client-side Sorting]
**Learning:** Generic `tr` selectors in client-side sorting and filtering scripts can cause functional regressions when feedback rows (like "No results found") are added to the table body. These rows are incorrectly included in sorts, appearing in random positions.
**Action:** Always use specific selectors like `.data-row` for data-related iterations to isolate metadata or feedback rows.

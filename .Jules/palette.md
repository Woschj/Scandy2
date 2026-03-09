# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-09 - [Search Reset UX Pattern]
**Learning:** Adding a dynamic 'Clear Search' button that appears only when the input is not empty significantly improves filter usability. Using `el.dispatchEvent(new Event('input'))` ensures that the filtering logic (which usually listens to `input`) is correctly triggered when the field is cleared programmatically.
**Action:** Implement 'Clear Search' buttons for all primary search filters using the `join` component to maintain visual alignment.

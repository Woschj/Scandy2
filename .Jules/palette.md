# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-03-05 - [Table Sorting Accessibility]
**Learning:** Table headers that trigger client-side sorting need more than just a click listener to be accessible. They require `role="button"`, `tabindex="0"`, a descriptive `aria-label`, and `aria-sort` attributes. Visual focus indicators (like rings) are also essential for keyboard users to know which header is active.
**Action:** When implementing interactive table headers, ensure they are focusable and communicate their state to assistive technologies using ARIA attributes.

# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-05 - [Search Feedback & Keyboard Accessibility]
**Learning:** List views benefit greatly from immediate feedback like 'No results' states and ARIA live regions to announce result counts. Additionally, providing a keyboard shortcut (like '/') to focus the search input, indicated by a hint in the placeholder, significantly improves navigation efficiency for power users and accessibility for those relying on keyboards.
**Action:** Implement 'No results' rows, result count announcements, and '/' search shortcuts in all list-based interfaces.

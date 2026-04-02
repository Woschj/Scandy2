# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-15 - [Search UX & Accessibility]
**Learning:** Global keyboard shortcuts (like '/') in shared templates must be encapsulated within element existence checks to prevent JS crashes on pages where the element is absent. Using `MutationObserver` on `tbody` allows for robust, decoupled UI feedback (counts, empty states) that works across multiple independent filtering mechanisms.
**Action:** Always wrap global listeners in existence checks and use `MutationObserver` for state-to-UI synchronization in complex list views.

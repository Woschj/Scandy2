# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-16 - [Dynamic List Feedback & Shortcuts]
**Learning:** In list views, using a `MutationObserver` on the table body allows for centralized, decoupled feedback logic (like "No results found" messages and result counts) that works regardless of whether filtering is triggered by search, dropdowns, or complex logic. Adding keyboard shortcuts like `/` for focus and `Esc` for clearing significantly improves power-user efficiency.
**Action:** Implement `MutationObserver` for dynamic table states and standard keyboard shortcuts in all data-heavy list views.

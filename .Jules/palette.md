# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-31 - [Search Accessibility and Feedback]
**Learning:** List views benefit from immediate accessible feedback. Using a `MutationObserver` on the table body allows for real-time updates to ARIA live regions and "No results" states that stay in sync with both text-based search and filter-based visibility changes. Global keyboard shortcuts like '/' should be scoped to ignore events when the user is already focused on an input.
**Action:** Implement `MutationObserver` for synchronized list feedback and ensure shortcut handlers are focus-aware.

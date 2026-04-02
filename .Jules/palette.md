# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2025-04-02 - [Dynamic Search Feedback]
**Learning:** Client-side search and filtering should provide immediate feedback via `aria-live="polite"` regions to announce result counts and a visual empty state ("No results found") to inform users when no matches are found, especially in paginated or large lists.
**Action:** Implement result count announcements and explicit empty state rows in all data tables with client-side filtering.

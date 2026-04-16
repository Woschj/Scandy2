# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-15 - [Unified Search & Filter Feedback]
**Learning:** In list-heavy applications, providing immediate feedback on filter state (result counts) and handling empty results gracefully (empty states with reset buttons) significantly reduces user frustration. Combining this with `aria-live` status updates ensures accessibility for all users.
**Action:** Centralize search/filter UI state management (like `updateSearchUI`) to maintain consistency across different list implementations (Tools, Workers, etc.).

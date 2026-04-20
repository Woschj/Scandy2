# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-20 - [Centralized Search Feedback & Row Visibility]
**Learning:** In list views with client-side filtering, users need immediate feedback on the number of matches. A centralized `updateSearchUI` function that synchronizes a visual counter, an `aria-live` status region, and an empty state row ("No results") provides a much more intuitive experience. For row visibility, using explicit `style.display = 'table-row'` with `!important` is more robust than class toggling when working with DaisyUI/Tailwind tables in diverse rendering contexts.
**Action:** Use a centralized update pattern for list views and ensure empty states are explicitly handled in the DOM.

# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-03 - [Unified List Filtering]
**Learning:** Consolidating search and filter logic into a single "unified" function in the base template prevents fragmented filter states where search results don't respect dropdown filters (and vice versa). Providing a "No results" row with visual feedback (icon + text) significantly improves the UX when filters are too restrictive.
**Action:** Use unified filtering logic for all list views and always include a "No results" feedback state.

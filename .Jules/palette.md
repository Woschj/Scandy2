# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-02-25 - [No Results Feedback in Tables]
**Learning:** When implementing a 'No results' feedback row in a table managed by JavaScript, ensure that iterating loops (search/filter) explicitly exclude the feedback row using selectors like `tr:not(#noResultsRow)`. Additionally, use `style.display` toggling rather than Tailwind's `.hidden` class to avoid conflicts with `!important` CSS rules and ensure visibility even if parent scripts set inline styles.
**Action:** Always verify that metadata rows are excluded from data iteration loops and use robust visibility management.

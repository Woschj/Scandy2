# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-01 - [Safe Form Loading State]
**Learning:** Disabling a submit button immediately in the `onsubmit` handler can sometimes interfere with form submission. Using `setTimeout(() => { btn.disabled = true; }, 0)` ensures the browser processes the submit event before the button becomes non-interactive.
**Action:** Always wrap `disabled = true` in a `setTimeout(..., 0)` when implementing immediate loading feedback on forms to prevent submission cancellation.

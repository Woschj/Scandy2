# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-03 - [Authentication Flow Standardization]
**Learning:** Authentication forms (login, reset password) should share a consistent visual language. Using centered DaisyUI cards with appropriate icons (e.g., `fas fa-unlock-alt`, `fas fa-key`) and standardized 'Back to Login' links makes the flow feel unified and trustworthy.
**Action:** Always maintain consistency in the authentication UI by reusing the centered card pattern and accessible input attributes.

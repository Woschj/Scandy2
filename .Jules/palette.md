## 2026-02-18 - [Accessibility Patterns in Scandy]
**Learning:** Many interactive elements in Scandy (cards, icons) were missing proper ARIA labels and keyboard accessibility. Form labels were also often not programmatically associated with their inputs.
**Action:** Always use `role="button"`, `tabindex="0"`, and `onkeydown` for clickable `div`s. Ensure every input has a corresponding label with a `for` attribute matching the input's `id`. Use `aria-label` for icon-only buttons.

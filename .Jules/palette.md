## 2026-02-18 - [Accessibility & Interaction Feedback]
**Learning:** Custom interactive elements (like cards used as buttons) must have proper ARIA roles, tabindex, and keyboard event handlers (Enter/Space) to be accessible. Additionally, async buttons should always provide visual loading states and use a `finally` block in JS to ensure the button is restored if the modal stays open or on error.
**Action:** Always check for `role="button"` and `tabindex="0"` on non-button interactive elements, and implement robust button state management for async calls.

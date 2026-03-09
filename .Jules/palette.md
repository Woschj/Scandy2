# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-03-09 - [Sortable Table Header Accessibility]
**Learning:** Using `<div>` for sortable table headers makes them inaccessible to keyboard users and screen readers. Implementing them as `<button type="button">` with `aria-sort` attributes and Tailwind focus rings (`focus:ring-2 focus:ring-primary/50`) ensures they are interactive, perceivable, and navigable.
**Action:** Always use semantic buttons for sortable headers and manage `aria-sort` states dynamically.

## 2026-03-09 - [Robust Search Clear Pattern]
**Learning:** A "Clear Search" button in a `join` group should trigger the `input` event on the text field after clearing the value to ensure that all listeners (e.g., live filtering) are synchronized. Using `el.style.display` for visibility toggling is more reliable in mock testing environments than class-based toggling.
**Action:** Implement search clear buttons that reset value, dispatch `input` event, and return focus.

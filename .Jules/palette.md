# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-02 - [Authentication Flow Navigation]
**Learning:** Navigation links in authentication flows (like "Zurück zum Login") should be styled consistently as low-emphasis but easily discoverable links. Using a left arrow icon (`fas fa-arrow-left`) and a hover-sensitive link class (`link-hover`) provides clear directional cues without overwhelming the primary action button.
**Action:** Use the `link link-hover text-sm flex items-center gap-2` pattern for secondary navigation in forms.

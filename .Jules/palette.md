# Palette's Journal - UX & Accessibility Learnings

## 2026-02-15 - [QuickScan Modal Accessibility]
**Learning:** Custom interactive cards implemented as `div`s need `role="button"`, `tabindex="0"`, and `onkeydown` handlers to be accessible to keyboard users. Additionally, dynamic content updates in these cards should be wrapped in `aria-live="polite"` regions to be announced by screen readers.
**Action:** Always check custom selection UI for keyboard accessibility and ensure dynamic updates are announced.

## 2026-02-15 - [Semantic Form Labels]
**Learning:** Even with clear visual labels, missing `for` attributes on `<label>` elements prevents proper association with inputs for assistive technologies.
**Action:** Explicitly link labels and inputs using `for` and `id` attributes in all form components.

## 2026-04-07 - [Standardized List Search & Shortcuts]
**Learning:** Adding a discoverable keyboard shortcut hint `( / )` and an `aria-live` status region to search inputs significantly improves both efficiency for power users and accessibility for screen reader users. Ensuring an explicit "No results" state prevents user confusion when filters return an empty set.
**Action:** Implement centralized `updateSearchStatus` logic and global `/` shortcuts for all searchable list views to provide consistent feedback and navigation.

## 2026-02-15 - [Missing Accessibility Utilities]
**Learning:** The project's design system (based on DaisyUI) lacked standard accessibility utilities like `sr-only` and `focus:not-sr-only`. This prevents common accessibility patterns like "Skip to content" links from being implemented without adding custom CSS.
**Action:** Always verify the existence of `.sr-only` classes before implementing accessibility features. If missing, define them in the base template or global stylesheet using standard patterns (position: absolute, width: 1px, clip, etc.).

## 2026-02-15 - [Keyboard Handlers for Custom Buttons]
**Learning:** When turning a `div` or other non-button element into a button using `role="button"` and `tabindex="0"`, simply adding a click handler is insufficient. An `onkeydown` handler for "Enter" and " " (Space) is required, and `event.preventDefault()` must be called for the Space key to prevent the page from scrolling.
**Action:** Use `onkeydown="if(event.key==='Enter' || event.key===' ') { event.preventDefault(); this.click(); }"` for all custom interactive elements.

## 2026-02-20 - [Search Bar Usability and Accessibility]
**Learning:** Adding a "Clear Search" button significantly improves usability in list-heavy applications. To implement this correctly: 1. Use `relative` positioning on the input container. 2. Ensure the clear button has a descriptive `aria-label`. 3. In JavaScript, manually dispatch an `input` event after clearing the value so that existing listeners (like live-filtering) are triggered. 4. Return focus to the input field after clearing for better keyboard flow.
**Action:** Always include a clear button for search inputs in list views and ensure it triggers an `input` event.

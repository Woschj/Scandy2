## 2026-02-15 - [Missing Accessibility Utilities]
**Learning:** The project's design system (based on DaisyUI) lacked standard accessibility utilities like `sr-only` and `focus:not-sr-only`. This prevents common accessibility patterns like "Skip to content" links from being implemented without adding custom CSS.
**Action:** Always verify the existence of `.sr-only` classes before implementing accessibility features. If missing, define them in the base template or global stylesheet using standard patterns (position: absolute, width: 1px, clip, etc.).

## 2026-02-15 - [Keyboard Handlers for Custom Buttons]
**Learning:** When turning a `div` or other non-button element into a button using `role="button"` and `tabindex="0"`, simply adding a click handler is insufficient. An `onkeydown` handler for "Enter" and " " (Space) is required, and `event.preventDefault()` must be called for the Space key to prevent the page from scrolling.
**Action:** Use `onkeydown="if(event.key==='Enter' || event.key===' ') { event.preventDefault(); this.click(); }"` for all custom interactive elements.

## 2026-02-17 - [Visible Focus Indicators for Custom Interactive Elements]
**Learning:** When using `role="button"` and `tabindex="0"` on non-semantic elements like `div` cards, standard browser focus indicators are often missing or inconsistent. Adding explicit focus styles is necessary for a good UX.
**Action:** Use Tailwind classes like `focus:outline-none focus:ring-4 focus:ring-primary/50` to provide clear, theme-consistent visual feedback during keyboard navigation.

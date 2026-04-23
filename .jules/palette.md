## 2026-02-15 - [Missing Accessibility Utilities]
**Learning:** The project's design system (based on DaisyUI) lacked standard accessibility utilities like `sr-only` and `focus:not-sr-only`. This prevents common accessibility patterns like "Skip to content" links from being implemented without adding custom CSS.
**Action:** Always verify the existence of `.sr-only` classes before implementing accessibility features. If missing, define them in the base template or global stylesheet using standard patterns (position: absolute, width: 1px, clip, etc.).

## 2026-02-15 - [Keyboard Handlers for Custom Buttons]
**Learning:** When turning a `div` or other non-button element into a button using `role="button"` and `tabindex="0"`, simply adding a click handler is insufficient. An `onkeydown` handler for "Enter" and " " (Space) is required, and `event.preventDefault()` must be called for the Space key to prevent the page from scrolling.
**Action:** Use `onkeydown="if(event.key==='Enter' || event.key===' ') { event.preventDefault(); this.click(); }"` for all custom interactive elements.

## 2026-02-15 - [Async Action Feedback]
**Learning:** Async action triggers (e.g., 'Confirm' buttons) should provide visual feedback by displaying a loading spinner and becoming disabled during processing. The button's original state (HTML content and disabled property) must be restored using a 'finally' block in JavaScript to ensure the UI remains functional regardless of the outcome.
**Action:** Use a `try...catch...finally` pattern for all async UI interactions to manage loading states and ensure consistency.

## 2026-02-15 - [Timed Feedback for File Downloads]
**Learning:** For file downloads (like Excel exports) where the server response doesn't provide a trivial hook for JavaScript to detect completion, a timed loading state (e.g., 5 seconds) provides a significantly better UX than no feedback. It acknowledges the user's action and prevents multiple clicks while the server generates the file.
**Action:** Apply a temporary `disabled` state and `loading` indicator to export links/buttons using a `setTimeout` to restore the original state after a reasonable delay (5-10s).

## 2026-04-02 - [Global Keyboard Shortcuts and Input Focus]
**Learning:** When implementing global keyboard shortcuts (e.g., '/' to focus search), it is critical to exclude the trigger if the user is already focused on an 'INPUT' or 'TEXTAREA'. This prevents the shortcut character from being typed into an active field or interfering with the user's current data entry.
**Action:** Always wrap global shortcut listeners in a check like `if (!['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName))`.

import os
from playwright.sync_api import sync_playwright

def verify_ui():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(record_video_dir="/home/jules/verification/video")
        page = context.new_page()

        # Verify Dashboard Exports
        dashboard_path = f"file://{os.getcwd()}/verification/dashboard.html"
        page.goto(dashboard_path)
        page.wait_for_timeout(500)

        # Take screenshot of dashboard header with export buttons
        page.set_viewport_size({"width": 1280, "height": 2000})
        page.screenshot(path="/home/jules/verification/verification.png", full_page=True)

        # Click an export button to see the loading state
        page.get_by_role("link", name="Standard Export").click()
        page.wait_for_timeout(500)

        # Verify QuickScan Modal Close Icon
        base_path = f"file://{os.getcwd()}/verification/base.html"
        page.goto(base_path)
        page.wait_for_timeout(500)

        # Open QuickScan modal
        page.click("#quickScanTrigger")
        page.wait_for_timeout(500)

        context.close()
        browser.close()

if __name__ == "__main__":
    verify_ui()

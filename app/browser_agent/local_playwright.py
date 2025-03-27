from pathlib import Path
import os
from playwright.sync_api import Browser as PlaywrightBrowser, Page
from .base_playwright_browser import BasePlaywrightBrowser


class LocalPlaywrightBrowser(BasePlaywrightBrowser):
    """Launches a local Chromium instance using Playwright."""

    def __init__(self, headless: bool = False):
        super().__init__()
        self.headless = headless

    def _get_browser_and_page(self) -> tuple[PlaywrightBrowser, Page]:
        width, height = self.dimensions
        launch_args = [f"--window-size={width},{height}", "--disable-extensions", "--disable-file-system"]
        browser = self._playwright.chromium.launch(
            chromium_sandbox=True,
            headless=self.headless,
            args=launch_args,
            env={"DISPLAY": ":0"}
        )

        # Create downloads directory if it doesn't exist
        downloads_path = Path("./downloads").absolute()
        downloads_path.mkdir(exist_ok=True)
        
        # Configure browser context with download options
        context = browser.new_context(
            accept_downloads=True
        )
        
        print(f"Downloads path: {downloads_path}")

        # Add event listeners for page creation and closure
        context.on("page", self._handle_new_page)
        
        # Handle download events
        context.on("download", self._handle_download)

        page = context.new_page()
        page.set_viewport_size({"width": width, "height": height})
        page.on("close", self._handle_page_close)

        page.goto("https://bing.com")

        return browser, page
        
    def _handle_download(self, download):
        """Handle download events."""
        print(f"Download started: {download.suggested_filename}")
        try:
            downloads_dir = Path("./downloads").absolute()
            save_path = downloads_dir / download.suggested_filename
            
            # Use Playwright's built-in save_as method
            download.save_as(save_path)
            
            print(f"Download saved to: {save_path}")
            
            # Wait for download to complete
            path_info = download.path()
            if path_info:
                print(f"Download saved at: {path_info}")
        except Exception as e:
            print(f"Error handling download: {e}")

    def _handle_new_page(self, page: Page):
        """Handle the creation of a new page."""
        print("New page created")
        self._page = page
        page.on("close", self._handle_page_close)

    def _handle_page_close(self, page: Page):
        """Handle the closure of a page."""
        print("Page closed")
        if self._page == page:
            if self._browser.contexts[0].pages:
                self._page = self._browser.contexts[0].pages[-1]
            else:
                print("Warning: All pages have been closed.")
                self._page = None
import time
import base64
from typing import List, Dict, Literal, Optional
from playwright.sync_api import sync_playwright, Browser as PlaywrightBrowser, Page
from app.utils import check_blocklisted_url
from app.browser_agent.browser import Browser

# Optional: key mapping if your model uses "CUA" style keys
CUA_KEY_TO_PLAYWRIGHT_KEY = {
    "/": "Divide",
    "\\": "Backslash",
    "alt": "Alt",
    "arrowdown": "ArrowDown",
    "arrowleft": "ArrowLeft",
    "arrowright": "ArrowRight",
    "arrowup": "ArrowUp",
    "backspace": "Backspace",
    "capslock": "CapsLock",
    "cmd": "Meta",
    "ctrl": "Control",
    "delete": "Delete",
    "end": "End",
    "enter": "Enter",
    "esc": "Escape",
    "home": "Home",
    "insert": "Insert",
    "option": "Alt",
    "pagedown": "PageDown",
    "pageup": "PageUp",
    "shift": "Shift",
    "space": " ",
    "super": "Meta",
    "tab": "Tab",
    "win": "Meta",
}


class BasePlaywrightBrowser(Browser):
    """
    Abstract base for Playwright-based browser implementations:

      - Subclasses override `_get_browser_and_page()` to do local or remote connection,
        returning (PlaywrightBrowser, Page).
      - This base class handles context creation (`__enter__`/`__exit__`),
        plus standard browser actions like click, scroll, etc.
      - Provides browser navigation with `goto(url)`, `back()`, and `forward()`.
    """

    dimensions = (1024, 768)

    def __init__(self):
        self._playwright = None
        self._browser: PlaywrightBrowser | None = None
        self._page: Page | None = None

    def __enter__(self):
        # Start Playwright and call the subclass hook for getting browser/page
        self._playwright = sync_playwright().start()
        self._browser, self._page = self._get_browser_and_page()

        # Set up network interception to flag URLs matching domains in BLOCKED_DOMAINS
        def handle_route(route, request):
            url = request.url
            try:
                check_blocklisted_url(url)
                route.continue_()
            except ValueError as e:
                print(f"Flagging blocked domain: {url}")
                route.abort()

        self._page.route("**/*", handle_route)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def get_current_url(self) -> str:
        return self._page.url

    # --- Common "Computer" actions ---
    def screenshot(self) -> str:
        """Capture only the viewport (not full_page)."""
        png_bytes = self._page.screenshot(full_page=False)
        return base64.b64encode(png_bytes).decode("utf-8")

    def click(self, x: int, y: int, button: str = "left") -> None:
        match button:
            case "back":
                self.back()
            case "forward":
                self.forward()
            case "wheel":
                self._page.mouse.wheel(x, y)
            case _:
                button_mapping = {"left": "left", "right": "right"}
                button_type = button_mapping.get(button, "left")
                self._page.mouse.click(x, y, button=button_type)
                
    def click_selector(self, selector: str, button: str = "left") -> None:
        """Click on an element using a CSS, XPath, or Playwright locator-style selector."""
        button_mapping = {"left": "left", "right": "right"}
        button_type = button_mapping.get(button, "left")
        
        # Handle Playwright's role-based selectors
        if selector.startswith("role="):
            # Extract role type and parameters
            role_parts = selector[5:].split("[", 1)
            role_type = role_parts[0]
            
            if len(role_parts) > 1 and role_parts[1].endswith("]"):
                # Extract name parameter
                params = role_parts[1][:-1].split("=", 1)
                if len(params) > 1 and params[0] == "name" and params[1].startswith("'") and params[1].endswith("'"):
                    name = params[1][1:-1]
                    # Use the locator API for role-based selection
                    self._page.get_by_role(role_type, name=name).click(button=button_type)
                    return
        # Handle specific SQL query selector
        elif "[role='link'][name='sql icon SQL query']" in selector:
            try:
                # Use the get_by_role API directly
                self._page.get_by_role("link", name="sql icon SQL query").click(button=button_type)
                return
            except Exception:
                # Fall back to CSS selector
                pass
        elif selector.startswith("data-testid="):
            # Parse data-testid selector
            parts = selector.split("=", 1)
            if len(parts) > 1:
                value = parts[1]
                # Handle nested selectors
                if ">>" in value:
                    main_part, sub_part = value.split(">>", 1)
                    self._page.locator(f"[data-testid='{main_part.strip()}']").locator(sub_part.strip()).click(button=button_type)
                else:
                    self._page.locator(f"[data-testid='{value}']").click(button=button_type)
                return
                
        # Default to standard selector
        self._page.click(selector, button=button_type)

    def double_click(self, x: int, y: int) -> None:
        self._page.mouse.dblclick(x, y)

    def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None:
        self._page.mouse.move(x, y)
        self._page.evaluate(f"window.scrollBy({scroll_x}, {scroll_y})")

    def type(self, text: str) -> None:
        self._page.keyboard.type(text)

    def wait(self, ms: int = 1000) -> None:
        time.sleep(ms / 1000)
        
    def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> bool:
        """Wait for a selector to appear in the page.
        
        Args:
            selector: CSS or XPath selector, or Playwright locator-style selector
            timeout: Maximum time to wait in milliseconds, None for default browser timeout
            
        Returns:
            True if the selector appeared, False if it timed out
        """
        try:
            timeout_ms = timeout if timeout is not None else 30000  # 30 seconds default
            
            # Handle Playwright's role-based selectors
            if selector.startswith("role="):
                # Extract role type and parameters
                role_parts = selector[5:].split("[", 1)
                role_type = role_parts[0]
                
                if len(role_parts) > 1 and role_parts[1].endswith("]"):
                    # Extract name parameter
                    params = role_parts[1][:-1].split("=", 1)
                    if len(params) > 1 and params[0] == "name" and params[1].startswith("'") and params[1].endswith("'"):
                        name = params[1][1:-1]
                        # Use the locator API for role-based selection
                        self._page.get_by_role(role_type, name=name).wait_for(timeout=timeout_ms)
                        return True
            else:
                # For selectors from PlayWright recording that use attributes 
                if "[role='link'][name='sql icon SQL query']" in selector:
                    try:
                        # Use the get_by_role API directly
                        self._page.get_by_role("link", name="sql icon SQL query").wait_for(timeout=timeout_ms)
                        return True
                    except Exception:
                        # Fall back to CSS selector
                        pass
                        
                # Standard CSS selector
                self._page.wait_for_selector(selector, timeout=timeout_ms)
                return True
                
            return False
        except Exception as e:
            print(f"Selector error: {e}")
            return False

    def move(self, x: int, y: int) -> None:
        self._page.mouse.move(x, y)

    def keypress(self, keys: List[str]) -> None:
        mapped_keys = [CUA_KEY_TO_PLAYWRIGHT_KEY.get(key.lower(), key) for key in keys]
        for key in mapped_keys:
            self._page.keyboard.down(key)
        for key in reversed(mapped_keys):
            self._page.keyboard.up(key)

    def drag(self, path: List[Dict[str, int]]) -> None:
        if not path:
            return
        self._page.mouse.move(path[0]["x"], path[0]["y"])
        self._page.mouse.down()
        for point in path[1:]:
            self._page.mouse.move(point["x"], point["y"])
        self._page.mouse.up()

    # --- Extra browser-oriented actions ---
    def goto(self, url: str) -> None:
        try:
            return self._page.goto(url)
        except Exception as e:
            print(f"Error navigating to {url}: {e}")

    def back(self) -> None:
        return self._page.go_back()

    def forward(self) -> None:
        return self._page.go_forward()
        
    def get_page_html(self) -> str:
        """Get the HTML content of the current page."""
        return self._page.content()
    
    def get_element_info(self, selector: str) -> dict:
        """Get information about an element by selector.
        
        Returns a dictionary with element properties like tag, text, attributes, etc.
        """
        return self._page.evaluate("""
            selector => {
                const el = document.querySelector(selector);
                if (!el) return null;
                
                const attributes = {};
                for (const attr of el.attributes) {
                    attributes[attr.name] = attr.value;
                }
                
                return {
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText,
                    html: el.innerHTML,
                    attributes: attributes,
                    isVisible: el.offsetWidth > 0 && el.offsetHeight > 0,
                    boundingBox: el.getBoundingClientRect().toJSON()
                };
            }
        """, selector)
    
    def fill_form(self, selector: str, value: str) -> None:
        """Fill a form field with the given value."""
        self._page.fill(selector, value)
    
    def extract_text(self, selector: str = "body") -> str:
        """Extract text content from an element."""
        return self._page.text_content(selector) or ""
    
    def open_new_tab(self, url: str = "") -> None:
        """Open a new tab and switch to it."""
        new_page = self._browser.new_page()
        # Store the new page as the current one
        self._page = new_page
        if url:
            self.goto(url)
    
    def switch_tab(self, tab_index: int) -> None:
        """Switch to a different tab by index."""
        pages = self._browser.contexts[0].pages
        if 0 <= tab_index < len(pages):
            self._page = pages[tab_index]
        else:
            raise IndexError(f"Tab index {tab_index} out of range (0-{len(pages)-1})")

    # --- Subclass hook ---
    def _get_browser_and_page(self) -> tuple[PlaywrightBrowser, Page]:
        """Subclasses must implement, returning (PlaywrightBrowser, Page)."""
        raise NotImplementedError
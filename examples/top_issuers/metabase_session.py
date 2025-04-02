"""
Metabase session management for browser automation.
"""

import os
import time
import base64
import traceback
from pathlib import Path

import sys
# Ensure access to the root directory modules
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.browser_agent.local_playwright import LocalPlaywrightBrowser

class PersistentMetabaseSession:
    """A class that maintains a persistent browser session with Metabase."""
    
    def __init__(self, headless=False, metabase_url="https://metabase.startengine.com"):
        self.headless = headless
        self.metabase_url = metabase_url
        self.username = os.getenv("METABASE_USERNAME")
        self.password = os.getenv("METABASE_PASSWORD")
        self.browser = None
        self.initialized = False
        # Add increased default timeout for finding elements
        self.default_timeout = 8000  # 8 seconds
        
        if not self.username or not self.password:
            raise ValueError("Metabase credentials are required. Set them in creds.env.")
    
    def find_and_click_element(self, selectors, text_contains=None, timeout=None):
        """
        Enhanced method to find and click an element with better error handling.
        
        Args:
            selectors (list): List of CSS selectors to try
            text_contains (str, optional): Text that should be contained in the element
            timeout (int, optional): Timeout in ms, defaults to self.default_timeout
            
        Returns:
            bool: True if element was found and clicked, False otherwise
        """
        if timeout is None:
            timeout = self.default_timeout
            
        if isinstance(selectors, str):
            selectors = [selectors]
            
        print(f"Finding element with selectors: {selectors} (text contains: {text_contains})")
        
        # Try each selector in turn
        for selector in selectors:
            try:
                if self.browser.wait_for_selector(selector, timeout=timeout):
                    print(f"Found element with selector: {selector}")
                    
                    # If text_contains is specified, verify the element has the expected text
                    if text_contains:
                        try:
                            element_info = self.browser.get_element_info(selector)
                            if element_info and text_contains in element_info.get("text", ""):
                                print(f"Element text contains '{text_contains}', clicking...")
                                self.browser.click_selector(selector)
                                self.browser.wait(1000)  # Wait after click
                                return True
                            else:
                                print(f"Element doesn't contain '{text_contains}', skipping")
                                continue
                        except Exception as text_error:
                            print(f"Error checking element text: {text_error}")
                            # If we can't check the text, try clicking anyway
                            print("Clicking element anyway")
                            self.browser.click_selector(selector)
                            self.browser.wait(1000)
                            return True
                    else:
                        # No text verification needed, just click
                        print("No text verification required, clicking element")
                        self.browser.click_selector(selector)
                        self.browser.wait(1000)
                        return True
            except Exception as e:
                print(f"Error with selector '{selector}': {e}")
                continue
                
        print(f"Failed to find and click element with selectors: {selectors}")
        return False
    
    def __enter__(self):
        """Initialize the browser session when entering the context."""
        print(f"Starting persistent browser session (headless: {self.headless})...")
        try:
            # Create the browser instance
            self.browser = LocalPlaywrightBrowser(headless=self.headless)
            print(f"Browser instance created: {self.browser}")
            
            # Important: Need to initialize the browser's internal state
            self.browser.__enter__()
            print(f"Browser initialized. Available attributes: {dir(self.browser)}")
            
            # Check if _page exists
            if hasattr(self.browser, '_page'):
                print(f"Browser has _page attribute: {self.browser._page}")
        except Exception as e:
            print(f"Error initializing browser: {e}")
            print(traceback.format_exc())
            raise
            
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the browser when exiting the context."""
        if self.browser:
            print("Closing browser session...")
            try:
                # Check if browser has _page attribute and close it directly
                if hasattr(self.browser, '_page') and self.browser._page:
                    print("Closing browser page...")
                    self.browser._page.close()
                
                # Check if browser has _browser attribute and close it directly
                if hasattr(self.browser, '_browser') and self.browser._browser:
                    print("Closing browser instance...")
                    self.browser._browser.close()
                
                # Try to call the browser's own exit method as a fallback
                try:
                    self.browser.__exit__(exc_type, exc_val, exc_tb)
                except:
                    pass
                    
            except Exception as e:
                print(f"Warning: Error closing browser: {e}")
                
            self.browser = None
            self.initialized = False
    
    def initialize_session(self):
        """Navigate to Metabase and log in."""
        if self.initialized:
            return
            
        print("Initializing Metabase session...")
        
        # Add a small delay before initialization to ensure browser is ready
        time.sleep(2)
        
        # Navigate to Metabase with timeout handling
        try:
            print(f"Navigating to {self.metabase_url}...")
            self.browser.goto(self.metabase_url)
            self.browser.wait(5000)  # Wait longer for page to load
            print("Successfully loaded Metabase")
        except Exception as e:
            print(f"Error navigating to Metabase: {e}")
            # Take a screenshot if possible
            try:
                screenshot = self.browser.screenshot()
                screenshot_path = Path.cwd() / f"navigation_error_{int(time.time())}.png"
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(screenshot))
                print(f"Navigation error screenshot saved to: {screenshot_path}")
            except:
                pass
            raise  # Re-raise the exception
        
        # Check for login form
        login_elements = ["input[name='username']", "input[placeholder='Email address']"]
        needs_login = any(self.browser.wait_for_selector(selector, timeout=2000) for selector in login_elements)
        
        if needs_login:
            print("Logging into Metabase...")
            # Find and fill username field
            for selector in login_elements:
                if self.browser.wait_for_selector(selector, timeout=2000):
                    self.browser.click_selector(selector)
                    self.browser.wait(500)
                    self.browser.type(self.username)
                    break
            
            # Tab to password field
            self.browser.keypress(["Tab"])
            self.browser.wait(200)
            self.browser.type(self.password)
            self.browser.wait(500)
            
            # Click login button or press Enter
            login_button = "button[type='submit']"
            if self.browser.wait_for_selector(login_button, timeout=2000):
                self.browser.click_selector(login_button)
            else:
                # Try to find any buttons that might be the login button
                submit_buttons = ["button.Button", "button.Button--primary"]
                clicked = False
                for btn_selector in submit_buttons:
                    if self.browser.wait_for_selector(btn_selector, timeout=2000):
                        try:
                            # Check if this is the sign-in button
                            element_info = self.browser.get_element_info(btn_selector)
                            if element_info and ("Sign in" in element_info.get("text", "") or 
                                               "Log in" in element_info.get("text", "")):
                                self.browser.click_selector(btn_selector)
                                clicked = True
                                break
                        except:
                            pass
                
                # If no button found, just press Enter
                if not clicked:
                    self.browser.keypress(["Enter"])
            
            self.browser.wait(5000)  # Wait for login to complete
        else:
            print("Already logged in to Metabase")
        
        self.initialized = True
    
    def run_query(self, sql_query, database="primary_facade", download_path=None):
        """Run a SQL query and download the results."""
        if not self.browser:
            raise ValueError("Browser session not initialized. Use with context manager.")
            
        if download_path is None:
            download_path = str(Path.cwd())
        elif isinstance(download_path, Path):
            download_path = str(download_path)
            
        print(f"Running query against database '{database}' and saving to '{download_path}'")
            
        try:
            # Make sure we're logged in
            try:
                self.initialize_session()
            except Exception as e:
                print(f"Error during initialization: {e}")
                print(traceback.format_exc())
                raise RuntimeError(f"Session initialization failed: {e}")
            
            # Navigate to new query interface
            print("Creating new SQL query...")
            try:
                self._create_new_question()
            except Exception as e:
                print(f"Error creating new question: {e}")
                print(traceback.format_exc())
                raise RuntimeError(f"Failed to create new question: {e}")
            
            # Select database
            print(f"Selecting database: {database}...")
            try:
                self._select_database(database)
            except Exception as e:
                print(f"Error selecting database: {e}")
                print(traceback.format_exc())
                raise RuntimeError(f"Failed to select database: {e}")
            
            # Enter and run query
            print("Running SQL query...")
            try:
                self._run_query(sql_query)
            except Exception as e:
                print(f"Error running query: {e}")
                print(traceback.format_exc())
                raise RuntimeError(f"Failed to run query: {e}")
            
            # Download results
            print("Downloading results...")
            try:
                csv_file_path = self._download_results(download_path)
                print(f"Results saved to: {csv_file_path}")
                return csv_file_path
            except Exception as e:
                print(f"Error downloading results: {e}")
                print(traceback.format_exc())
                raise RuntimeError(f"Failed to download results: {e}")
            
        except Exception as e:
            print(f"Error running query: {e}")
            print(traceback.format_exc())
            
            # Take a screenshot to help debug the issue
            timestamp = int(time.time())
            screenshot_path = Path(download_path) / f"error_screenshot_{timestamp}.png"
            try:
                if hasattr(self.browser, 'screenshot'):
                    print("Taking error screenshot...")
                    screenshot = self.browser.screenshot()
                    with open(screenshot_path, "wb") as f:
                        # Screenshot is base64 encoded, so decode it first
                        f.write(base64.b64decode(screenshot))
                    print(f"Error screenshot saved to: {screenshot_path}")
            except Exception as screenshot_error:
                print(f"Could not save error screenshot: {screenshot_error}")
            return None
    
    def _create_new_question(self):
        """Navigate to the SQL editor."""
        # First check if we need to go to the Metabase home page to find the New button
        current_url = self.browser.get_current_url() if hasattr(self.browser, 'get_current_url') else ""
        if not "/question/" in current_url and not current_url.endswith("/"):
            try:
                print("Navigating to Metabase home page to find New button...")
                self.browser.goto(self.metabase_url)
                self.browser.wait(3000)
            except Exception as e:
                print(f"Error navigating to home page: {e}")
        
        # Use our improved click method to find and click the New button
        new_button_selectors = [
            "button[data-testid='new-button']", 
            ".Icon-add", 
            "button.Button", 
            "button[aria-label='New']",
            "button.NewButton"
        ]
        
        # Try to find and click using our improved method
        clicked = self.find_and_click_element(new_button_selectors, text_contains="New")
        
        # If that fails, try one more approach with the Playwright API directly
        if not clicked:
            try:
                print("Trying direct role-based selector for New button...")
                new_button = self.browser._page.get_by_role("button", name="New")
                if new_button:
                    print("Found New button using role selector, clicking...")
                    new_button.click()
                    clicked = True
                    self.browser.wait(1000)
            except Exception as e:
                print(f"Role-based New button selector failed: {e}")
                
        if not clicked:
            raise ValueError("Could not find New button")
        
        # Look for SQL query option with improved error handling
        print("Looking for SQL query option...")
        
        # First try to find by role directly as it's most reliable
        try:
            print("Trying direct role-based selector for SQL query...")
            sql_link = self.browser._page.get_by_role("link", name="SQL query")
            if sql_link:
                print("Found SQL query link using role selector, clicking...")
                sql_link.click()
                self.browser.wait(2000)
                return  # Exit early if we found and clicked the element
        except Exception as e:
            print(f"Role-based SQL query selector failed: {e}")
            
        # Use improved method to find and click SQL query option
        sql_selectors = [
            "a[href*='/question#']", 
            "a.Button", 
            "a[data-metabase-event='Navbar;Create Question Click']",
            "a[href*='question/notebook']",
            "a[href*='#notebook']",
            ".NewButton a",
            "[data-metabase-event*='Question']",
            "a.text-brand-hover"
        ]
        
        clicked = self.find_and_click_element(sql_selectors, text_contains="SQL")
        
        # If that fails, try with broader text match
        if not clicked:
            clicked = self.find_and_click_element(sql_selectors, text_contains="Query")
            
        # Last resort - try once more with the API directly
        if not clicked:
            try:
                print("Trying final approach for SQL query option...")
                sql_link = self.browser._page.locator("a").filter(has_text="SQL query").first
                if sql_link:
                    sql_link.click()
                    clicked = True
                    self.browser.wait(2000)
            except Exception as e:
                print(f"Final SQL query selector attempt failed: {e}")
                
        if not clicked:
            raise ValueError("Could not find SQL query option")
        
        # Wait longer for the SQL editor to fully load
        self.browser.wait(8000)
    
    def _select_database(self, database_name):
        """Select the database to query."""
        # Click database selector with our improved method
        database_selectors = [
            "[data-testid='gui-builder-data'] a", 
            ".List-section-header", 
            ".QueryBuilder-section button",
            "div.PopoverBody a",  # More general selector
            ".PopoverBody button.Button"  # Another general selector
        ]
        
        print(f"Selecting database: {database_name}")
        clicked = self.find_and_click_element(database_selectors)
        
        # If that fails, try with the Playwright API directly
        if not clicked:
            try:
                print("Trying direct API for database selector...")
                db_selector = self.browser._page.get_by_test_id("gui-builder-data").locator("a")
                if db_selector:
                    db_selector.click()
                    clicked = True
                    self.browser.wait(1000)
            except Exception as e:
                print(f"Direct API for database selection failed: {e}")
                
        if not clicked:
            raise ValueError("Could not find database selector")
        
        # Wait after clicking the selector
        self.browser.wait(2000)
        
        # Search for database using improved approach
        search_selectors = [
            "[data-testid='list-search-field']",
            "input[type='search']",
            "input[placeholder*='search']",
            "input.input"
        ]
        
        # Try to find and click the search field
        search_clicked = self.find_and_click_element(search_selectors)
        
        # If we found the search field, type the database name
        if search_clicked:
            print(f"Found search field, typing database name: {database_name}")
            self.browser.wait(500)
            self.browser.type(database_name)
        else:
            # Try direct API approach
            try:
                print("Trying direct API for search field...")
                search_field = self.browser._page.get_by_test_id("list-search-field")
                if search_field:
                    search_field.fill(database_name)
                    search_clicked = True
            except Exception as e:
                print(f"Direct API for search field failed: {e}")
                
            if not search_clicked:
                print("Could not find search field, will try to select database directly")
        
        self.browser.wait(1000)
        
        # Press Enter or click on the option
        try:
            self.browser.keypress(["Enter"])
            self.browser.wait(1000)
        except:
            # Click on database option
            selectors = [
                f"div:has-text('{database_name}')", 
                f"heading:has-text('{database_name}')",
                f"li:has-text('{database_name}')",
                f".List-item:has-text('{database_name}')"
            ]
            
            # Try each selector
            for selector in selectors:
                if self.browser.wait_for_selector(selector, timeout=6000):
                    print(f"Found database option with selector: {selector}")
                    self.browser.click_selector(selector)
                    self.browser.wait(2000)
                    break
            
            # One more attempt with the Playwright API
            try:
                print("Trying direct text-based search for database...")
                db_item = self.browser._page.get_by_text(database_name)
                if db_item:
                    db_item.click()
                    self.browser.wait(2000)
            except Exception as e:
                print(f"Text-based database selection failed: {e}")
                
            # Give a longer wait after database selection
            self.browser.wait(3000)
    
    def _run_query(self, sql_query):
        """Enter and run the SQL query."""
        # Click the SQL editor using our improved helper method
        editor_selectors = [".ace_content", ".ace_editor", ".ace_text-input", ".ace_text-layer"]
        
        # Try to find and click the SQL editor
        print("Finding and clicking SQL editor...")
        clicked = self.find_and_click_element(editor_selectors, timeout=10000)
        
        # If helper method fails, try direct approach with the Playwright API
        if not clicked:
            try:
                print("Trying direct API for SQL editor...")
                ace_editor = self.browser._page.locator(".ace_editor").first
                if ace_editor:
                    ace_editor.click()
                    clicked = True
                    self.browser.wait(1000)
            except Exception as e:
                print(f"Direct API for SQL editor selection failed: {e}")
                
        if not clicked:
            raise ValueError("Could not find SQL editor")
        
        self.browser.wait(500)
        
        # Clear existing content and enter new query
        self.browser.keypress(["Control", "a"])
        self.browser.wait(200)
        self.browser.keypress(["Delete"])
        self.browser.wait(200)
        
        # Format the query - strip extra whitespace and ensure clean SQL
        clean_query = sql_query.strip()
        print(f"Entering SQL query:\n{clean_query}")
        
        # Type the query with extra newlines at the end 
        # Make sure the SQL is well-formatted for Metabase
        try:
            # Type character by character for more reliable input
            self.browser.keypress(["Control", "a"])
            self.browser.wait(200)
            self.browser.keypress(["Delete"])
            self.browser.wait(200)
            
            # Try more reliable typing approach
            if hasattr(self.browser._page, 'fill') and hasattr(self.browser._page, 'locator'):
                try:
                    # Try to use Playwright's more powerful fill method
                    self.browser._page.locator(".ace_text-input").fill(clean_query)
                    print("Used Playwright locator fill method")
                except Exception as e:
                    print(f"Playwright fill method failed: {e}")
                    # Fallback to typing each character
                    self.browser.type(clean_query)
            else:
                # Type each line with a small pause
                lines = clean_query.split('\n')
                for i, line in enumerate(lines):
                    self.browser.type(line)
                    if i < len(lines) - 1:
                        self.browser.keypress(["Enter"])
                        self.browser.wait(50)  # Small pause between lines
                
            # Add extra newlines at the end for good measure
            self.browser.keypress(["Enter"])
            self.browser.keypress(["Enter"])
        except Exception as e:
            print(f"Error typing query: {e}")
            # Try alternative input method
            try:
                # Fallback method 1
                if hasattr(self.browser, 'fill_form'):
                    self.browser.fill_form(".ace_editor", clean_query)
                    print("Used fill_form method")
                # Fallback method 2
                elif hasattr(self.browser._page, 'fill'):
                    selector = ".ace_text-input, .ace_content textarea, .ace_editor textarea"
                    self.browser._page.fill(selector, clean_query)
                    print("Used page.fill method")
                else:
                    # Last resort - just type it all at once
                    self.browser.type(clean_query + "\n\n")
                    print("Used basic type method")
            except Exception as e2:
                print(f"Alternative input methods failed: {e2}")
                # Last desperate attempt - character by character
                print("Trying character-by-character input...")
                for char in clean_query:
                    self.browser.type(char)
                    self.browser.wait(10)  # Tiny pause to avoid overflowing input buffer
        
        self.browser.wait(1000)
        
        # Use our improved helper method to find and click the Run button
        run_button_selectors = [
            "[data-testid='run-button']", 
            "button.RunButton", 
            "button.Button--primary",
            "button.Icon-play",
            "[aria-label='Run query']",
            ".NativeQueryEditor-run"
        ]
        
        print("Finding and clicking Run button...")
        clicked = self.find_and_click_element(run_button_selectors, text_contains="Run", timeout=8000)
        
        # If helper method fails, try with direct Playwright API approaches
        if not clicked:
            try:
                print("Trying direct test-id approach for Run button...")
                # Try different test ID paths
                test_id_paths = [
                    ["native-query-editor-sidebar", "run-button"],
                    ["run-button"],
                    ["query-builder-main", "run-button"]
                ]
                
                for path in test_id_paths:
                    try:
                        if len(path) == 1:
                            self.browser._page.get_by_test_id(path[0]).click()
                        else:
                            self.browser._page.get_by_test_id(path[0]).get_by_test_id(path[1]).click()
                        clicked = True
                        print(f"Successfully clicked Run button using test-id path: {path}")
                        break
                    except Exception as path_error:
                        print(f"Test-id path {path} failed: {path_error}")
                
                if not clicked:
                    # Try role approach
                    print("Trying role approach for Run button...")
                    self.browser._page.get_by_role("button", name="Run").click()
                    clicked = True
            except Exception as e:
                print(f"All direct Playwright approaches failed: {e}")
                
        if not clicked:
            try:
                # Last resort - try to press keyboard shortcut for Run (often Ctrl+Enter or Shift+Enter)
                print("Trying keyboard shortcuts for Run...")
                shortcuts = [
                    ["Control", "Enter"],
                    ["Shift", "Enter"]
                ]
                
                for shortcut in shortcuts:
                    try:
                        self.browser.keypress(shortcut)
                        print(f"Pressed keyboard shortcut: {shortcut}")
                        self.browser.wait(1000)
                        # Look for signs of query execution
                        if self.browser.wait_for_selector(".LoadingSpinner, .Loading", timeout=2000):
                            print("Query appears to be running after shortcut")
                            clicked = True
                            break
                    except Exception as shortcut_error:
                        print(f"Keyboard shortcut {shortcut} failed: {shortcut_error}")
                        
            except Exception as e:
                print(f"Keyboard shortcut approaches failed: {e}")
                
        if not clicked:
            raise ValueError("Could not find or activate Run button")
        
        # Wait for query execution with a longer timeout
        print("Waiting for query execution to complete...")
        self.browser.wait(10000)  # Increased timeout for query execution
    
    def _download_results(self, download_path):
        """Download the query results as CSV."""
        timestamp = int(time.time())
        expected_file_path = Path(download_path) / f"metabase_query_result_{timestamp}.csv"
        
        # Use our improved helper method to find and click the download button
        download_button_selectors = [
            "[data-testid='download-button']", 
            "button.Icon-download", 
            "button.Button",
            "[aria-label='Download results']",
            ".Icon-download",
            ".download-button"
        ]
        
        print("Finding and clicking download button...")
        clicked = self.find_and_click_element(download_button_selectors, text_contains="Download", timeout=8000)
        
        # If helper method fails, try with direct Playwright API approaches
        if not clicked:
            try:
                print("Trying direct test-id approach for download button...")
                self.browser._page.get_by_test_id("download-button").click()
                clicked = True
            except Exception as e:
                print(f"Test-id approach for download button failed: {e}")
                try:
                    # Try role approach
                    print("Trying role approach for download button...")
                    download_button = self.browser._page.get_by_role("button", name="Download")
                    if download_button:
                        download_button.click()
                        clicked = True
                except Exception as e:
                    print(f"Role approach for download button failed: {e}")
                
        if not clicked:
            try:
                # Try to find by icon
                print("Trying to find download button by icon class...")
                icon_buttons = self.browser._page.locator("button .Icon-download, button.Icon-download").all()
                if icon_buttons and len(icon_buttons) > 0:
                    icon_buttons[0].click()
                    clicked = True
            except Exception as e:
                print(f"Icon approach for download button failed: {e}")
                
        if not clicked:
            raise ValueError("Could not find download button")
        
        self.browser.wait(1000)
        
        # Use our improved helper method to find and click the CSV option
        with self.browser._page.expect_download() as download_info:
            csv_option_selectors = [
                "[data-testid='download-results-button']", 
                "a[data-testid='csv-download-button']", 
                "a.Link",
                ".Icon-download + span",
                "a[href*='csv']",
                "[aria-label='Download CSV']"
            ]
            
            print("Finding and clicking CSV download option...")
            clicked = self.find_and_click_element(csv_option_selectors, text_contains="CSV", timeout=8000)
            
            # If helper method fails, try with direct Playwright API approaches
            if not clicked:
                try:
                    print("Trying direct test-id approach for CSV option...")
                    test_id_options = ["download-results-button", "csv-download-button"]
                    for test_id in test_id_options:
                        try:
                            self.browser._page.get_by_test_id(test_id).click()
                            clicked = True
                            print(f"Successfully clicked CSV option using test-id: {test_id}")
                            break
                        except Exception as test_id_error:
                            print(f"Test-id {test_id} failed: {test_id_error}")
                    
                    if not clicked:
                        # Try finding by text
                        print("Trying to find CSV option by text...")
                        csv_link = self.browser._page.get_by_text("CSV", exact=False)
                        if csv_link:
                            csv_link.click()
                            clicked = True
                except Exception as e:
                    print(f"All direct Playwright approaches for CSV option failed: {e}")
                    
            if not clicked:
                raise ValueError("Could not find CSV option")
        
        # Wait for download to complete and save the file
        try:
            print("Waiting for download to complete...")
            download = download_info.value
            print(f"Saving download to: {expected_file_path}")
            download.save_as(expected_file_path)
        except Exception as e:
            print(f"Error saving download: {e}")
            # Look for any downloaded files with similar names in case it was saved automatically
            try:
                print("Looking for automatically downloaded files...")
                import glob
                downloaded_files = glob.glob(str(Path(download_path) / "*.csv"))
                # Sort by modification time, newest first
                downloaded_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                if downloaded_files:
                    newest_file = downloaded_files[0]
                    # Copy to our expected path
                    import shutil
                    shutil.copy2(newest_file, expected_file_path)
                    print(f"Found and copied recent download: {newest_file} -> {expected_file_path}")
                else:
                    raise ValueError("No downloaded CSV files found in target directory")
            except Exception as fallback_error:
                print(f"Fallback file search failed: {fallback_error}")
                raise ValueError(f"Failed to save download: {e}")
                
        print(f"Successfully downloaded results to: {expected_file_path}")
        return str(expected_file_path)
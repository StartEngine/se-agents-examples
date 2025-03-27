import os
import time
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from app.browser_agent.local_playwright import LocalPlaywrightBrowser
from app.memory.selector_memory import SelectorMemory

load_dotenv(override=True)
logger = logging.getLogger(__name__)

class MetabaseAgent:
    """Agent for interacting with Metabase to run SQL queries and download results."""
    
    # Default selectors for common elements - verified with Playwright recordings
    DEFAULT_SELECTORS = {
        "login_page": {
            "username_field": "input[name='username'], input[type='email'], input[placeholder='Email address']",
            "password_field": "input[name='password'], input[type='password'], input[placeholder='Password']", 
            "login_button": "button[type='submit'], button:contains('Sign in')"
        },
        "nav": {
            "new_button": "button:contains('New'), button[name='New'], .Icon-add",
            "question_option": "a:contains('Question'), .List-item:contains('Question')"
        },
        "new_question_menu": {
            "sql_option": "a[role='link'][name='sql icon SQL query']"
        },
        "question_page": {
            "database_selector": "[data-testid='gui-builder-data'] a, .List-section-header, .QueryBuilder-section button",
            "database_search": "[data-testid='list-search-field'], input[type='search'], input:placeholder('Find a database')",
            "database_option": "heading:contains('primary_facade'), div:contains('primary_facade')",
            "sql_editor": ".ace_content, .ace_editor", 
            "run_button": "[data-testid='run-button'], button:contains('Run')"
        },
        "results_page": {
            "download_button": "[data-testid='download-button'], button:contains('Download')",
            "csv_option": "[data-testid='download-results-button'], a:contains('CSV'), div:contains('CSV')"
        }
    }
    
    def __init__(self, 
                headless: bool = False, 
                metabase_url: str = "https://metabase.startengine.com",
                username: Optional[str] = None,
                password: Optional[str] = None,
                cache_dir: str = "./cache"):
        """Initialize the Metabase agent.
        
        Args:
            headless: Whether to run the browser in headless mode
            metabase_url: URL of the Metabase instance
            username: Metabase username (if None, reads from METABASE_USERNAME env var)
            password: Metabase password (if None, reads from METABASE_PASSWORD env var)
            cache_dir: Directory for caching memory
        """
        self.headless = headless
        self.metabase_url = metabase_url
        self.username = username or os.getenv("METABASE_USERNAME")
        self.password = password or os.getenv("METABASE_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("Metabase credentials are required. Set them in .env file or pass them to the constructor.")
            
        # Initialize selector memory
        self.memory = SelectorMemory("metabase", cache_dir)
        
    @staticmethod
    def create_recording(output_file: str, url: str = "https://metabase.startengine.com"):
        """Generate a recording of Metabase interactions using Playwright codegen.
        
        This utility helps gather accurate selectors for the Metabase UI.
        
        Args:
            output_file: Path where the generated Python code will be saved
            url: URL of the Metabase instance to record interactions with
            
        Usage:
            MetabaseAgent.create_recording("metabase_recording.py")
            # Then perform your interactions in the browser window that opens
        """
        import subprocess
        import sys
        
        try:
            subprocess.run([
                sys.executable, "-m", "playwright", "codegen",
                "--target", "python", 
                "-o", output_file,
                url
            ], check=True)
            print(f"Recording saved to {output_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error running Playwright codegen: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        
    def run_query_and_download(self, sql_query: str, database: str = "primary_facade", 
                             download_path: Optional[str] = None) -> str:
        """Run a SQL query in Metabase and download the results.
        
        Args:
            sql_query: The SQL query to run
            database: The database to query
            download_path: Path where to save the CSV (defaults to current dir)
            
        Returns:
            Path to the downloaded CSV file
        """
        if download_path is None:
            download_path = str(Path.cwd())
        
        with LocalPlaywrightBrowser(headless=self.headless) as browser:
            # Navigate to Metabase
            browser.goto(self.metabase_url)
            browser.wait(5000)  # Wait longer for page to load
            
            # Check if we need to log in
            self._handle_login(browser)
            
            # Navigate to new query interface
            self._create_new_question(browser)
            
            # Select database
            self._select_database(browser, database)
            
            # Enter and run query
            self._run_query(browser, sql_query)
            
            # Download results
            file_path = self._download_results(browser, download_path)
            
            return file_path
            
    def _get_selector(self, page: str, element: str) -> str:
        """Get a selector from memory or fall back to default.
        
        Args:
            page: The logical page name
            element: The name of the UI element
            
        Returns:
            CSS selector string for the element
        """
        # Try to get from memory first
        selector = self.memory.get_selector(page, element)
        
        # Fall back to default if needed
        if not selector and page in self.DEFAULT_SELECTORS and element in self.DEFAULT_SELECTORS[page]:
            # Get the default selector
            selector = self.DEFAULT_SELECTORS[page][element]
            
            # Support Playwright selectors format
            if selector.startswith("role="):
                # Convert role=button[name='Sign in'] to a locator selector
                logger.info(f"Using role-based selector: {selector}")
            elif selector.startswith("data-testid="):
                # Convert data-testid=download-button to [data-testid='download-button']
                parts = selector.split("=", 1)
                if len(parts) > 1:
                    attr, value = parts
                    if ">>" in value:
                        # Handle nested selectors like data-testid=gui-builder-data >> a
                        main_part, sub_part = value.split(">>", 1)
                        selector = f"[{attr}='{main_part.strip()}'] {sub_part.strip()}"
                    else:
                        selector = f"[{attr}='{value}']"
                    logger.info(f"Converted data-testid selector to: {selector}")
            
        # If still no selector, log a warning
        if not selector:
            logger.warning(f"No selector found for {page}.{element}")
            
        return selector
        
    def _try_click_selector(self, browser, page: str, element: str) -> bool:
        """Attempt to click an element using selector from memory or defaults.
        
        Updates memory with success or failure.
        
        Args:
            browser: Browser instance
            page: Logical page name
            element: Element name
            
        Returns:
            True if successful, False otherwise
        """
        selector = self._get_selector(page, element)
        if not selector:
            return False
            
        # For selectors with multiple options (comma-separated)
        selector_options = [s.strip() for s in selector.split(',')]
        logger.info(f"Trying to click {page}.{element} with selectors: {selector_options}")
        
        for specific_selector in selector_options:
            try:
                # First wait for the selector to appear
                if browser.wait_for_selector(specific_selector, timeout=2000):
                    # Debug information
                    element_info = browser.get_element_info(specific_selector)
                    if element_info:
                        logger.info(f"Found element: {specific_selector}, visible: {element_info.get('isVisible', False)}")
                    
                    # Try to click it
                    browser.click_selector(specific_selector)
                    browser.wait(1000)  # Longer wait after click
                    
                    # Update memory with successful click
                    self.memory.update_selector(page, element, specific_selector, success=True)
                    logger.info(f"Successfully clicked {page}.{element} with selector: {specific_selector}")
                    return True
            except Exception as e:
                logger.warning(f"Failed to click {page}.{element} with selector {specific_selector}: {e}")
                continue
        
        # If we get here, none of the selectors worked
        logger.warning(f"All selectors failed for {page}.{element}")
        self.memory.update_selector(page, element, selector, success=False)
        return False
    
    def _handle_login(self, browser):
        """Handle Metabase login if needed using Playwright selectors."""
        # Check if we're already logged in by looking for the New button
        try:
            new_button = self._get_selector("nav", "new_button")
            if browser.wait_for_selector(new_button, timeout=3000):
                logger.info("Already logged in, skipping login")
                return
        except Exception:
            # If we can't find the New button, assume we need to log in
            pass
        
        logger.info("Login form detected, attempting to log in")
        
        try:
            # Step 1: Click and fill email field
            username_selector = self._get_selector("login_page", "username_field")
            if not username_selector:
                logger.warning("No username field selector found")
                return
                
            logger.info(f"Clicking username field: {username_selector}")
            if not browser.wait_for_selector(username_selector, timeout=5000):
                logger.warning("Username field not found")
                return
                
            browser.click_selector(username_selector)
            browser.wait(500)
            browser.type(self.username)
            logger.info("Entered username")
            
            # Step 2: Tab to password field or click it directly
            browser.keypress(["Tab"])  # This matches the recording behavior
            browser.wait(200)
            
            # If Tab didn't work, try clicking directly
            password_selector = self._get_selector("login_page", "password_field")
            if password_selector:
                if browser.wait_for_selector(password_selector, timeout=2000):
                    browser.click_selector(password_selector)
                    browser.wait(200)
            
            # Step 3: Enter password
            browser.type(self.password)
            browser.wait(500)
            logger.info("Entered password")
            
            # Step 4: Click login button
            login_selector = self._get_selector("login_page", "login_button")
            if not login_selector:
                logger.warning("No login button selector found")
                browser.keypress(["Enter"])
                browser.wait(5000)
                return
                
            logger.info(f"Clicking login button: {login_selector}")
            if not browser.wait_for_selector(login_selector, timeout=3000):
                logger.warning("Login button not found, trying Enter key")
                browser.keypress(["Enter"])
                browser.wait(5000)
                return
                
            browser.click_selector(login_selector)
            logger.info("Clicked login button")
            
            # Wait for login to complete
            browser.wait(5000)
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            # Try pressing Enter as a fallback
            try:
                browser.keypress(["Enter"])
                browser.wait(5000)
            except Exception:
                pass
    
    def _create_new_question(self, browser):
        """Create a new SQL query using code from Playwright recording."""
        logger.info("Creating new SQL query")
        
        try:
            # Using direct translation from the Playwright recording
            # Step 1: Check if we need to go back to homepage
            current_url = browser.get_current_url()
            if not current_url.endswith("/"):
                logger.info("Navigating to home page.")
                browser.goto(self.metabase_url)
                browser.wait(5000)
            
            # Step 2: Wait for and click the New button (just like in recording)
            try:
                browser._page.get_by_role("button", name="New").click()
                logger.info("Clicked New button using get_by_role")
            except Exception as e:
                logger.warning(f"Role-based New button not found: {e}")
                # Fall back to regular selectors
                selectors = ["button:contains('New')", ".Icon-add", "button[data-testid='new-button']"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=3000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find New button")
                    return False
            
            browser.wait(1000)
            
            # Step 3: Click the SQL query option directly (just like in recording)
            try:
                browser._page.get_by_role("link", name="sql icon SQL query").click()
                logger.info("Clicked SQL query option using get_by_role")
            except Exception as e:
                logger.warning(f"Role-based SQL query option not found: {e}")
                # Fall back to regular selectors
                selectors = ["a:contains('SQL query')", "a:contains('SQL')", "a[href*='/question#']"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=3000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find SQL query option")
                    return False
            
            # Wait for page to load
            browser.wait(5000)
            logger.info("SQL query option clicked successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating new SQL query: {e}")
            return False
    
    def _select_database(self, browser, database_name):
        """Select the specified database using direct Playwright code."""
        logger.info(f"Selecting database: {database_name}")
        
        try:
            # Using direct translation from the Playwright recording
            
            # Step 1: Click the database selector dropdown
            try:
                browser._page.get_by_test_id("gui-builder-data").locator("a").click()
                logger.info("Clicked database selector using get_by_test_id")
            except Exception as e:
                logger.warning(f"Database selector click failed: {e}")
                # Fallback to traditional selectors
                selectors = ["[data-testid='gui-builder-data'] a", ".List-section-header", ".QueryBuilder-section button"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=3000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find database selector")
                    return
            
            browser.wait(1000)
            
            # Step 2: Search for the primary_facade database
            try:
                browser._page.get_by_test_id("list-search-field").fill(database_name)
                logger.info("Entered database name in search field")
            except Exception as e:
                logger.warning(f"Database search field error: {e}")
                # Fallback
                if browser.wait_for_selector("[data-testid='list-search-field']", timeout=3000):
                    browser.click_selector("[data-testid='list-search-field']")
                    browser.wait(500)
                    browser.type(database_name)
                else:
                    logger.error("Could not find database search field")
            
            browser.wait(1000)
            
            # Either press Enter or click on the option
            try:
                browser.keypress(["Enter"])
                browser.wait(1000)
            except Exception:
                pass
                
            # Step 3: Click on the database option
            try:
                browser._page.get_by_role("heading", name="primary_facade").click()
                logger.info("Selected database using get_by_role")
            except Exception as e:
                logger.warning(f"Database option click failed: {e}")
                # Fallback
                selectors = [f"heading[name='{database_name}']", f"div:contains('{database_name}')"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=3000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error(f"Could not find option for database: {database_name}")
                    return
            
            browser.wait(1000)
            logger.info(f"Successfully selected database: {database_name}")
            
        except Exception as e:
            logger.error(f"Error selecting database: {e}")
    
    def _run_query(self, browser, sql_query):
        """Enter and run the SQL query using direct Playwright code."""
        logger.info("Running SQL query")
        
        try:
            # Using direct translation from the Playwright recording
            
            # Step 1: Click the SQL editor area
            try:
                browser._page.locator(".ace_content").click()
                logger.info("Clicked SQL editor using direct locator")
            except Exception as e:
                logger.warning(f"SQL editor click failed: {e}")
                # Fallback
                selectors = [".ace_content", ".ace_editor"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=3000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find SQL editor")
                    return
            
            browser.wait(500)
            
            # Step 2: Enter the SQL query
            try:
                # Clear existing content first
                browser.keypress(["Control", "a"])
                browser.wait(200)
                browser.keypress(["Delete"])
                browser.wait(200)
                
                # Type the query with extra newlines at the end like in the recording
                browser._page.get_by_role("textbox").fill(sql_query + "\n\n")
                logger.info("Entered SQL query using get_by_role")
            except Exception as e:
                logger.warning(f"SQL query input failed: {e}")
                # Fallback
                browser.type(sql_query + "\n\n")
            
            browser.wait(1000)
            
            # Step 3: Click the Run button
            try:
                browser._page.get_by_test_id("native-query-editor-sidebar").get_by_test_id("run-button").click()
                logger.info("Clicked Run button using get_by_test_id")
            except Exception as e:
                logger.warning(f"Run button click failed: {e}")
                # Fallback
                selectors = ["[data-testid='run-button']", "button:contains('Run')"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=3000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find Run button")
                    return
            
            # Wait for query execution
            browser.wait(8000)
            logger.info("Query executed successfully")
            
        except Exception as e:
            logger.error(f"Error running query: {e}")
    
    def _download_results(self, browser, download_path):
        """Download the query results as CSV using direct Playwright code."""
        logger.info("Downloading query results")
        
        try:
            # Using direct translation from the Playwright recording
            
            # Step 1: Click the download button
            try:
                browser._page.get_by_test_id("download-button").click()
                logger.info("Clicked download button using get_by_test_id")
            except Exception as e:
                logger.warning(f"Download button click failed: {e}")
                # Fallback
                selectors = ["[data-testid='download-button']", "button:contains('Download')"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=5000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find download button")
                    return
            
            browser.wait(1000)
            
            # Step 2: Click the download results (CSV) button
            try:
                browser._page.get_by_test_id("download-results-button").click()
                logger.info("Clicked CSV option using get_by_test_id")
            except Exception as e:
                logger.warning(f"CSV option click failed: {e}")
                # Fallback
                selectors = ["[data-testid='download-results-button']", "a:contains('CSV')"]
                clicked = False
                for selector in selectors:
                    if browser.wait_for_selector(selector, timeout=3000):
                        browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find CSV option")
                    return
            
            # Wait for download to complete
            browser.wait(8000)
            logger.info("Download initiated successfully")
            
        except Exception as e:
            logger.error(f"Error downloading results: {e}")
        
        # Create path for downloaded file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        expected_file_path = Path(download_path) / f"metabase_query_result_{timestamp}.csv"
        
        return str(expected_file_path)
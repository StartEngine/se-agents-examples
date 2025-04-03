"""
Metabase session management for browser automation.

This class provides a persistent browser session for running multiple Metabase queries
without having to log in for each query.
"""

import os
import time
import base64
import logging
from pathlib import Path

import sys
# Ensure access to the root directory modules
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from app.browser_agent.local_playwright import LocalPlaywrightBrowser

# Set up a simple logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PersistentMetabaseSession:
    """A class that maintains a persistent browser session with Metabase."""
    
    # Default selectors for common Metabase elements - copied from MetabaseAgent
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
    
    def __init__(self, headless=False, metabase_url="https://metabase.startengine.com"):
        """Initialize the Metabase session.
        
        Args:
            headless: Whether to run browser in headless mode
            metabase_url: URL of the Metabase instance
        """
        self.headless = headless
        self.metabase_url = metabase_url
        self.username = os.getenv("METABASE_USERNAME")
        self.password = os.getenv("METABASE_PASSWORD")
        self.browser = None
        
        if not self.username or not self.password:
            raise ValueError("Metabase credentials are required. Set them in creds.env.")
    
    def __enter__(self):
        """Initialize the browser session when entering the context."""
        logger.info(f"Starting persistent browser session (headless: {self.headless})...")
        
        # Create browser instance
        self.browser = LocalPlaywrightBrowser(headless=self.headless)
        self.browser.__enter__()
        
        # Login to Metabase
        self._handle_login()
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Close the browser when exiting the context."""
        if self.browser:
            logger.info("Closing browser session...")
            self.browser.__exit__(exc_type, exc_val, exc_tb)
            self.browser = None
    
    def _get_selector(self, page, element):
        """Get a selector from the DEFAULT_SELECTORS dict."""
        if page in self.DEFAULT_SELECTORS and element in self.DEFAULT_SELECTORS[page]:
            return self.DEFAULT_SELECTORS[page][element]
        return None
    
    def _handle_login(self):
        """Handle Metabase login - copied from MetabaseAgent._handle_login."""
        logger.info(f"Navigating to {self.metabase_url}...")
        self.browser.goto(self.metabase_url)
        self.browser.wait(5000)  # Wait for page to load
        
        # Check if we're already logged in by looking for the New button
        new_button = self._get_selector("nav", "new_button")
        if self.browser.wait_for_selector(new_button, timeout=3000):
            logger.info("Already logged in, skipping login")
            return
        
        logger.info("Login form detected, attempting to log in")
        
        try:
            # Step 1: Click and fill email field
            username_selector = self._get_selector("login_page", "username_field")
            if not username_selector:
                logger.warning("No username field selector found")
                return
                
            logger.info(f"Clicking username field: {username_selector}")
            if not self.browser.wait_for_selector(username_selector, timeout=5000):
                logger.warning("Username field not found")
                return
                
            self.browser.click_selector(username_selector)
            self.browser.wait(500)
            self.browser.type(self.username)
            logger.info("Entered username")
            
            # Step 2: Tab to password field or click it directly
            self.browser.keypress(["Tab"])  # This matches the recording behavior
            self.browser.wait(200)
            
            # If Tab didn't work, try clicking directly
            password_selector = self._get_selector("login_page", "password_field")
            if password_selector:
                if self.browser.wait_for_selector(password_selector, timeout=2000):
                    self.browser.click_selector(password_selector)
                    self.browser.wait(200)
            
            # Step 3: Enter password
            self.browser.type(self.password)
            self.browser.wait(500)
            logger.info("Entered password")
            
            # Step 4: Click login button
            login_selector = self._get_selector("login_page", "login_button")
            if not login_selector:
                logger.warning("No login button selector found")
                self.browser.keypress(["Enter"])
                self.browser.wait(5000)
                return
                
            logger.info(f"Clicking login button: {login_selector}")
            if not self.browser.wait_for_selector(login_selector, timeout=3000):
                logger.warning("Login button not found, trying Enter key")
                self.browser.keypress(["Enter"])
                self.browser.wait(5000)
                return
                
            self.browser.click_selector(login_selector)
            logger.info("Clicked login button")
            
            # Wait for login to complete
            self.browser.wait(5000)
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            # Try pressing Enter as a fallback
            try:
                self.browser.keypress(["Enter"])
                self.browser.wait(5000)
            except Exception:
                pass
    
    def run_query(self, sql_query, database="primary_facade", download_path=None):
        """Run a SQL query and download the results.
        
        Args:
            sql_query: The SQL query to run
            database: The database to query
            download_path: Path to save the results to
            
        Returns:
            str: Path to the downloaded CSV file
        """
        if not self.browser:
            raise ValueError("Browser session not initialized. Use with context manager.")
        
        if download_path is None:
            download_path = str(Path.cwd())
        elif isinstance(download_path, Path):
            download_path = str(download_path)
        
        logger.info(f"Running query against database '{database}' and saving to '{download_path}'")
        
        # Create a timestamp for the filename
        timestamp = int(time.time())
        expected_file_path = Path(download_path) / f"metabase_query_result_{timestamp}.csv"
        
        # Create empty file as fallback
        with open(expected_file_path, 'w') as f:
            f.write("no_results\n")
        
        try:
            # 1. Create new question
            if not self._create_new_question():
                logger.error("Failed to create new question")
                return str(expected_file_path)
            
            # 2. Select database
            self._select_database(database)
            
            # 3. Run query
            self._run_query(sql_query)
            
            # 4. Download results
            return self._download_results(download_path, expected_file_path)
            
        except Exception as e:
            logger.error(f"Error running query: {e}")
            
            # Take a screenshot for debugging
            try:
                screenshot = self.browser.screenshot()
                screenshot_path = Path(download_path) / f"error_screenshot_{int(time.time())}.png"
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(screenshot))
                logger.info(f"Error screenshot saved to: {screenshot_path}")
            except Exception as screenshot_error:
                logger.error(f"Error taking screenshot: {screenshot_error}")
            
            return str(expected_file_path)
    
    def _create_new_question(self):
        """Create a new SQL query - copied from MetabaseAgent._create_new_question."""
        logger.info("Creating new SQL query")
        
        try:
            # Step 1: Check if we need to go back to homepage
            current_url = self.browser.get_current_url()
            if not current_url.endswith("/"):
                logger.info("Navigating to home page.")
                self.browser.goto(self.metabase_url)
                self.browser.wait(5000)
            
            # Step 2: Wait for and click the New button
            try:
                self.browser._page.get_by_role("button", name="New").click()
                logger.info("Clicked New button using get_by_role")
            except Exception as e:
                logger.warning(f"Role-based New button not found: {e}")
                # Fall back to regular selectors
                selectors = ["button:contains('New')", ".Icon-add", "button[data-testid='new-button']"]
                clicked = False
                for selector in selectors:
                    if self.browser.wait_for_selector(selector, timeout=3000):
                        self.browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find New button")
                    return False
            
            self.browser.wait(1000)
            
            # Step 3: Click the SQL query option
            try:
                self.browser._page.get_by_role("link", name="sql icon SQL query").click()
                logger.info("Clicked SQL query option using get_by_role")
            except Exception as e:
                logger.warning(f"Role-based SQL query option not found: {e}")
                # Fall back to regular selectors
                selectors = ["a:contains('SQL query')", "a:contains('SQL')", "a[href*='/question#']"]
                clicked = False
                for selector in selectors:
                    if self.browser.wait_for_selector(selector, timeout=3000):
                        self.browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find SQL query option")
                    return False
            
            # Wait for page to load
            self.browser.wait(5000)
            logger.info("SQL query option clicked successfully")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating new SQL query: {e}")
            return False
    
    def _select_database(self, database_name):
        """Select the database to query - copied from MetabaseAgent._select_database."""
        logger.info(f"Selecting database: {database_name}")
        
        try:
            # Step 1: Click the database selector dropdown
            try:
                self.browser._page.get_by_test_id("gui-builder-data").locator("a").click()
                logger.info("Clicked database selector using get_by_test_id")
            except Exception as e:
                logger.warning(f"Database selector click failed: {e}")
                # Fallback to traditional selectors
                selectors = ["[data-testid='gui-builder-data'] a", ".List-section-header", ".QueryBuilder-section button"]
                clicked = False
                for selector in selectors:
                    if self.browser.wait_for_selector(selector, timeout=3000):
                        self.browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find database selector")
                    return
            
            self.browser.wait(1000)
            
            # Step 2: Search for the database
            try:
                self.browser._page.get_by_test_id("list-search-field").fill(database_name)
                logger.info("Entered database name in search field")
            except Exception as e:
                logger.warning(f"Database search field error: {e}")
                # Fallback
                if self.browser.wait_for_selector("[data-testid='list-search-field']", timeout=3000):
                    self.browser.click_selector("[data-testid='list-search-field']")
                    self.browser.wait(500)
                    self.browser.type(database_name)
                else:
                    logger.error("Could not find database search field")
            
            self.browser.wait(1000)
            
            # Either press Enter or click on the option
            try:
                self.browser.keypress(["Enter"])
                self.browser.wait(1000)
            except Exception:
                pass
                
            # Step 3: Click on the database option
            try:
                # Try with dynamic name
                self.browser._page.get_by_role("heading", name=database_name).click()
                logger.info("Selected database using get_by_role")
            except Exception as e:
                logger.warning(f"Database option click failed: {e}")
                # Fallback
                selectors = [f"heading[name='{database_name}']", f"div:contains('{database_name}')"]
                clicked = False
                for selector in selectors:
                    if self.browser.wait_for_selector(selector, timeout=3000):
                        self.browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error(f"Could not find option for database: {database_name}")
                    return
            
            self.browser.wait(1000)
            logger.info(f"Successfully selected database: {database_name}")
            
        except Exception as e:
            logger.error(f"Error selecting database: {e}")
    
    def _run_query(self, sql_query):
        """Enter and run the SQL query - copied from MetabaseAgent._run_query."""
        logger.info("Running SQL query")
        
        try:
            # Step 1: Click the SQL editor area
            try:
                self.browser._page.locator(".ace_content").click()
                logger.info("Clicked SQL editor using direct locator")
            except Exception as e:
                logger.warning(f"SQL editor click failed: {e}")
                # Fallback
                selectors = [".ace_content", ".ace_editor"]
                clicked = False
                for selector in selectors:
                    if self.browser.wait_for_selector(selector, timeout=3000):
                        self.browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find SQL editor")
                    return
            
            self.browser.wait(500)
            
            # Step 2: Enter the SQL query
            try:
                # Clear existing content first
                self.browser.keypress(["Control", "a"])
                self.browser.wait(200)
                self.browser.keypress(["Delete"])
                self.browser.wait(200)
                
                # Type the query with extra newlines at the end like in the recording
                self.browser._page.get_by_role("textbox").fill(sql_query + "\n\n")
                logger.info("Entered SQL query using get_by_role")
            except Exception as e:
                logger.warning(f"SQL query input failed: {e}")
                # Fallback
                self.browser.type(sql_query + "\n\n")
            
            self.browser.wait(1000)
            
            # Step 3: Click the Run button
            try:
                self.browser._page.get_by_test_id("native-query-editor-sidebar").get_by_test_id("run-button").click()
                logger.info("Clicked Run button using get_by_test_id")
            except Exception as e:
                logger.warning(f"Run button click failed: {e}")
                # Fallback
                selectors = ["[data-testid='run-button']", "button:contains('Run')", "button.RunButton"]
                clicked = False
                for selector in selectors:
                    if self.browser.wait_for_selector(selector, timeout=3000):
                        self.browser.click_selector(selector)
                        clicked = True
                        break
                if not clicked:
                    logger.error("Could not find Run button, trying keyboard shortcut")
                    try:
                        self.browser.keypress(["Control", "Enter"])
                        clicked = True
                    except Exception as shortcut_error:
                        logger.error(f"Keyboard shortcut failed: {shortcut_error}")
                        
                if not clicked:
                    logger.error("Could not find Run button")
                    return
            
            # Wait for query execution
            self.browser.wait(8000)
            logger.info("Query executed successfully")
            
        except Exception as e:
            logger.error(f"Error running query: {e}")
    
    def _download_results(self, download_path, fallback_path):
        """Download the query results as CSV - copied from MetabaseAgent._download_results."""
        logger.info("Downloading query results")
        
        try:
            # Make sure download directory exists
            Path(download_path).mkdir(exist_ok=True)
            
            # Create a flag for tracking if download has started
            download_started = False
            
            # Set up download listener before clicking download button
            with self.browser._page.expect_download(timeout=15000) as download_info:
                # Step 1: Click the download button
                try:
                    self.browser._page.get_by_test_id("download-button").click()
                    logger.info("Clicked download button using get_by_test_id")
                    download_started = True
                except Exception as e:
                    logger.warning(f"Download button click failed: {e}")
                    # Fallback
                    selectors = ["[data-testid='download-button']", "button:contains('Download')", ".Icon-download"]
                    clicked = False
                    for selector in selectors:
                        if self.browser.wait_for_selector(selector, timeout=5000):
                            self.browser.click_selector(selector)
                            clicked = True
                            download_started = True
                            break
                    if not clicked:
                        logger.error("Could not find download button")
                        return str(fallback_path)
                
                self.browser.wait(1000)
                
                # Step 2: Click the download results (CSV) button
                try:
                    self.browser._page.get_by_test_id("download-results-button").click()
                    logger.info("Clicked CSV option using get_by_test_id")
                    download_started = True
                except Exception as e:
                    logger.warning(f"CSV option click failed: {e}")
                    # Fallback
                    selectors = ["[data-testid='download-results-button']", "a:contains('CSV')", "div:contains('CSV')"]
                    clicked = False
                    for selector in selectors:
                        if self.browser.wait_for_selector(selector, timeout=3000):
                            self.browser.click_selector(selector)
                            clicked = True
                            download_started = True
                            break
                    if not clicked:
                        logger.error("Could not find CSV option")
                        return str(fallback_path)
            
            # Get the download object if download started
            if download_started:
                try:
                    download = download_info.value
                    logger.info(f"Download started: {download.suggested_filename}")
                    
                    # Save the file to the specified path
                    download.save_as(fallback_path)
                    logger.info(f"File saved to: {fallback_path}")
                    
                    # Wait for download to complete
                    download_path = download.path()
                    if download_path:
                        logger.info(f"Download completed at browser path: {download_path}")
                    
                    # Return the path where we saved the file
                    return str(fallback_path)
                except Exception as e:
                    logger.error(f"Error handling download: {e}")
            else:
                logger.error("Download was not initiated properly")
            
        except Exception as e:
            logger.error(f"Error downloading results: {e}")
        
        # Return fallback path if we couldn't download the file
        return str(fallback_path)
"""
Example demonstrating how to retrieve top offerings by amount raised using the Metabase agent.

This example shows how to:
1. Initialize the Metabase agent
2. Run a SQL query against the primary facade database through Metabase
3. Process and display the results to console
"""

import os
import sys
import csv
import time
import base64
import tempfile
import traceback
from pathlib import Path
from dotenv import load_dotenv
from app.metabase_agent.metabase import MetabaseAgent
from app.browser_agent.local_playwright import LocalPlaywrightBrowser
import re

# Load environment variables from creds.env
load_dotenv(dotenv_path="creds.env", override=True)

# Define dictionary of queries for Metabase
QUERIES = {
    "top_offerings_by_amount_raised": """
        select sum(i.amount) + sum(i.investor_fee) as amount_raised, o.slug
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.status = 'APPROVED'
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        group by o.slug
        order by amount_raised DESC
        LIMIT {limit}
    """,
    "offering_amount_raised_last_7_days": """
        select sum(i.amount) + sum(i.investor_fee) as amount_raised
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '7 days'
    """,
    "offering_amount_raised_last_30_days": """
        select sum(i.amount) + sum(i.investor_fee) as amount_raised
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '30 days'
    """,
    "offering_number_of_investors": """
        select count(distinct(i.investor_profile_id)) as number_of_investors
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
    """,
    "offering_number_of_investors_last_7_days": """
        select count(distinct(i.investor_profile_id)) as number_of_investors
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '7 days'
    """,
    "offering_number_of_investors_last_30_days": """
        select count(distinct(i.investor_profile_id)) as number_of_investors
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '30 days'
    """
    # Additional queries can be added here in the future
}

def run_metabase_query(session, query, temp_dir):
    """
    Runs a query against Metabase and returns the processed results.
    
    Args:
        session: The PersistentMetabaseSession to use
        query (str): The SQL query to run
        temp_dir (str): The directory to save the results to
        
    Returns:
        list: List of processed results from the query
    """
    # Make sure temp_dir is a string path, not a Path object
    if isinstance(temp_dir, Path):
        temp_dir = str(temp_dir)
        
    try:
        # Initialize the session first (ensure we're logged in)
        session.initialize_session()
        
        # Run the query and download results to temp directory
        csv_file_path = session.run_query(
            sql_query=query,
            database="primary_facade",
            download_path=temp_dir
        )
        
        if not csv_file_path or not Path(csv_file_path).exists():
            print("Error: Failed to download query results.")
            return []
        
        # Process the CSV file
        return process_csv_results(csv_file_path)
        
    except Exception as e:
        print(f"Error running Metabase query: {e}")
        # Try to take a screenshot to help debug the issue
        try:
            if session.browser:
                timestamp = int(time.time())
                screenshot_path = Path(temp_dir) / f"error_screenshot_{timestamp}.png"
                screenshot = session.browser.screenshot()
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(screenshot))
                print(f"Error screenshot saved to: {screenshot_path}")
        except Exception as screenshot_error:
            print(f"Could not take error screenshot: {screenshot_error}")
        return []

def get_offering_data(session, slug, temp_dir, amount_raised=None, amount_raised_formatted=None):
    """
    Get all data for a specific offering by running multiple queries.
    
    Args:
        session: The PersistentMetabaseSession to use
        slug (str): The offering slug to get data for
        temp_dir (str): Temporary directory to store downloads
        amount_raised (float, optional): Already known amount raised
        amount_raised_formatted (str, optional): Formatted amount raised
        
    Returns:
        dict: All data for the offering
    """
    # Initialize with slug and any pre-known amount raised
    offering_data = {'slug': slug}
    if amount_raised is not None:
        offering_data['amount_raised'] = amount_raised
        offering_data['amount_raised_formatted'] = amount_raised_formatted or "${:,.2f}".format(amount_raised)
    
    print(f"Gathering complete data for {slug}...")
    
    try:
        # The issue is with double-quoting in the SQL queries
        # We need to ensure the slug is properly quoted in the SQL
        # For PostgreSQL, string values should be surrounded by single quotes
        quoted_slug = f"'{slug}'"
        
        # 1. Get amount raised in last 7 days
        print(f"  - Getting amount raised in last 7 days...")
        # Format and clean the query for better compatibility
        raw_query = QUERIES["offering_amount_raised_last_7_days"].format(slug=quoted_slug)
        query = clean_sql_query(raw_query)
        print(f"DEBUG - Query being sent: {query}")
        results = run_metabase_query(session, query, temp_dir)
        if results and len(results) > 0:
            amount_raised_7d = results[0].get('amount_raised', 0)
            offering_data['amount_raised_7d'] = amount_raised_7d
            offering_data['amount_raised_7d_formatted'] = "${:,.2f}".format(float(amount_raised_7d) if amount_raised_7d else 0)
        
        # 2. Get amount raised in last 30 days
        print(f"  - Getting amount raised in last 30 days...")
        raw_query = QUERIES["offering_amount_raised_last_30_days"].format(slug=quoted_slug)
        query = clean_sql_query(raw_query)
        print(f"DEBUG - Query being sent: {query}")
        results = run_metabase_query(session, query, temp_dir)
        if results and len(results) > 0:
            amount_raised_30d = results[0].get('amount_raised', 0)
            offering_data['amount_raised_30d'] = amount_raised_30d
            offering_data['amount_raised_30d_formatted'] = "${:,.2f}".format(float(amount_raised_30d) if amount_raised_30d else 0)
        
        # 3. Get total investors
        print(f"  - Getting total investors count...")
        raw_query = QUERIES["offering_number_of_investors"].format(slug=quoted_slug)
        query = clean_sql_query(raw_query)
        print(f"DEBUG - Query being sent: {query}")
        results = run_metabase_query(session, query, temp_dir)
        if results and len(results) > 0:
            investors = results[0].get('number_of_investors', 0)
            offering_data['investors_total'] = investors
        
        # 4. Get investors in last 7 days
        print(f"  - Getting investors count from last 7 days...")
        raw_query = QUERIES["offering_number_of_investors_last_7_days"].format(slug=quoted_slug)
        query = clean_sql_query(raw_query)
        print(f"DEBUG - Query being sent: {query}")
        results = run_metabase_query(session, query, temp_dir)
        if results and len(results) > 0:
            investors_7d = results[0].get('number_of_investors', 0)
            offering_data['investors_7d'] = investors_7d
        
        # 5. Get investors in last 30 days
        print(f"  - Getting investors count from last 30 days...")
        raw_query = QUERIES["offering_number_of_investors_last_30_days"].format(slug=quoted_slug)
        query = clean_sql_query(raw_query)
        print(f"DEBUG - Query being sent: {query}")
        results = run_metabase_query(session, query, temp_dir)
        if results and len(results) > 0:
            investors_30d = results[0].get('number_of_investors', 0)
            offering_data['investors_30d'] = investors_30d
        
        # Print the data we've gathered so far
        print(f"\nData for {slug}:")
        print(f"  Total amount raised: {offering_data.get('amount_raised_formatted', '$0.00')}")
        print(f"  Amount raised (7 days): {offering_data.get('amount_raised_7d_formatted', '$0.00')}")
        print(f"  Amount raised (30 days): {offering_data.get('amount_raised_30d_formatted', '$0.00')}")
        print(f"  Total investors: {offering_data.get('investors_total', 0)}")
        print(f"  Investors (7 days): {offering_data.get('investors_7d', 0)}")
        print(f"  Investors (30 days): {offering_data.get('investors_30d', 0)}")
        print("-" * 80)
        
        return offering_data
        
    except Exception as e:
        print(f"Error getting data for {slug}: {e}")
        return offering_data

def clean_sql_query(query):
    """
    Clean and format a SQL query for better readability and compatibility with Metabase.
    Specifically handles the interval syntax correctly for PostgreSQL.
    
    Args:
        query (str): The raw SQL query
        
    Returns:
        str: Cleaned SQL query
    """
    # Remove extra whitespace
    clean = query.strip()
    
    # Remove leading/trailing newlines
    clean = clean.strip('\n')
    
    # Preserve interval expressions like 'now() - interval '7 days'' by temporarily replacing them
    # This ensures we don't break the interval syntax when formatting
    interval_pattern = r'(now\(\)\s*-\s*interval\s*\'[^\']*\')'
    interval_replacements = {}
    
    for i, match in enumerate(re.finditer(interval_pattern, clean, re.IGNORECASE)):
        placeholder = f"__INTERVAL_PLACEHOLDER_{i}__"
        interval_replacements[placeholder] = match.group(0)
        clean = clean.replace(match.group(0), placeholder)
    
    # Also preserve other special operators like >=, <=, != etc.
    compound_ops = ['>=', '<=', '!=', '<>', '==']
    op_replacements = {}
    
    for i, op in enumerate(compound_ops):
        placeholder = f"__OP_PLACEHOLDER_{i}__"
        op_replacements[placeholder] = op
        clean = clean.replace(op, placeholder)
    
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean)
    
    # Now add spacing around basic operators
    for op in ['=', '<', '>', '+', '-', '*', '/', '%']:
        clean = clean.replace(op, f' {op} ')
    
    # Re-normalize whitespace
    clean = re.sub(r'\s+', ' ', clean)
    
    # Fix double spaces
    while '  ' in clean:
        clean = clean.replace('  ', ' ')
    
    # Put back the compound operators with proper spacing
    for placeholder, op in op_replacements.items():
        # First remove any spaces around the placeholder
        clean = re.sub(f"\\s*{re.escape(placeholder)}\\s*", f" {op} ", clean)
    
    # Properly format interval expressions in a way that works with PostgreSQL
    for placeholder, interval in interval_replacements.items():
        # Format the interval expression with proper spacing
        # First remove the placeholder with its surroundings
        clean = re.sub(f"\\s*{re.escape(placeholder)}\\s*", " " + interval + " ", clean)
    
    # Fix any spacing issues that might have been created
    clean = re.sub(r'\s+', ' ', clean)
    while '  ' in clean:
        clean = clean.replace('  ', ' ')
        
    # Ensure intervals are properly formatted
    # PostgreSQL requires the syntax: INTERVAL '7 days'
    clean = re.sub(r'INTERVAL\s+\'', 'INTERVAL \'', clean)
    
    # Special debugging for interval syntax
    if 'INTERVAL' in clean:
        print("DEBUG - Interval syntax check:")
        interval_matches = re.findall(r'(INTERVAL\s*\'[^\']*\')', clean)
        for i, match in enumerate(interval_matches):
            print(f"  Interval {i+1}: '{match}'")
            # Ensure proper format: INTERVAL '7 days'
            if not re.match(r'INTERVAL\s*\'[^\']+\'', match):
                print(f"  WARNING: Interval {i+1} might have incorrect format")
                # Try to fix it
                fixed = re.sub(r'INTERVAL\s*\'', 'INTERVAL \'', match)
                clean = clean.replace(match, fixed)
                print(f"  Fixed to: '{fixed}'")
        
    # Finally, ensure compound operators are correct
    for op in ['>=', '<=', '<>', '!=']:
        # Fix any broken compound operators like > = or < =
        broken_op = ' '.join(list(op))
        if broken_op in clean:
            print(f"DEBUG - Found broken operator: '{broken_op}'")
            clean = clean.replace(broken_op, op)
            print(f"DEBUG - Fixed to: '{op}'")
    
    # Replace SQL keywords with uppercase for readability
    sql_keywords = [
        'select', 'from', 'where', 'join', 'left join', 'right join', 'inner join',
        'group by', 'order by', 'having', 'limit', 'and', 'or', 'not', 'in', 'between',
        'union', 'insert', 'update', 'delete', 'create', 'alter', 'drop', 'interval'
    ]
    
    for keyword in sql_keywords:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + keyword + r'\b'
        clean = re.sub(pattern, keyword.upper(), clean, flags=re.IGNORECASE)
    
    return clean

class PersistentMetabaseSession:
    """A class that maintains a persistent browser session with Metabase."""
    
    def __init__(self, headless=False, metabase_url="https://metabase.startengine.com"):
        self.headless = headless
        self.metabase_url = metabase_url
        self.username = os.getenv("METABASE_USERNAME")
        self.password = os.getenv("METABASE_PASSWORD")
        self.browser = None
        self.initialized = False
        
        if not self.username or not self.password:
            raise ValueError("Metabase credentials are required. Set them in creds.env.")
    
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
        needs_login = any(self.browser.wait_for_selector(selector, timeout=1000) for selector in login_elements)
        
        if needs_login:
            print("Logging into Metabase...")
            # Find and fill username field
            for selector in login_elements:
                if self.browser.wait_for_selector(selector, timeout=1000):
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
            login_button = "button[type='submit'], button:contains('Sign in')"
            if self.browser.wait_for_selector(login_button, timeout=1000):
                self.browser.click_selector(login_button)
            else:
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
        # Click New button
        selectors = ["button:contains('New')", ".Icon-add", "button[data-testid='new-button']"]
        clicked = False
        for selector in selectors:
            if self.browser.wait_for_selector(selector, timeout=3000):
                self.browser.click_selector(selector)
                clicked = True
                break
        
        if not clicked:
            try:
                # Try using get_by_role
                self.browser._page.get_by_role("button", name="New").click()
                clicked = True
            except:
                pass
                
        if not clicked:
            raise ValueError("Could not find New button")
        
        self.browser.wait(1000)
        
        # Click the SQL query option
        selectors = ["a:contains('SQL query')", "a:contains('SQL')", "a[href*='/question#']"]
        clicked = False
        for selector in selectors:
            if self.browser.wait_for_selector(selector, timeout=3000):
                self.browser.click_selector(selector)
                clicked = True
                break
                
        if not clicked:
            try:
                # Try using get_by_role
                self.browser._page.get_by_role("link", name="sql icon SQL query").click()
                clicked = True
            except:
                pass
                
        if not clicked:
            raise ValueError("Could not find SQL query option")
        
        self.browser.wait(5000)
    
    def _select_database(self, database_name):
        """Select the database to query."""
        # Click database selector
        selectors = ["[data-testid='gui-builder-data'] a", ".List-section-header", ".QueryBuilder-section button"]
        clicked = False
        for selector in selectors:
            if self.browser.wait_for_selector(selector, timeout=3000):
                self.browser.click_selector(selector)
                clicked = True
                break
                
        if not clicked:
            try:
                # Try using get_by_test_id
                self.browser._page.get_by_test_id("gui-builder-data").locator("a").click()
                clicked = True
            except:
                pass
                
        if not clicked:
            raise ValueError("Could not find database selector")
        
        self.browser.wait(1000)
        
        # Search for database
        search_field = "[data-testid='list-search-field']"
        if self.browser.wait_for_selector(search_field, timeout=3000):
            self.browser.click_selector(search_field)
            self.browser.wait(500)
            self.browser.type(database_name)
        else:
            try:
                # Try using get_by_test_id
                self.browser._page.get_by_test_id("list-search-field").fill(database_name)
            except:
                pass
        
        self.browser.wait(1000)
        
        # Press Enter or click on the option
        try:
            self.browser.keypress(["Enter"])
            self.browser.wait(1000)
        except:
            # Click on database option
            selectors = [f"div:contains('{database_name}')", f"heading:contains('{database_name}')"]
            for selector in selectors:
                if self.browser.wait_for_selector(selector, timeout=3000):
                    self.browser.click_selector(selector)
                    break
    
    def _run_query(self, sql_query):
        """Enter and run the SQL query."""
        # Click the SQL editor
        selectors = [".ace_content", ".ace_editor"]
        clicked = False
        for selector in selectors:
            if self.browser.wait_for_selector(selector, timeout=3000):
                self.browser.click_selector(selector)
                clicked = True
                break
                
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
        
        # Click the Run button
        selectors = ["[data-testid='run-button']", "button:contains('Run')"]
        clicked = False
        for selector in selectors:
            if self.browser.wait_for_selector(selector, timeout=3000):
                self.browser.click_selector(selector)
                clicked = True
                break
                
        if not clicked:
            try:
                # Try using get_by_test_id
                self.browser._page.get_by_test_id("native-query-editor-sidebar").get_by_test_id("run-button").click()
                clicked = True
            except Exception as e:
                print(f"Get by test ID failed: {e}")
                # One more attempt with direct page methods
                try:
                    self.browser._page.get_by_role("button", name="Run").click()
                    clicked = True
                except Exception as e:
                    print(f"Get by role failed: {e}")
                
        if not clicked:
            raise ValueError("Could not find Run button")
        
        # Wait for query execution
        self.browser.wait(8000)
    
    def _download_results(self, download_path):
        """Download the query results as CSV."""
        timestamp = int(time.time())
        expected_file_path = Path(download_path) / f"metabase_query_result_{timestamp}.csv"
        
        # Click the download button
        selectors = ["[data-testid='download-button']", "button:contains('Download')"]
        clicked = False
        for selector in selectors:
            if self.browser.wait_for_selector(selector, timeout=5000):
                self.browser.click_selector(selector)
                clicked = True
                break
                
        if not clicked:
            try:
                # Try using get_by_test_id
                self.browser._page.get_by_test_id("download-button").click()
                clicked = True
            except:
                pass
                
        if not clicked:
            raise ValueError("Could not find download button")
        
        self.browser.wait(1000)
        
        # Click the CSV option
        with self.browser._page.expect_download() as download_info:
            selectors = ["[data-testid='download-results-button']", "a:contains('CSV')"]
            clicked = False
            for selector in selectors:
                if self.browser.wait_for_selector(selector, timeout=3000):
                    self.browser.click_selector(selector)
                    clicked = True
                    break
                    
            if not clicked:
                try:
                    # Try using get_by_test_id
                    self.browser._page.get_by_test_id("download-results-button").click()
                    clicked = True
                except:
                    pass
                    
            if not clicked:
                raise ValueError("Could not find CSV option")
        
        # Wait for download to complete and save the file
        download = download_info.value
        download.save_as(expected_file_path)
        
        return str(expected_file_path)

def process_csv_results(csv_file_path):
    """
    Process the CSV file downloaded from Metabase.
    
    Args:
        csv_file_path (str): Path to the CSV file
        
    Returns:
        list: List of dictionaries containing query results
    """
    results = []
    file_name = os.path.basename(csv_file_path)
    file_size = os.path.getsize(csv_file_path) / 1024  # Size in KB
    
    print(f"Processing Metabase CSV file: {file_name} ({file_size:.2f} KB)")
    
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Read the content for feedback
            content = csvfile.read()
            line_count = content.count('\n') + 1
            print(f"  - CSV contains {line_count} lines (including header)")
            csvfile.seek(0)  # Reset file pointer to beginning
            
            # Create the CSV reader
            reader = csv.DictReader(csvfile)
            
            # Get columns for feedback
            columns = reader.fieldnames
            print(f"  - CSV columns: {', '.join(columns)}")
            
            row_count = 0
            for row in reader:
                row_count += 1
                # Copy the row so we can modify it
                processed_row = {}
                
                # Process each column
                for col, value in row.items():
                    # Skip empty or None values
                    if not value or value == 'null':
                        processed_row[col] = None
                        continue
                    
                    # Try to convert to float if the column looks like a number
                    if col.lower() in ('amount_raised', 'amount', 'number_of_investors') or 'count' in col.lower():
                        # Remove commas from numbers
                        clean_value = value.replace(',', '')
                        try:
                            processed_row[col] = float(clean_value)
                            # For amount columns, also add formatted version
                            if 'amount' in col.lower() or 'raised' in col.lower():
                                processed_row[f"{col}_formatted"] = "${:,.2f}".format(float(clean_value))
                        except ValueError:
                            # If not a number, keep as string
                            processed_row[col] = value
                            print(f"Warning: Could not convert '{value}' to a number for column '{col}'")
                    else:
                        # Keep non-numeric values as strings
                        processed_row[col] = value
                
                results.append(processed_row)
            
            print(f"  - Processed {row_count} rows from {file_name}")
            return results
    
    except Exception as e:
        print(f"Error processing CSV results: {e}")
        return []

def print_offering_data(offerings_dict):
    """
    Print offering data from a dictionary.
    
    Args:
        offerings_dict: Dictionary with slugs as keys and offering data as values
    """
    if not offerings_dict:
        print("\nNo results found.")
        return
    
    # Calculate and store total amount
    total_amount = sum(data.get('amount_raised', 0) for data in offerings_dict.values())
    
    # Print header
    print(f"\nTop {len(offerings_dict)} Offerings by Amount Raised:")
    print("-" * 100)
    
    # Sort by amount raised (descending) and print
    sorted_slugs = sorted(
        offerings_dict.keys(), 
        key=lambda slug: offerings_dict[slug].get('amount_raised', 0), 
        reverse=True
    )
    
    # Print each offering with all available details
    for i, slug in enumerate(sorted_slugs, 1):
        data = offerings_dict[slug]
        print(f"{i}. {slug}")
        
        # Print all available data for this offering
        if 'amount_raised' in data:
            print(f"   Total Amount Raised: {data.get('amount_raised_formatted', '$0.00')}")
        
        # 7-day metrics
        if 'amount_raised_7d' in data:
            print(f"   Amount Raised (7 days): {data.get('amount_raised_7d_formatted', '$0.00')}")
        if 'investors_7d' in data:
            print(f"   Investors (7 days): {int(data.get('investors_7d', 0))}")
            
        # 30-day metrics
        if 'amount_raised_30d' in data:
            print(f"   Amount Raised (30 days): {data.get('amount_raised_30d_formatted', '$0.00')}")
        if 'investors_30d' in data:
            print(f"   Investors (30 days): {int(data.get('investors_30d', 0))}")
            
        # Total investors
        if 'investors_total' in data:
            print(f"   Total Investors: {int(data.get('investors_total', 0))}")
            
        print("-" * 100)
    
    # Print summary statistics
    print(f"\nSummary:")
    print(f"  Total Amount Raised Across All Offerings: ${total_amount:,.2f}")
    print(f"  Average Raise per Offering: ${total_amount/len(offerings_dict):,.2f}")

if __name__ == "__main__":
    # Get command line arguments
    limit = 10
    headless = False
    
    # Parse limit argument
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Invalid limit value: {sys.argv[1]}. Using default limit of 10.")
    
    # Parse headless argument (if provided)
    if len(sys.argv) > 2:
        headless_arg = sys.argv[2].lower()
        if headless_arg in ('true', 't', 'yes', 'y', '1'):
            headless = True
    
    # Check if Metabase credentials are set
    if not os.getenv("METABASE_USERNAME") or not os.getenv("METABASE_PASSWORD"):
        print("Error: Metabase credentials are not set.")
        print("Please ensure the following environment variables are set in creds.env:")
        print("  - METABASE_USERNAME")
        print("  - METABASE_PASSWORD")
        sys.exit(1)
    
    try:
        # Create a temporary directory for all downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a single persistent Metabase session
            with PersistentMetabaseSession(headless=headless) as session:
                # First, get the list of top offerings with their amount raised
                print("\nFetching top offerings by amount raised...")
                raw_query = QUERIES["top_offerings_by_amount_raised"].format(limit=limit)
                query = clean_sql_query(raw_query)
                print(f"DEBUG - Query being sent: {query}")
                top_offerings_with_data = run_metabase_query(session, query, temp_dir)
                
                if not top_offerings_with_data:
                    print("No offerings found. Check your query and try again.")
                    sys.exit(1)
                
                # Extract the slugs and create a map of slug to amount raised
                top_slugs = []
                slug_to_amount = {}
                
                for offering in top_offerings_with_data:
                    slug = offering.get('slug')
                    if slug:
                        top_slugs.append(slug)
                        slug_to_amount[slug] = {
                            'amount_raised': offering.get('amount_raised', 0),
                            'amount_raised_formatted': offering.get('amount_raised_formatted', '$0.00')
                        }
                
                print(f"Found {len(top_slugs)} top offerings: {', '.join(top_slugs)}")
                
                # Initialize a dictionary to store all offering data
                all_offerings_data = {}
                
                # Process each slug one by one, gathering all data before moving to the next
                print("\nRetrieving detailed data for each offering...")
                
                # Now process each offering with the known amount_raised
                for i, slug in enumerate(top_slugs, 1):
                    print(f"\n[{i}/{len(top_slugs)}] Processing offering: {slug}")
                    
                    # Get the pre-known amount raised
                    amount_data = slug_to_amount.get(slug, {})
                    amount_raised = amount_data.get('amount_raised')
                    amount_raised_formatted = amount_data.get('amount_raised_formatted')
                    
                    # Get all detailed data for this offering
                    offering_data = get_offering_data(
                        session, 
                        slug, 
                        temp_dir,
                        amount_raised=amount_raised,
                        amount_raised_formatted=amount_raised_formatted
                    )
                    
                    # Store the complete data for this offering
                    all_offerings_data[slug] = offering_data
            
            # After all offerings have been processed, print a final summary
            total_amount = sum(data.get('amount_raised', 0) for data in all_offerings_data.values())
            print("\n" + "=" * 100)
            print(f"SUMMARY OF TOP {len(all_offerings_data)} OFFERINGS")
            print("=" * 100)
            print(f"Total amount raised across all offerings: ${total_amount:,.2f}")
            if all_offerings_data:
                print(f"Average raised per offering: ${total_amount/len(all_offerings_data):,.2f}")
            
            # List offerings sorted by amount raised
            print("\nOfferings by amount raised (high to low):")
            sorted_slugs = sorted(
                all_offerings_data.keys(),
                key=lambda s: all_offerings_data[s].get('amount_raised', 0),
                reverse=True
            )
            
            for i, slug in enumerate(sorted_slugs, 1):
                data = all_offerings_data[slug]
                print(f"{i}. {slug}: {data.get('amount_raised_formatted', '$0.00')}")
                
    except Exception as e:
        print(f"Error running script: {e}")
        print("Full error details:")
        traceback.print_exc()
    
    print("\nUsage:")
    print("  python -m examples.top_issuers_example [limit] [headless]")
    print("  - limit: Number of offerings to retrieve (default: 10)")
    print("  - headless: Run without browser UI (true/false, default: false)")
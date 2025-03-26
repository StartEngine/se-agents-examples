import os
import time
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from app.browser_agent.local_playwright import LocalPlaywrightComputer

load_dotenv(override=True)

class MetabaseAgent:
    """Agent for interacting with Metabase to run SQL queries and download results."""
    
    def __init__(self, 
                headless: bool = False, 
                metabase_url: str = "https://metabase.startengine.com",
                username: Optional[str] = None,
                password: Optional[str] = None):
        """Initialize the Metabase agent.
        
        Args:
            headless: Whether to run the browser in headless mode
            metabase_url: URL of the Metabase instance
            username: Metabase username (if None, reads from METABASE_USERNAME env var)
            password: Metabase password (if None, reads from METABASE_PASSWORD env var)
        """
        self.headless = headless
        self.metabase_url = metabase_url
        self.username = username or os.getenv("METABASE_USERNAME")
        self.password = password or os.getenv("METABASE_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("Metabase credentials are required. Set them in .env file or pass them to the constructor.")
    
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
        
        with LocalPlaywrightComputer(headless=self.headless) as computer:
            # Navigate to Metabase
            computer.goto(self.metabase_url)
            computer.wait(2000)  # Wait for page to load
            
            # Check if we need to log in
            self._handle_login(computer)
            
            # Navigate to new query interface
            self._create_new_question(computer)
            
            # Select database
            self._select_database(computer, database)
            
            # Enter and run query
            self._run_query(computer, sql_query)
            
            # Download results
            file_path = self._download_results(computer, download_path)
            
            return file_path
    
    def _handle_login(self, computer):
        """Handle Metabase login if needed."""
        # Check if login form is visible
        # This is a simplified approach; in a real implementation, we'd check for login elements
        # For now, we'll assume if we see a login form, we need to log in
        
        # Take a screenshot to see the current state
        screenshot = computer.screenshot()
        
        # Simple approach: Try to find and click on username field (coordinates will need adjustment)
        try:
            # Click on username field (adjust coordinates as needed)
            computer.click(400, 300)  # Approximate coordinates for username field
            computer.wait(500)
            
            # Type username
            computer.type(self.username)
            computer.wait(500)
            
            # Tab to password field
            computer.keypress(["Tab"])
            computer.wait(500)
            
            # Type password
            computer.type(self.password)
            computer.wait(500)
            
            # Press Enter to submit
            computer.keypress(["Enter"])
            computer.wait(3000)  # Wait for login to complete
        except Exception as e:
            print(f"Login attempt failed or not needed: {e}")
    
    def _create_new_question(self, computer):
        """Navigate to create a new question."""
        # Click on New button
        # Coordinates will need adjustment based on actual UI
        computer.click(100, 100)  # Approximate location of New button
        computer.wait(1000)
        
        # Click on Question option
        computer.click(100, 150)  # Approximate location of Question option
        computer.wait(1000)
        
        # Click on SQL option
        computer.click(500, 300)  # Approximate location of SQL option
        computer.wait(1000)
    
    def _select_database(self, computer, database):
        """Select the specified database."""
        # Click on database selector
        computer.click(200, 100)  # Approximate location of database selector
        computer.wait(1000)
        
        # This is a simplified approach; in reality, we'd need to find and click
        # on the specific database name in the dropdown
        # For now, we'll just simulate clicking where we expect the database to be
        
        # Click on the database name (adjust coordinates as needed)
        computer.click(200, 150)  # Approximate location of database in dropdown
        computer.wait(1000)
    
    def _run_query(self, computer, sql_query):
        """Enter and run the SQL query."""
        # Click in the SQL editor
        computer.click(400, 400)  # Approximate location of SQL editor
        computer.wait(500)
        
        # Select all existing text (Ctrl+A) and delete it
        computer.keypress(["Control", "a"])
        computer.keypress(["Delete"])
        computer.wait(500)
        
        # Type the SQL query
        computer.type(sql_query)
        computer.wait(1000)
        
        # Run the query (usually a button or keyboard shortcut)
        computer.keypress(["Control", "Enter"])  # Common shortcut for Run
        computer.wait(5000)  # Wait for query to complete
    
    def _download_results(self, computer, download_path):
        """Download the query results as CSV."""
        # Click on download button (adjust coordinates as needed)
        computer.click(700, 500)  # Approximate location of download button
        computer.wait(1000)
        
        # Click on CSV option (adjust coordinates as needed)
        computer.click(700, 550)  # Approximate location of CSV option
        computer.wait(3000)  # Wait for download to complete
        
        # In a real implementation, we'd track the downloaded file
        # For this example, we'll assume the file is downloaded to the provided path
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        expected_file_path = Path(download_path) / f"metabase_query_result_{timestamp}.csv"
        
        return str(expected_file_path)
"""JIRA agent for browser automation with JIRA tickets.

This module provides the JiraAgent class for interacting with JIRA:
- Logging in (with various authentication methods)
- Reading ticket information
- Adding comments
- Changing ticket status
- Extracting data for analysis
"""

import os
import json
import time
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from dotenv import load_dotenv
from app.browser_agent.local_playwright import LocalPlaywrightBrowser
from app.memory.selector_memory import SelectorMemory
from app.jira_agent.auth import is_login_page, login
from app.jira_agent.selectors import DEFAULT_SELECTORS, FIELD_SELECTORS

# Conditionally import jira for API mode
try:
    from jira import JIRA
    JIRA_API_AVAILABLE = True
except ImportError:
    JIRA_API_AVAILABLE = False
    logging.warning("JIRA API package not installed. To use API mode, run: pip install jira")

# Load environment variables, first trying .env.local
load_dotenv(dotenv_path=".env.local", override=True)
# If .env.local doesn't exist, fall back to .env
if os.getenv("JIRA_URL") is None and os.path.exists(".env"):
    load_dotenv(dotenv_path=".env", override=True)
logger = logging.getLogger(__name__)


class JiraAgent:
    """Agent for interacting with JIRA to read and manipulate tickets."""
    
    def __init__(self, 
                headless: bool = False, 
                jira_url: str = None,
                username: Optional[str] = None,
                password: Optional[str] = None,
                use_sso: bool = True,
                prefer_google: bool = True,
                cache_dir: str = "./cache",
                mode: str = "browser"):
        """Initialize the JIRA agent.
        
        Args:
            headless: Whether to run the browser in headless mode
            jira_url: URL of the JIRA instance
            username: JIRA username (if None, reads from JIRA_USERNAME env var)
            password: JIRA password (if None, reads from JIRA_PASSWORD env var)
            use_sso: Whether to use SSO for authentication
            prefer_google: Whether to prefer Google SSO if available
            cache_dir: Directory for caching memory
            mode: Interaction mode - 'browser' (Playwright) or 'api' (JIRA API)
        """
        self.headless = headless
        self.jira_url = jira_url or os.getenv("JIRA_URL", "https://mydomain.atlassian.net")
        self.username = username or os.getenv("JIRA_USERNAME")
        self.password = password or os.getenv("JIRA_PASSWORD")
        self.use_sso = use_sso
        self.prefer_google = prefer_google
        self.mode = mode
        
        if not self.username or not self.password:
            raise ValueError("JIRA credentials are required. Set them in .env file or pass them to the constructor.")
            
        # Initialize selector memory
        self.memory = SelectorMemory("jira", cache_dir)
        
    def get_ticket(self, ticket_id: str, extract_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get information about a JIRA ticket.
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            extract_fields: List of additional fields to extract (defaults to common fields)
            
        Returns:
            Dictionary with ticket information
        """
        # Default fields to extract if not specified
        if extract_fields is None:
            extract_fields = ["summary", "description"]
            
        logger.info(f"Getting information for ticket {ticket_id}")
        
        # Initialize with basic info in case of errors
        ticket_info = {
            "id": ticket_id,
            "url": f"{self.jira_url}/browse/{ticket_id}",
        }
        
        # Use different implementation based on mode
        if self.mode == "api":
            return self._get_ticket_api(ticket_id, extract_fields)
        else:
            return self._get_ticket_browser(ticket_id, extract_fields, ticket_info)
    
    def _get_ticket_api(self, ticket_id: str, extract_fields: List[str]) -> Dict[str, Any]:
        """Get ticket information using JIRA API.
        
        Args:
            ticket_id: The JIRA ticket ID
            extract_fields: List of fields to extract
            
        Returns:
            Dictionary with ticket information
        """
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API not available. Install with: pip install jira")
            return {
                "id": ticket_id,
                "url": f"{self.jira_url}/browse/{ticket_id}",
                "error": "JIRA API package not installed. Run: pip install jira"
            }
            
        logger.info(f"Using API mode to get ticket {ticket_id}")
        
        # Initialize with basic info
        ticket_info = {
            "id": ticket_id,
            "url": f"{self.jira_url}/browse/{ticket_id}",
            "mode": "api"
        }
        
        try:
            # Connect to JIRA
            auth_method = None
            
            # Determine authentication method based on URL and credentials
            if self.use_sso:
                logger.warning("SSO not supported in API mode. Using basic auth instead.")
            
            # Use basic auth with username/password or token
            auth = (self.username, self.password)
            
            # Connect to JIRA
            jira = JIRA(
                server=self.jira_url,
                basic_auth=auth
            )
            
            # Get issue
            issue = jira.issue(ticket_id)
            
            # Extract common fields
            if "summary" in extract_fields or not extract_fields:
                ticket_info["summary"] = issue.fields.summary
                
            if "description" in extract_fields or not extract_fields:
                ticket_info["description"] = issue.fields.description or ""
                
            if "status" in extract_fields:
                ticket_info["status"] = issue.fields.status.name
                
            if "assignee" in extract_fields:
                if issue.fields.assignee:
                    ticket_info["assignee"] = issue.fields.assignee.displayName
                else:
                    ticket_info["assignee"] = "Unassigned"
                    
            if "priority" in extract_fields:
                if issue.fields.priority:
                    ticket_info["priority"] = issue.fields.priority.name
                else:
                    ticket_info["priority"] = "None"
                    
            if "type" in extract_fields:
                if issue.fields.issuetype:
                    ticket_info["type"] = issue.fields.issuetype.name
                else:
                    ticket_info["type"] = "Unknown"
                    
            if "reporter" in extract_fields:
                if issue.fields.reporter:
                    ticket_info["reporter"] = issue.fields.reporter.displayName
                else:
                    ticket_info["reporter"] = "Unknown"
                    
            if "created" in extract_fields:
                ticket_info["created"] = issue.fields.created
                
            if "updated" in extract_fields:
                ticket_info["updated"] = issue.fields.updated
                
            if "comments" in extract_fields:
                comments = []
                for comment in issue.fields.comment.comments:
                    comments.append({
                        "author": comment.author.displayName,
                        "text": comment.body,
                        "created": comment.created
                    })
                ticket_info["comments"] = comments
                
            if "labels" in extract_fields:
                ticket_info["labels"] = issue.fields.labels if issue.fields.labels else []
                
            # Extract any custom fields that were requested
            field_map = {field['name'].lower(): field['id'] for field in jira.fields()}
            for field in extract_fields:
                if field not in ticket_info and field.lower() in field_map:
                    field_id = field_map[field.lower()]
                    if hasattr(issue.fields, field_id):
                        value = getattr(issue.fields, field_id)
                        if value is not None:
                            ticket_info[field] = value
                
            return ticket_info
            
        except Exception as e:
            logger.error(f"JIRA API error: {e}")
            ticket_info["error"] = f"JIRA API error: {str(e)}"
            return ticket_info
            
    def _get_ticket_browser(self, ticket_id: str, extract_fields: List[str], ticket_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get ticket information using browser automation.
        
        Args:
            ticket_id: The JIRA ticket ID
            extract_fields: List of fields to extract
            ticket_info: Dictionary with basic ticket information
            
        Returns:
            Dictionary with ticket information
        """
        try:
            with LocalPlaywrightBrowser(headless=self.headless) as browser:
                # Navigate to the JIRA ticket
                ticket_url = f"{self.jira_url}/browse/{ticket_id}"
                logger.info(f"Navigating to {ticket_url}")
                browser.goto(ticket_url)
                
                # Extra wait to ensure page is fully loaded
                browser.wait(5000)  # Increased wait time
                
                # Update URL after navigation
                ticket_info["url"] = browser.get_current_url()
                
                # Check if login is required
                try:
                    if is_login_page(browser):
                        logger.info("Login required")
                        login_success = login(browser, self.username, self.password, 
                             use_sso=self.use_sso, prefer_google=self.prefer_google)
                        
                        if not login_success:
                            logger.error("Login failed")
                            ticket_info["error"] = "Login failed"
                            return ticket_info
                            
                        # Wait for redirect after login
                        browser.wait(5000)
                        
                        # Navigate to ticket again if needed
                        current_url = browser.get_current_url()
                        if ticket_id not in current_url:
                            logger.info(f"Navigating back to ticket {ticket_id} after login")
                            browser.goto(ticket_url)
                            browser.wait(5000)
                            
                            # Update URL after navigation
                            ticket_info["url"] = browser.get_current_url()
                except Exception as e:
                    logger.error(f"Error during login check: {e}")
                    ticket_info["error"] = f"Login error: {str(e)}"
                    return ticket_info
                
                # Extract ticket fields
                try:
                    self._extract_ticket_fields(browser, ticket_info, extract_fields)
                except Exception as e:
                    logger.error(f"Error extracting ticket fields: {e}")
                    ticket_info["error"] = f"Field extraction error: {str(e)}"
                
                return ticket_info
        except Exception as e:
            logger.error(f"Unexpected error accessing ticket {ticket_id}: {e}")
            ticket_info["error"] = f"Browser error: {str(e)}"
            return ticket_info
    
    def add_comment(self, ticket_id: str, comment_text: str) -> bool:
        """Add a comment to a JIRA ticket.
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            comment_text: The text of the comment to add
            
        Returns:
            True if comment was added successfully
        """
        logger.info(f"Adding comment to ticket {ticket_id}")
        
        # Use different implementation based on mode
        if self.mode == "api":
            return self._add_comment_api(ticket_id, comment_text)
        else:
            return self._add_comment_browser(ticket_id, comment_text)
    
    def _add_comment_api(self, ticket_id: str, comment_text: str) -> bool:
        """Add a comment to a ticket using JIRA API.
        
        Args:
            ticket_id: The JIRA ticket ID
            comment_text: The text of the comment to add
            
        Returns:
            True if comment was added successfully
        """
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API not available. Install with: pip install jira")
            return False
            
        logger.info(f"Using API mode to add comment to {ticket_id}")
        
        try:
            # Connect to JIRA
            jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.username, self.password)
            )
            
            # Add comment to the issue
            jira.add_comment(ticket_id, comment_text)
            
            logger.info(f"Comment added to {ticket_id} via API")
            return True
            
        except Exception as e:
            logger.error(f"Error adding comment via API: {e}")
            return False
    
    def _add_comment_browser(self, ticket_id: str, comment_text: str) -> bool:
        """Add a comment to a ticket using browser automation.
        
        Args:
            ticket_id: The JIRA ticket ID
            comment_text: The text of the comment to add
            
        Returns:
            True if comment was added successfully
        """
        with LocalPlaywrightBrowser(headless=self.headless) as browser:
            # Navigate to the JIRA ticket
            ticket_url = f"{self.jira_url}/browse/{ticket_id}"
            browser.goto(ticket_url)
            browser.wait(3000)  # Wait for page to load
            
            # Check if login is required
            if is_login_page(browser):
                logger.info("Login required")
                login(browser, self.username, self.password, 
                     use_sso=self.use_sso, prefer_google=self.prefer_google)
                
                # Wait for redirect after login
                browser.wait(5000)
                
                # Navigate to ticket again if needed
                current_url = browser.get_current_url()
                if ticket_id not in current_url:
                    browser.goto(ticket_url)
                    browser.wait(3000)
            
            # Click the comment button
            comment_button = DEFAULT_SELECTORS["ticket_page"]["add_comment"]["button"]
            if not browser.wait_for_selector(comment_button, timeout=5000):
                logger.error("Comment button not found")
                return False
                
            browser.click_selector(comment_button)
            browser.wait(1000)
            
            # Fill in the comment field
            comment_field = DEFAULT_SELECTORS["ticket_page"]["add_comment"]["field"]
            if not browser.wait_for_selector(comment_field, timeout=3000):
                logger.error("Comment field not found")
                return False
                
            browser.click_selector(comment_field)
            browser.type(comment_text)
            browser.wait(1000)
            
            # Click the submit button
            submit_button = DEFAULT_SELECTORS["ticket_page"]["add_comment"]["submit"]
            if not browser.wait_for_selector(submit_button, timeout=3000):
                logger.error("Submit button not found")
                return False
                
            browser.click_selector(submit_button)
            browser.wait(5000)  # Wait for comment to be added
            
            # Verify comment was added
            latest_comment_selector = f"{DEFAULT_SELECTORS['ticket_page']['comments']}:nth-last-child(1)"
            if browser.wait_for_selector(latest_comment_selector, timeout=5000):
                comment_text_content = browser.extract_text(latest_comment_selector)
                if comment_text in comment_text_content:
                    logger.info("Comment added successfully")
                    return True
                    
            logger.warning("Could not verify comment was added")
            return False
    
    def change_status(self, ticket_id: str, new_status: str) -> bool:
        """Change the status of a JIRA ticket.
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            new_status: The new status to set (e.g., "In Progress", "Done")
            
        Returns:
            True if status was changed successfully
        """
        logger.info(f"Changing status of ticket {ticket_id} to {new_status}")
        
        # Use different implementation based on mode
        if self.mode == "api":
            return self._change_status_api(ticket_id, new_status)
        else:
            return self._change_status_browser(ticket_id, new_status)
            
    def _change_status_api(self, ticket_id: str, new_status: str) -> bool:
        """Change ticket status using JIRA API.
        
        Args:
            ticket_id: The JIRA ticket ID
            new_status: The new status to set
            
        Returns:
            True if status was changed successfully
        """
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API not available. Install with: pip install jira")
            return False
            
        logger.info(f"Using API mode to change status of {ticket_id} to {new_status}")
        
        try:
            # Connect to JIRA
            jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.username, self.password)
            )
            
            # Get the issue
            issue = jira.issue(ticket_id)
            
            # Get available transitions
            transitions = jira.transitions(issue)
            
            # Find the transition ID for the requested status
            transition_id = None
            for t in transitions:
                if t['name'].lower() == new_status.lower() or t['to']['name'].lower() == new_status.lower():
                    transition_id = t['id']
                    break
                    
            if not transition_id:
                logger.error(f"No transition found for status: {new_status}")
                available_statuses = [t['to']['name'] for t in transitions]
                logger.info(f"Available statuses: {available_statuses}")
                return False
                
            # Perform the transition
            jira.transition_issue(issue, transition_id)
            
            logger.info(f"Changed status of {ticket_id} to {new_status} via API")
            return True
            
        except Exception as e:
            logger.error(f"Error changing status via API: {e}")
            return False
            
    def _change_status_browser(self, ticket_id: str, new_status: str) -> bool:
        """Change ticket status using browser automation.
        
        Args:
            ticket_id: The JIRA ticket ID
            new_status: The new status to set
            
        Returns:
            True if status was changed successfully
        """
        with LocalPlaywrightBrowser(headless=self.headless) as browser:
            # Navigate to the JIRA ticket
            ticket_url = f"{self.jira_url}/browse/{ticket_id}"
            browser.goto(ticket_url)
            browser.wait(3000)  # Wait for page to load
            
            # Check if login is required
            if is_login_page(browser):
                logger.info("Login required")
                login(browser, self.username, self.password, 
                     use_sso=self.use_sso, prefer_google=self.prefer_google)
                browser.wait(5000)
                
                # Navigate to ticket again if needed
                current_url = browser.get_current_url()
                if ticket_id not in current_url:
                    browser.goto(ticket_url)
                    browser.wait(3000)
            
            # Find and click the status dropdown
            status_dropdown = DEFAULT_SELECTORS["ticket_page"]["status_transition"]["dropdown"]
            if not browser.wait_for_selector(status_dropdown, timeout=5000):
                logger.error("Status dropdown not found")
                return False
                
            browser.click_selector(status_dropdown)
            browser.wait(2000)  # Wait for dropdown to open
            
            # Custom status selector based on the provided status name
            status_selector = f"button:contains('{new_status}')"
            
            # Try to find the status option
            if not browser.wait_for_selector(status_selector, timeout=5000):
                logger.error(f"Status option '{new_status}' not found")
                return False
                
            # Click the status option
            browser.click_selector(status_selector)
            browser.wait(3000)  # Wait for status change to take effect
            
            # Optional: Verify status changed
            current_status_text = browser.extract_text(DEFAULT_SELECTORS["ticket_page"]["status"])
            if new_status.lower() in current_status_text.lower():
                logger.info(f"Status successfully changed to {new_status}")
                return True
                
            logger.warning("Could not verify status change")
            return True  # Return True anyway as the click was successful

    def save_ticket_data(self, ticket_info: Dict[str, Any], output_dir: Optional[str] = None) -> str:
        """Save ticket data to a JSON file.
        
        Args:
            ticket_info: Dictionary of ticket data
            output_dir: Directory to save file (defaults to ./ticket_data)
            
        Returns:
            Path to saved file
        """
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "ticket_data")
            
        # Create directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Filename from ticket ID
        filename = f"{ticket_info['id'].replace('-', '_').lower()}.json"
        filepath = os.path.join(output_dir, filename)
        
        # Save data
        with open(filepath, 'w') as f:
            json.dump(ticket_info, f, indent=2)
            
        logger.info(f"Ticket data saved to: {filepath}")
        return filepath
    
    def analyze_ticket(self, ticket_id: str, analysis_endpoint: Optional[str] = None, 
                      analysis_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze a JIRA ticket using an external service or local processing.
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            analysis_endpoint: Optional endpoint for analysis service
            analysis_params: Additional parameters for analysis
            
        Returns:
            Analysis results as a dictionary
        """
        # Use different implementation based on mode
        if self.mode == "api":
            return self._analyze_ticket_api(ticket_id, analysis_endpoint, analysis_params)
        else:
            return self._analyze_ticket_browser(ticket_id, analysis_endpoint, analysis_params)
    
    def _analyze_ticket_api(self, ticket_id: str, analysis_endpoint: Optional[str], 
                        analysis_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ticket using JIRA API.
        
        Args:
            ticket_id: The JIRA ticket ID
            analysis_endpoint: Optional endpoint for analysis service
            analysis_params: Additional parameters for analysis
            
        Returns:
            Analysis results as a dictionary
        """
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API not available. Install with: pip install jira")
            return {
                "ticket_id": ticket_id,
                "error": "JIRA API package not installed. Run: pip install jira"
            }
            
        logger.info(f"Using API mode to analyze ticket {ticket_id}")
        
        try:
            # Connect to JIRA
            jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.username, self.password)
            )
            
            # Get the issue
            issue = jira.issue(ticket_id)
            
            # Get ticket data
            ticket_data = {
                "id": ticket_id,
                "summary": issue.fields.summary,
                "description": issue.fields.description or "",
                "status": issue.fields.status.name,
                "assignee": issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned",
                "reporter": issue.fields.reporter.displayName if issue.fields.reporter else "Unknown",
                "type": issue.fields.issuetype.name if issue.fields.issuetype else "Unknown",
                "priority": issue.fields.priority.name if issue.fields.priority else "None",
                "created": issue.fields.created,
                "updated": issue.fields.updated
            }
            
            # Get comments
            comments = []
            for comment in issue.fields.comment.comments:
                comments.append({
                    "author": comment.author.displayName,
                    "text": comment.body,
                    "created": comment.created
                })
            ticket_data["comments"] = comments
            
            # Basic analysis
            analysis_results = {
                "ticket_id": ticket_id,
                "data": ticket_data,
                "analysis": {
                    "word_count": len(ticket_data["description"].split()),
                    "comment_count": len(comments),
                    "age_days": self._days_since(ticket_data["created"]),
                    "last_updated_days": self._days_since(ticket_data["updated"])
                }
            }
            
            # If there's an external analysis endpoint, use it
            if analysis_endpoint:
                try:
                    import requests
                    
                    # Prepare payload
                    payload = {
                        "ticket_id": ticket_id,
                        "ticket_data": ticket_data
                    }
                    
                    # Add any additional parameters
                    if analysis_params:
                        payload.update(analysis_params)
                        
                    # Call the analysis service
                    response = requests.post(analysis_endpoint, json=payload)
                    
                    if response.status_code == 200:
                        external_analysis = response.json()
                        analysis_results["external_analysis"] = external_analysis
                        logger.info("External analysis completed successfully")
                    else:
                        analysis_results["external_analysis_error"] = f"Error: {response.status_code}"
                        logger.error(f"External analysis failed: {response.status_code}")
                except Exception as e:
                    analysis_results["external_analysis_error"] = str(e)
                    logger.error(f"Error calling external analysis service: {e}")
            
            return analysis_results
            
        except Exception as e:
            logger.error(f"Error analyzing ticket via API: {e}")
            return {
                "ticket_id": ticket_id,
                "error": f"JIRA API error: {str(e)}"
            }
    
    def _days_since(self, date_string: str) -> int:
        """Calculate days between a date string and now.
        
        Args:
            date_string: Date string in JIRA format
            
        Returns:
            Number of days
        """
        from datetime import datetime
        import dateutil.parser
        
        try:
            # Parse the date string
            issue_date = dateutil.parser.parse(date_string)
            
            # Calculate difference from now
            now = datetime.now(issue_date.tzinfo)
            delta = now - issue_date
            
            return delta.days
        except Exception:
            return 0
    
    def _analyze_ticket_browser(self, ticket_id: str, analysis_endpoint: Optional[str], 
                          analysis_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze ticket using browser automation.
        
        Args:
            ticket_id: The JIRA ticket ID
            analysis_endpoint: Optional endpoint for analysis service
            analysis_params: Additional parameters for analysis
            
        Returns:
            Analysis results as a dictionary
        """
        logger.info(f"Analyzing ticket {ticket_id}")
        
        # Get ticket data first
        ticket_info = self.get_ticket(
            ticket_id, 
            extract_fields=["summary", "description", "status", "priority", "type"]
        )
        
        # Simple analysis based on ticket data
        analysis_results = {
            "ticket_id": ticket_id,
            "data": {
                "summary": ticket_info.get("summary", ""),
                "status": ticket_info.get("status", ""),
                "type": ticket_info.get("type", "")
            },
            "analysis": {
                "word_count": len(ticket_info.get("description", "").split()),
                "priority": ticket_info.get("priority", "Unknown")
            }
        }
        
        # If an external analysis endpoint is provided, use it
        if analysis_endpoint:
            try:
                import requests
                
                # Prepare request payload
                payload = {
                    "ticket_id": ticket_id,
                    "ticket_data": ticket_info
                }
                
                # Add any additional parameters
                if analysis_params:
                    payload.update(analysis_params)
                    
                # Send request to analysis service
                response = requests.post(analysis_endpoint, json=payload)
                
                if response.status_code == 200:
                    external_analysis = response.json()
                    analysis_results["external_analysis"] = external_analysis
                    logger.info("External analysis completed successfully")
                else:
                    analysis_results["external_analysis_error"] = f"Error: {response.status_code}"
                    logger.error(f"External analysis failed: {response.status_code}")
            except Exception as e:
                analysis_results["external_analysis_error"] = str(e)
                logger.error(f"Error calling external analysis service: {e}")
        
        return analysis_results
        
    def _extract_ticket_fields(self, browser, ticket_info: Dict[str, Any], extract_fields: List[str]) -> None:
        """Extract all requested fields from the JIRA ticket.
        
        Args:
            browser: Browser instance
            ticket_info: Dictionary to update with extracted data
            extract_fields: List of fields to extract
        """
        # Always extract summary and description
        fields_to_extract = ["summary", "description"] + extract_fields
        
        # Remove duplicates
        fields_to_extract = list(dict.fromkeys(fields_to_extract))
        
        for field in fields_to_extract:
            if field in FIELD_SELECTORS:
                logger.info(f"Extracting {field}")
                selector = FIELD_SELECTORS[field]
                try:
                    # First check if the element exists and is visible
                    element_info = browser.get_element_info(selector)
                    
                    if element_info and element_info.get('isVisible', False):
                        text = browser.extract_text(selector)
                        ticket_info[field] = text
                        logger.info(f"Extracted {field}: {text[:50]}..." if len(text) > 50 else f"Extracted {field}: {text}")
                    else:
                        # Log debug info
                        if element_info:
                            logger.debug(f"{field} element found but not visible: {element_info}")
                        else:
                            logger.debug(f"{field} element not found")
                        
                        # Extended selectors for common fields
                        if field == "summary":
                            alt_selectors = [
                                "h1", 
                                "[data-testid*='summary']", 
                                "[id*='summary']", 
                                "[class*='summary']",
                                ".issue-header-content h1",
                                "h1.entry-title",
                                "#summary-val",
                                ".ghx-summary"
                            ]
                        elif field == "description":
                            alt_selectors = [
                                "[data-testid*='description']", 
                                "[id*='description']", 
                                "[class*='description']",
                                "#description-val",
                                ".user-content-block"
                            ]
                        else:
                            alt_selectors = [
                                f"[data-testid*='{field}']", 
                                f"[id*='{field}']", 
                                f"[class*='{field}']"
                            ]
                        
                        # Try each alternative selector
                        field_found = False
                        for alt_selector in alt_selectors:
                            try:
                                if browser.wait_for_selector(alt_selector, timeout=3000):  # Increased timeout
                                    text = browser.extract_text(alt_selector)
                                    ticket_info[field] = text
                                    logger.info(f"Extracted {field} using {alt_selector}: {text[:50]}..." if len(text) > 50 else f"Extracted {field} using {alt_selector}: {text}")
                                    field_found = True
                                    break
                            except Exception as e:
                                logger.debug(f"Error with alt selector {alt_selector}: {e}")
                                continue
                        
                        if not field_found:
                            logger.warning(f"Could not find {field} using any selector")
                            ticket_info[field] = "Not found"
                except Exception as e:
                    logger.error(f"Error extracting {field}: {e}")
                    ticket_info[field] = "Error extracting"
        
        # As a fallback, get the entire HTML if extraction fails
        if "summary" not in ticket_info or ticket_info["summary"] == "Not found":
            try:
                # Try a broader approach by getting all headings
                headings = browser.execute_script("""
                    return Array.from(document.querySelectorAll('h1,h2')).map(el => el.innerText).join('\\n');
                """)
                
                if headings:
                    logger.info("Found headings as fallback for summary")
                    ticket_info["summary"] = headings.split('\n')[0]  # Use the first heading
                else:
                    # Save HTML for debugging
                    ticket_info["_html"] = browser.get_page_html()
                    logger.info("Saved page HTML as fallback")
            except Exception as e:
                logger.error(f"Error getting page HTML: {e}") 
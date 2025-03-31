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
                cache_dir: str = "./cache"):
        """Initialize the JIRA agent.
        
        Args:
            headless: Whether to run the browser in headless mode
            jira_url: URL of the JIRA instance
            username: JIRA username (if None, reads from JIRA_USERNAME env var)
            password: JIRA password (if None, reads from JIRA_PASSWORD env var)
            use_sso: Whether to use SSO for authentication
            prefer_google: Whether to prefer Google SSO if available
            cache_dir: Directory for caching memory
        """
        self.headless = headless
        self.jira_url = jira_url or os.getenv("JIRA_URL", "https://mydomain.atlassian.net")
        self.username = username or os.getenv("JIRA_USERNAME")
        self.password = password or os.getenv("JIRA_PASSWORD")
        self.use_sso = use_sso
        self.prefer_google = prefer_google
        
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
            new_status: The new status (e.g., "In Progress", "Done", etc.)
            
        Returns:
            True if status was changed successfully
        """
        logger.info(f"Changing status of ticket {ticket_id} to {new_status}")
        
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
            
            # Click the status dropdown
            status_dropdown = DEFAULT_SELECTORS["ticket_page"]["status_transition"]["dropdown"]
            if not browser.wait_for_selector(status_dropdown, timeout=5000):
                logger.error("Status dropdown not found")
                return False
                
            browser.click_selector(status_dropdown)
            browser.wait(1000)
            
            # Click the new status option
            # First try to find a specific selector for the requested status
            status_key = new_status.lower().replace(" ", "_")
            if status_key in DEFAULT_SELECTORS["ticket_page"]["status_transition"]["options"]:
                status_option = DEFAULT_SELECTORS["ticket_page"]["status_transition"]["options"][status_key]
            else:
                # Otherwise, try a generic selector with the status text
                status_option = f"button:contains('{new_status}'), [role='option']:contains('{new_status}')"
                
            if not browser.wait_for_selector(status_option, timeout=5000):
                logger.error(f"Status option '{new_status}' not found")
                return False
                
            browser.click_selector(status_option)
            browser.wait(5000)  # Wait for status to change
            
            # Verify status was changed
            status_text = browser.extract_text(DEFAULT_SELECTORS["ticket_page"]["status"])
            if new_status.lower() in status_text.lower():
                logger.info("Status changed successfully")
                return True
                
            logger.warning("Could not verify status was changed")
            return False
    
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
        """Analyze a JIRA ticket and optionally call an external API.
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            analysis_endpoint: Optional API endpoint URL for external analysis
            analysis_params: Optional additional parameters for the API call
            
        Returns:
            Dictionary with analysis results
        """
        # Get ticket information
        ticket_info = self.get_ticket(ticket_id, extract_fields=["status", "assignee", "priority", "type", 
                                                               "reporter", "comments", "labels"])
        
        # Basic analysis
        analysis_results = {
            "ticket_id": ticket_id,
            "summary": ticket_info.get("summary", ""),
            "status": ticket_info.get("status", ""),
            "has_description": bool(ticket_info.get("description")),
            "comment_count": len(ticket_info.get("comments", [])),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Call external API if provided
        if analysis_endpoint:
            import requests
            
            params = analysis_params or {}
            params.update({
                "ticket_id": ticket_id,
                "summary": ticket_info.get("summary", ""),
                "description": ticket_info.get("description", "")
            })
            
            try:
                response = requests.post(analysis_endpoint, json=params)
                if response.status_code == 200:
                    api_results = response.json()
                    analysis_results["api_results"] = api_results
                    logger.info(f"API analysis completed for ticket {ticket_id}")
                else:
                    logger.error(f"API call failed with status {response.status_code}")
                    analysis_results["api_error"] = f"Status code: {response.status_code}"
            except Exception as e:
                logger.error(f"API call error: {e}")
                analysis_results["api_error"] = str(e)
        
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
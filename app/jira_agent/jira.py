"""JIRA agent for interacting with JIRA tickets.

This module provides the JiraAgent class for interacting with JIRA:
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
                jira_url: str = None,
                username: Optional[str] = None,
                password: Optional[str] = None,
                cache_dir: str = "./cache"):
        """Initialize the JIRA agent.
        
        Args:
            jira_url: URL of the JIRA instance
            username: JIRA username (if None, reads from JIRA_USERNAME env var)
            password: JIRA password (if None, reads from JIRA_PASSWORD env var)
            cache_dir: Directory for caching memory
        """
        self.jira_url = jira_url or os.getenv("JIRA_URL", "https://mydomain.atlassian.net")
        self.username = username or os.getenv("JIRA_USERNAME")
        self.password = password or os.getenv("JIRA_PASSWORD")
        
        if not self.username or not self.password:
            raise ValueError("JIRA credentials are required. Set them in .env file or pass them to the constructor.")
            
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API package not installed. Install with: pip install jira")
        
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
        
        return self._get_ticket_api(ticket_id, extract_fields)
    
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
            
        logger.info(f"Using API to get ticket {ticket_id}")
        
        # Initialize with basic info
        ticket_info = {
            "id": ticket_id,
            "url": f"{self.jira_url}/browse/{ticket_id}"
        }
        
        try:
            # Connect to JIRA
            jira = JIRA(
                server=self.jira_url,
                basic_auth=(self.username, self.password)
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
    
    def add_comment(self, ticket_id: str, comment_text: str) -> bool:
        """Add a comment to a JIRA ticket.
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            comment_text: The text of the comment to add
            
        Returns:
            True if comment was added successfully
        """
        logger.info(f"Adding comment to ticket {ticket_id}")
        
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API not available. Install with: pip install jira")
            return False
            
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
    
    def change_status(self, ticket_id: str, new_status: str) -> bool:
        """Change the status of a JIRA ticket.
        
        Args:
            ticket_id: The JIRA ticket ID (e.g., "PROJ-123")
            new_status: The new status to set (e.g., "In Progress", "Done")
            
        Returns:
            True if status was changed successfully
        """
        logger.info(f"Changing status of ticket {ticket_id} to {new_status}")
        
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API not available. Install with: pip install jira")
            return False
            
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
        if not JIRA_API_AVAILABLE:
            logger.warning("JIRA API not available. Install with: pip install jira")
            return {
                "ticket_id": ticket_id,
                "error": "JIRA API package not installed. Run: pip install jira"
            }
            
        logger.info(f"Analyzing ticket {ticket_id}")
        
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
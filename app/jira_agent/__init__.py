"""JIRA agent for automating interaction with JIRA tickets.

This package provides tools for:
1. Authenticating with JIRA (including SSO)
2. Navigating to and extracting data from JIRA tickets
3. Performing actions on tickets (commenting, status updates, etc.)
"""

from app.jira_agent.jira import JiraAgent

__all__ = ["JiraAgent"] 
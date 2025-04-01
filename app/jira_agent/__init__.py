"""JIRA agent for automating interaction with JIRA tickets.

This package provides tools for:
1. Authenticating with JIRA (including SSO)
2. Navigating to and extracting data from JIRA tickets
3. Performing actions on tickets (commenting, status updates, etc.)
4. Integrating with external APIs and parsing API documentation
"""

from app.jira_agent.jira import JiraAgent
from app.jira_agent.api_utils import (
    parse_api_docs_with_llm,
    extract_endpoints_rule_based,
    get_api_documentation,
    determine_headers
)

__all__ = [
    "JiraAgent",
    "parse_api_docs_with_llm",
    "extract_endpoints_rule_based",
    "get_api_documentation",
    "determine_headers"
] 
"""
Example demonstrating how to use the JIRA agent with an external API.

This example shows how to:
1. Initialize the JIRA agent
2. Extract data from JIRA tickets
3. Send ticket data to an external API for analysis
4. Post the analysis results back as a comment
"""

import os
import json
import re
import requests
from dotenv import load_dotenv
from app.jira_agent import (
    JiraAgent, 
    select_api_with_llm,
    extract_endpoints_rule_based,
    get_api_documentation,
    determine_headers
)

# Load environment variables from .env.local file
load_dotenv(dotenv_path=".env.local", override=True)

# Define your API endpoint
# This can be any API that takes JIRA ticket data and returns an analysis
API_ENDPOINT = os.getenv("PROD_SUPPORT_API_URL", "http://localhost:8080/")
API_KEY = os.getenv("ANALYSIS_API_KEY", "")
# Optional: Add LLM API key for documentation parsing
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")


def analyze_with_api(ticket_data):
    """
    Send ticket data to an external API for analysis.
    
    Args:
        ticket_data: Dictionary containing ticket information
        
    Returns:
        Dictionary with analysis results or error message
    """
    print(f"Connecting to API at: {API_ENDPOINT}")
    
    # Get API documentation using the refactored utility
    api_documentation, content_type = get_api_documentation(API_ENDPOINT, "/docs/guide")
    
    if not api_documentation:
        print("Could not retrieve API documentation")
        api_analysis_result = {"endpoints": [], "analysis_endpoint": None}
    else:
        # Use the refactored LLM parser
        api_analysis_result = select_api_with_llm(
            ticket_data,
            api_documentation, 
            llm_api_key=LLM_API_KEY,
            llm_api_url=LLM_API_URL
        )
        
        # Display the endpoints found
        selected_endpoint = api_analysis_result.get("endpoint", [])
        print(f"Selected endpoint: {selected_endpoint}")
        
        # Display additional information if provided by the LLM
        if "relevant_info" in api_analysis_result:
            print(f"Relevant information from ticket: {api_analysis_result['relevant_info']}")
    
    # Now proceed with the actual analysis
    print(f"\nSending ticket data to API for analysis...")
    
    try:
        # In a real implementation, you would do:
        full_url = f"{API_ENDPOINT.rstrip('/')}{selected_endpoint}"
        print(f"Using endpoint: {full_url}")
        
        # Use the utility to determine headers based on documentation
        headers = determine_headers(api_analysis_result, API_KEY)
        
        # Try to make the actual API call
        # Uncomment this in real implementation:
        # response = requests.post(full_url, json=ticket_data, headers=headers)
        # if response.status_code == 200:
        #     return response.json()
        
        # For this example, we'll simulate a response with simplified content
        simulation_response = {
            "analysis": {
                # Only include necessary fields
                "user_account_status": "Active"
            },
            "api_info": {
                "documentation_available": bool(api_documentation),
                "endpoints_found": api_analysis_result.get("endpoints", []),
                "endpoint_used": selected_endpoint,
                "llm_parsed": True,
                "auth_method": api_analysis_result.get("auth_method", "Not specified")
            }
        }
        
        # Add email to response if available
        if "user_email" in ticket_data and ticket_data["user_email"]:
            simulation_response["analysis"]["user_email"] = ticket_data["user_email"]
        
        return simulation_response
        
    except Exception as e:
        print(f"Error during API analysis: {e}")
        return {
            "error": str(e),
            "message": "Failed to analyze ticket"
        }


def format_analysis_comment(analysis_results):
    """
    Format analysis results as a markdown comment for JIRA.
    
    Args:
        analysis_results: Dictionary with analysis results
        
    Returns:
        Formatted comment text
    """
    comment = "**Automated Analysis Results**\n\n"
    
    # Get analysis section
    analysis = analysis_results.get("analysis", {})
    
    # Add user email if available
    if "user_email" in analysis:
        comment += f"**User Email**: {analysis['user_email']}\n"
    
    # Add account status if available
    if "user_account_status" in analysis:
        comment += f"**Account Status**: {analysis['user_account_status']}\n"
    
    comment += "\n"
    
    # Add API information if available
    api_info = analysis_results.get("api_info", {})
    if api_info:
        comment += "**API Information**:\n"
        comment += f"- Documentation Available: {api_info.get('documentation_available', False)}\n"
        comment += f"- Endpoint Used: {api_info.get('endpoint_used', 'Unknown')}\n"
        
        # Add list of available endpoints (first 3 only to keep comment concise)
        endpoints = api_info.get("endpoints_found", [])
        if endpoints:
            comment += f"- Available Endpoints ({len(endpoints)} total): "
            if len(endpoints) <= 3:
                comment += ", ".join(endpoints)
            else:
                comment += ", ".join(endpoints[:3]) + f", ... ({len(endpoints) - 3} more)"
            comment += "\n"
    
    return comment


def main():
    """Run the JIRA API integration example."""
    # Get ticket ID from user
    ticket_id = input("Enter JIRA ticket ID (e.g., PROJ-123): ")
    
    # Initialize the JIRA agent
    agent = JiraAgent(
        jira_url=os.getenv("JIRA_URL"),
        username=os.getenv("JIRA_USERNAME"),
        password=os.getenv("JIRA_PASSWORD")
    )
    
    # Get ticket information with additional fields
    print(f"\nGetting information for ticket {ticket_id}...")
    ticket_info = agent.get_ticket(
        ticket_id, 
        extract_fields=["summary", "description"]
    )
    
    # Extract email from description if present
    description = ticket_info.get("description", "")
    
    # Display basic ticket information
    print(f"\nTicket: {ticket_info.get('id')}")
    print(f"Summary: {ticket_info.get('summary', 'Unknown')}")
    print(f"Status: {ticket_info.get('status', 'Unknown')}")
    
    # Analyze with external API (or simulation)
    print("\nSending to API for analysis...")
    analysis_results = analyze_with_api(ticket_info)
    
    # Display analysis results
    print("\nAnalysis Results:")
    print(json.dumps(analysis_results, indent=2))
    
    # Format as comment
    comment_text = format_analysis_comment(analysis_results)
    print("\nFormatted Comment:")
    print(comment_text)
    
    # Ask if we should post the analysis as a comment
    post_comment = input("\nPost analysis as comment to JIRA ticket? (y/n): ").lower() == 'y'
    if post_comment:
        print(f"Adding analysis as comment to ticket {ticket_id}...")
        result = agent.add_comment(ticket_id, comment_text)
        if result:
            print("Analysis comment added successfully!")
        else:
            print("Failed to add analysis comment.")
    
    # Save analysis to file
    save_option = input("\nSave full analysis to file? (y/n): ").lower()
    if save_option == 'y':
        # Create results dict with both ticket info and analysis
        combined_results = {
            "ticket_info": ticket_info,
            "analysis": analysis_results
        }
        
        # Save file
        output_dir = os.path.join(os.getcwd(), "analysis_results")
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{ticket_id.replace('-', '_').lower()}_analysis.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(combined_results, f, indent=2)
            
        print(f"Analysis saved to: {filepath}")
    
    print("\nJIRA API integration example completed!")
    
if __name__ == "__main__":
    main() 
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
import requests
from dotenv import load_dotenv
from app.jira_agent import JiraAgent

# Load environment variables
load_dotenv(override=True)

# Define your API endpoint
# This can be any API that takes JIRA ticket data and returns an analysis
API_ENDPOINT = os.getenv("ANALYSIS_API_ENDPOINT", "https://your-analysis-api.com/analyze")
API_KEY = os.getenv("ANALYSIS_API_KEY", "")


def analyze_with_api(ticket_data):
    """
    Send ticket data to an external API for analysis.
    
    Args:
        ticket_data: Dictionary containing ticket information
        
    Returns:
        Dictionary with analysis results or error message
    """
    # This is a simulation - in a real example, you would call your actual API
    # For demonstration, we'll simulate an API response
    
    print(f"Sending data to API: {API_ENDPOINT}")
    
    # In a real implementation, you would do:
    # headers = {"Authorization": f"Bearer {API_KEY}"}
    # response = requests.post(API_ENDPOINT, json=ticket_data, headers=headers)
    # return response.json()
    
    # For this example, we'll simulate a response
    simulation_response = {
        "analysis": {
            "ticket_type": "Bug Report",
            "priority_recommendation": "High" if "urgent" in ticket_data.get("summary", "").lower() else "Medium",
            "estimated_effort": "4 hours",
            "similar_tickets": ["PROJ-100", "PROJ-212", "PROJ-345"],
            "recommended_action": "Assign to backend team",
            "automated_checks": [
                {"name": "Security scan", "result": "Passed"},
                {"name": "Code quality", "result": "Failed", "details": "Insufficient test coverage"}
            ]
        },
        "timestamp": "2023-06-01T12:34:56Z"
    }
    
    return simulation_response


def format_analysis_comment(analysis_results):
    """
    Format analysis results as a markdown comment for JIRA.
    
    Args:
        analysis_results: Dictionary with analysis results
        
    Returns:
        Formatted comment text
    """
    comment = "**Automated Analysis Results**\n\n"
    
    # Add ticket type and priority
    analysis = analysis_results.get("analysis", {})
    comment += f"**Ticket Type**: {analysis.get('ticket_type', 'Unknown')}\n"
    comment += f"**Recommended Priority**: {analysis.get('priority_recommendation', 'Unknown')}\n"
    comment += f"**Estimated Effort**: {analysis.get('estimated_effort', 'Unknown')}\n\n"
    
    # Add recommended action
    if "recommended_action" in analysis:
        comment += f"**Recommended Action**: {analysis['recommended_action']}\n\n"
    
    # Add similar tickets
    similar_tickets = analysis.get("similar_tickets", [])
    if similar_tickets:
        comment += "**Similar Tickets**:\n"
        for ticket in similar_tickets:
            comment += f"- {ticket}\n"
        comment += "\n"
    
    # Add automated checks
    automated_checks = analysis.get("automated_checks", [])
    if automated_checks:
        comment += "**Automated Checks**:\n"
        for check in automated_checks:
            result_icon = "✅" if check["result"] == "Passed" else "❌"
            comment += f"- {result_icon} {check['name']}: {check['result']}"
            if "details" in check:
                comment += f" - {check['details']}"
            comment += "\n"
    
    return comment


def main():
    """Run the JIRA API integration example."""
    # Get ticket ID from user
    ticket_id = input("Enter JIRA ticket ID (e.g., PROJ-123): ")
    
    # Initialize the JIRA agent
    agent = JiraAgent(
        headless=False,  # Set to True to hide the browser
        jira_url=os.getenv("JIRA_URL"),
        use_sso=True,
        prefer_google=True
    )
    
    # Get ticket information with additional fields
    print(f"\nGetting information for ticket {ticket_id}...")
    ticket_info = agent.get_ticket(
        ticket_id, 
        extract_fields=["status", "assignee", "priority", "type", "reporter", "labels", "comments"]
    )
    
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
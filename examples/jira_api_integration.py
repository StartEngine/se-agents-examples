"""
Example demonstrating how to use the JIRA agent with an external API.

This example shows how to:
1. Initialize the JIRA agent
2. Extract data from JIRA tickets
3. Send ticket data to an external API for analysis
4. Display the API response
"""

import os
import json
import requests
from dotenv import load_dotenv
from app.jira_agent import (
    JiraAgent, 
    select_api_with_llm,
    extract_endpoints_rule_based,
    get_api_documentation
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
        API response text
    """
    print(f"Connecting to API at: {API_ENDPOINT}")
    
    # Get API documentation using the refactored utility
    api_documentation, content_type = get_api_documentation(API_ENDPOINT, "/docs/guide")
    
    if not api_documentation:
        print("Could not retrieve API documentation")
        api_analysis_result = {"endpoint": None, "relevant_info": None, "endpoint_params": {}}
    else:
        try:
            # Use the refactored LLM parser
            api_analysis_result = select_api_with_llm(
                ticket_data,
                api_documentation, 
                llm_api_key=LLM_API_KEY,
                llm_api_url=LLM_API_URL
            )
            
            # Make sure api_analysis_result is a dictionary
            if not isinstance(api_analysis_result, dict):
                print(f"Warning: Expected dictionary from select_api_with_llm but got {type(api_analysis_result)}")
                api_analysis_result = {"endpoint": None, "relevant_info": str(api_analysis_result), "endpoint_params": {}}
        except Exception as e:
            print(f"Error during API documentation analysis: {e}")
            api_analysis_result = {"endpoint": None, "relevant_info": None, "endpoint_params": {}}
    
    # Safely get values from api_analysis_result
    selected_endpoint = None
    relevant_info = None
    endpoint_params = {}
    
    if isinstance(api_analysis_result, dict):
        selected_endpoint = api_analysis_result.get("endpoint")
        relevant_info = api_analysis_result.get("relevant_info")
        endpoint_params = api_analysis_result.get("endpoint_params", {})
    
    # Display the endpoints found
    print(f"Selected endpoint: {selected_endpoint}")
    
    # Display additional information if provided by the LLM
    if relevant_info:
        print(f"Relevant information from ticket: {relevant_info}")
        
    if endpoint_params:
        print(f"Required parameters for endpoint: {endpoint_params}")
    
    # Now proceed with the actual analysis
    print(f"\nSending ticket data to API for analysis...")
    
    try:
        # Use default endpoint if none was selected
        if not selected_endpoint:
            selected_endpoint = "/api/v1/analyze"
            print(f"No endpoint selected, using default: {selected_endpoint}")
            
        # Build the request URL
        base_url = f"{API_ENDPOINT.rstrip('/')}{selected_endpoint}"
        
        # Create headers for API request
        headers = {}
        if API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"
            
        # Prepare request parameters based on relevant_info and endpoint_params
        request_params = {}
        if isinstance(relevant_info, dict):
            # For each parameter required by the endpoint, try to find it in relevant_info
            if endpoint_params:
                for param_name in endpoint_params.keys():
                    if param_name in relevant_info:
                        request_params[param_name] = relevant_info[param_name]
            else:
                # If we don't have endpoint_params, just use all relevant_info
                request_params = relevant_info
        
        # Include some ticket information if not already in request_params
        if "ticket_id" not in request_params and "id" in ticket_data:
            request_params["ticket_id"] = ticket_data["id"]
        
        if "email" not in request_params and isinstance(relevant_info, dict) and "email" in relevant_info:
            request_params["email"] = relevant_info["email"]
        
        # Build the final URL with parameters
        url_params = "&".join([f"{k}={v}" for k, v in request_params.items()])
        if "?" not in base_url:
            full_url = f"{base_url}?{url_params}" if url_params else base_url
        else:
            full_url = f"{base_url}&{url_params}" if url_params else base_url
            
        print(f"Making GET request to: {full_url}")
        
        # Make the actual API call (GET method only)
        response = requests.get(full_url, headers=headers)
        
        if response.status_code == 200:
            return response.text
        else:
            error_message = f"API call failed with status {response.status_code}: {response.text[:100]}"
            print(error_message)
            return error_message
        
    except Exception as e:
        error_message = f"Error during API analysis: {e}"
        print(error_message)
        return error_message


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
        extract_fields=["summary", "description", "assignee"]
    )
    
    # Display basic ticket information
    print(f"\nTicket: {ticket_info.get('id')}")
    print(f"Summary: {ticket_info.get('summary', 'Unknown')}")
    print(f"Assignee: {ticket_info.get('assignee', 'Unknown')}")
    
    # Analyze with external API
    print("\nSending to API for analysis...")
    api_response = analyze_with_api(ticket_info)
    
    # Display raw API response
    print("\nAPI Response:")
    print(api_response)
    
    # Ask if we should post the API response as a comment to JIRA
    post_comment = input("\nPost API response as comment to JIRA ticket? (y/n): ").lower() == 'y'
    if post_comment:
        print(f"Adding API response as comment to ticket {ticket_id}...")
        result = agent.add_comment(ticket_id, api_response)
        if result:
            print("API response comment added successfully!")
        else:
            print("Failed to add comment.")
    
    print("\nJIRA API integration example completed!")
    
if __name__ == "__main__":
    main() 
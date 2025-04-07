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
import tkinter as tk
from tkinter import scrolledtext
import threading
from dotenv import load_dotenv
from app.jira_agent import (
    JiraAgent, 
    select_api_with_llm,
    extract_endpoints_rule_based,
    get_api_documentation
)
import sys

# Load environment variables from .env.local file
load_dotenv(dotenv_path=".env.local", override=True)

# Define your API endpoint
# This can be any API that takes JIRA ticket data and returns an analysis
API_ENDPOINT = os.getenv("PROD_SUPPORT_API_URL", "http://localhost:8080/")
API_KEY = os.getenv("ANALYSIS_API_KEY", "")
# Optional: Add LLM API key for documentation parsing
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")


class RedirectText:
    """
    A class that redirects print statements to both the console and a tkinter text widget.
    """
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = ""
        self.original_stdout = sys.__stdout__
        
    def write(self, string):
        self.buffer += string
        self.text_widget.config(state=tk.NORMAL)
        self.text_widget.insert(tk.END, string)
        self.text_widget.see(tk.END)
        self.text_widget.config(state=tk.DISABLED)
        # Write to original stdout to avoid recursion
        self.original_stdout.write(string)
        
    def flush(self):
        pass


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


def run_analysis(ticket_id, submit_button, status_label, comment_frame, yes_button, no_button):
    """Process JIRA ticket and display results in GUI"""
    
    # Update status
    status_label.config(text="Working on your request...")
    submit_button.config(state=tk.DISABLED)
    
    # Hide comment buttons initially
    comment_frame.pack_forget()
    
    # Initialize the JIRA agent
    agent = JiraAgent(
        jira_url=os.getenv("JIRA_URL"),
        username=os.getenv("JIRA_USERNAME"),
        password=os.getenv("JIRA_PASSWORD")
    )
    
    # Get ticket information with additional fields
    print(f"\nGetting information for ticket {ticket_id}...")
    import time
    time.sleep(2)  # Add a 2-second delay
    
    ticket_info = agent.get_ticket(
        ticket_id, 
        extract_fields=["summary", "description", "assignee"]
    )
    
    # Display basic ticket information
    print(f"\nTicket: {ticket_info.get('id')}")
    time.sleep(2)  # Add a 2-second delay
    
    print(f"Summary: {ticket_info.get('summary', 'Unknown')}")
    time.sleep(2)  # Add a 2-second delay
    
    print(f"Assignee: {ticket_info.get('assignee', 'Unknown')}")
    time.sleep(2)  # Add a 2-second delay
    
    # Analyze with external API
    print("\nSending to API for analysis...")
    time.sleep(2)  # Add a 2-second delay
    
    api_response = analyze_with_api(ticket_info)
    
    # Display raw API response
    print("\nAPI Response:")
    time.sleep(2)  # Add a 2-second delay
    
    print(api_response)
    
    # Store the current ticket_id and api_response for the comment buttons
    yes_button.config(command=lambda: post_comment_to_jira(agent, ticket_id, api_response, status_label, comment_frame))
    no_button.config(command=lambda: skip_comment(status_label, comment_frame))
    
    # Show the comment option in the UI
    comment_frame.pack(fill=tk.X, pady=10)
    
    # Update status
    status_label.config(text="Analysis completed! Post as comment?")


def post_comment_to_jira(agent, ticket_id, api_response, status_label, comment_frame):
    """Post the API response as a comment to the JIRA ticket"""
    status_label.config(text="Posting comment...")
    
    # Hide comment buttons
    comment_frame.pack_forget()
    
    print(f"\nAdding API response as comment to ticket {ticket_id}...")
    result = agent.add_comment(ticket_id, api_response)
    if result:
        print("API response comment added successfully!")
        status_label.config(text="Comment added successfully!")
    else:
        print("Failed to add comment.")
        status_label.config(text="Failed to add comment.")
    
    print("\nJIRA API integration example completed!")


def skip_comment(status_label, comment_frame):
    """Skip posting the comment"""
    # Hide comment buttons
    comment_frame.pack_forget()
    
    print("\nSkipped posting comment.")
    print("\nJIRA API integration example completed!")
    status_label.config(text="Analysis completed!")


def create_gui():
    """Create a GUI window for JIRA ticket analysis"""
    root = tk.Tk()
    root.title("JIRA API Integration")
    
    # Set window size
    window_width = 800
    window_height = 600
    root.geometry(f"{window_width}x{window_height}")
    
    # Center the window on the screen
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x_position = int((screen_width - window_width) / 2)
    y_position = int((screen_height - window_height) / 2)
    root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    
    # Create frames
    input_frame = tk.Frame(root, padx=10, pady=10)
    input_frame.pack(fill=tk.X)
    
    output_frame = tk.Frame(root, padx=10, pady=10)
    output_frame.pack(fill=tk.BOTH, expand=True)
    
    # Create comment frame (initially hidden)
    comment_frame = tk.Frame(root, padx=10, pady=10)
    
    # Add comment question and buttons
    tk.Label(comment_frame, text="Post API response as comment to JIRA ticket?").pack(side=tk.LEFT)
    yes_button = tk.Button(comment_frame, text="Yes", width=8)
    yes_button.pack(side=tk.LEFT, padx=5)
    no_button = tk.Button(comment_frame, text="No", width=8)
    no_button.pack(side=tk.LEFT, padx=5)
    
    # Ticket ID input
    tk.Label(input_frame, text="Enter JIRA Ticket ID:").pack(side=tk.LEFT)
    ticket_entry = tk.Entry(input_frame, width=20)
    ticket_entry.pack(side=tk.LEFT, padx=5)
    
    # Status label
    status_label = tk.Label(input_frame, text="Ready")
    status_label.pack(side=tk.RIGHT)
    
    # Output text area
    output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, state=tk.DISABLED)
    output_text.pack(fill=tk.BOTH, expand=True)
    
    # Submit button
    def on_submit():
        ticket_id = ticket_entry.get().strip()
        if not ticket_id:
            status_label.config(text="Please enter a ticket ID")
            return
            
        # Clear output
        output_text.config(state=tk.NORMAL)
        output_text.delete(1.0, tk.END)
        output_text.config(state=tk.DISABLED)
        
        # Run analysis in a separate thread to keep UI responsive
        thread = threading.Thread(
            target=run_analysis, 
            args=(ticket_id, submit_button, status_label, comment_frame, yes_button, no_button)
        )
        thread.daemon = True
        thread.start()
    
    submit_button = tk.Button(input_frame, text="Analyze Ticket", command=on_submit)
    submit_button.pack(side=tk.LEFT, padx=5)
    
    # Redirect stdout to the text widget
    redirect = RedirectText(output_text)
    sys.stdout = redirect
    
    return root


def main():
    """Run the JIRA API integration example with GUI."""
    root = create_gui()
    root.mainloop()
    
if __name__ == "__main__":
    main() 
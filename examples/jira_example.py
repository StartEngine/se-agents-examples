"""
Example demonstrating how to use the JIRA agent for interacting with JIRA tickets.

This example shows how to:
1. Initialize the JIRA agent
2. Get information about a ticket
3. Add comments to tickets
4. Change ticket status
5. Save ticket data
"""

import os
from dotenv import load_dotenv
from app.jira_agent import JiraAgent

# Load environment variables
load_dotenv(override=True)

def main():
    """Run the JIRA example."""
    # Get ticket ID from user
    ticket_id = input("Enter JIRA ticket ID (e.g., PROJ-123): ")
    
    # Initialize the JIRA agent
    # You can customize these parameters or set them in your .env file
    agent = JiraAgent(
        headless=False,  # Set to True to hide the browser
        jira_url=os.getenv("JIRA_URL"),
        use_sso=True,
        prefer_google=True
    )
    
    # Display menu of options
    print("\nJIRA Agent Example")
    print("1. Get ticket information")
    print("2. Add a comment to the ticket")
    print("3. Change ticket status")
    print("4. Analyze ticket")
    print("5. Do all of the above")
    choice = input("\nSelect an option (1-5): ")
    
    if choice in ("1", "5"):
        # Get ticket information
        print(f"\nGetting information for ticket {ticket_id}...")
        ticket_info = agent.get_ticket(ticket_id)
        
        # Display ticket information
        print("\nTicket Information:")
        for key, value in ticket_info.items():
            if key == "_html":
                print(f"  {key}: [HTML content]")
            elif key == "comments" and isinstance(value, list):
                print(f"  {key}: {len(value)} comments")
                if value and len(value) > 0:
                    print(f"    First comment: {value[0]['text'][:100]}..." if len(value[0]['text']) > 100 else f"    First comment: {value[0]['text']}")
            elif isinstance(value, str) and len(value) > 150:
                print(f"  {key}: {value[:150]}...")
            else:
                print(f"  {key}: {value}")
        
        # Save ticket data
        save_option = input("\nSave ticket data to file? (y/n): ").lower()
        if save_option == 'y':
            file_path = agent.save_ticket_data(ticket_info)
            print(f"Ticket data saved to: {file_path}")
    
    if choice in ("2", "5"):
        # Add a comment
        comment_text = input("\nEnter comment text (leave empty to skip): ")
        if comment_text:
            print(f"Adding comment to ticket {ticket_id}...")
            result = agent.add_comment(ticket_id, comment_text)
            if result:
                print("Comment added successfully!")
            else:
                print("Failed to add comment.")
    
    if choice in ("3", "5"):
        # Change ticket status
        status_options = ["To Do", "In Progress", "Done"]
        print("\nStatus options:")
        for i, status in enumerate(status_options, 1):
            print(f"{i}. {status}")
        
        status_choice = input("Select new status (1-3, or enter custom status): ")
        try:
            new_status = status_options[int(status_choice) - 1]
        except (ValueError, IndexError):
            new_status = status_choice
            
        if new_status:
            print(f"Changing status of ticket {ticket_id} to '{new_status}'...")
            result = agent.change_status(ticket_id, new_status)
            if result:
                print("Status changed successfully!")
            else:
                print("Failed to change status.")
    
    if choice in ("4", "5"):
        # Analyze ticket
        print(f"\nAnalyzing ticket {ticket_id}...")
        
        # You can specify an API endpoint here if you have one
        analysis_endpoint = input("Enter API endpoint for analysis (leave empty to skip): ")
        
        if analysis_endpoint:
            analysis_results = agent.analyze_ticket(ticket_id, analysis_endpoint=analysis_endpoint)
        else:
            analysis_results = agent.analyze_ticket(ticket_id)
            
        print("\nAnalysis Results:")
        for key, value in analysis_results.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")
    
    print("\nJIRA example completed!")
    
if __name__ == "__main__":
    main() 
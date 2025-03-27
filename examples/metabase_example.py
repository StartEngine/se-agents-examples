"""
Example demonstrating how to use the Metabase agent for running SQL queries and downloading results.

This example shows how to:
1. Initialize the Metabase agent
2. Log in to Metabase
3. Create a new SQL question
4. Run a query on a specific database
5. Download results as CSV
"""

import os
from pathlib import Path
from app.metabase_agent.metabase import MetabaseAgent

def run_investment_report():
    """
    Connects to Metabase, runs a query to get recent investments, and downloads the results.
    
    Returns:
        str: Path to the downloaded CSV file
    """
    print("Connecting to Metabase and running investment report...")
    
    # SQL query to get investments from the last 2 weeks
    query = """
select i.id, i.offering_id, i.status, i.amount, i.request_platform, i.created_date
from primary_facade.investment i
where i.created_date > now() - interval '2 week'
order by i.created_date;
"""

    
    # Create a directory for downloads if it doesn't exist
    downloads_dir = Path.cwd() / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    
    # Initialize the Metabase agent
    # Set headless=False to see the browser UI during automation
    agent = MetabaseAgent(headless=False)
    
    # Run the query and download results
    file_path = agent.run_query_and_download(
        sql_query=query,
        database="primary_facade",
        download_path=str(downloads_dir)
    )
    
    return file_path

if __name__ == "__main__":
    # Run the example
    result_file = run_investment_report()
    
    print("\nInvestment report completed!")
    print(f"Results saved to: {result_file}")
    
    print("\nNote: This example demonstrates browser automation with Metabase.")
    print("The exact UI interaction coordinates will need adjustment based on the actual Metabase interface.")

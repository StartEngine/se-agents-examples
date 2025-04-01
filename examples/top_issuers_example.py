"""
Example demonstrating how to retrieve top offerings by amount raised using the Metabase agent.

This example shows how to:
1. Initialize the Metabase agent
2. Run a SQL query against the primary facade database through Metabase
3. Process and display the results to console
"""

import os
import sys
import csv
from pathlib import Path
from dotenv import load_dotenv
from app.metabase_agent.metabase import MetabaseAgent

# Load environment variables from creds.env
load_dotenv(dotenv_path="creds.env", override=True)

def get_top_offerings(limit=10, headless=False):
    """
    Retrieves the top offerings by amount raised from the primary facade database using Metabase.
    
    Args:
        limit (int): Number of top offerings to retrieve
        headless (bool): Whether to run the browser in headless mode
        
    Returns:
        list: List of dictionaries containing offering information
    """
    print(f"Fetching top {limit} offerings by amount raised via Metabase...")
    
    # Check if Metabase credentials are set
    if not os.getenv("METABASE_USERNAME") or not os.getenv("METABASE_PASSWORD"):
        print("Error: Metabase credentials are not set.")
        print("Please ensure the following environment variables are set in creds.env:")
        print("  - METABASE_USERNAME")
        print("  - METABASE_PASSWORD")
        return []
    
    # Create the SQL query for top offerings
    query = f"""
    select o.slug, oarc.amount_raised
    from primary_facade.offering o
    join primary_facade.offering_amount_raised_cache oarc on o.id = oarc.offering_id
    where o.status = 'APPROVED'
    order by oarc.amount_raised DESC
    LIMIT {limit}
    """
    
    try:
        # Use the specific downloads directory path
        downloads_dir = Path("/Users/jordanjahja/Downloads")
        # Ensure the directory exists
        if not downloads_dir.exists():
            print(f"Warning: Downloads directory {downloads_dir} does not exist. Creating it...")
            downloads_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize the Metabase agent
        agent = MetabaseAgent(headless=headless)
        
        # Run the query and download results directly to Downloads folder
        csv_file_path = agent.run_query_and_download(
            sql_query=query,
            database="primary_facade",
            download_path=str(downloads_dir)
        )
        
        if not csv_file_path or not Path(csv_file_path).exists():
            print("Error: Failed to download query results.")
            return []
        
        print(f"\nMetabase results saved to: {csv_file_path}")
        
        # Process the CSV file
        return process_csv_results(csv_file_path)
    
    except Exception as e:
        print(f"Error running Metabase query: {e}")
        return []

def process_csv_results(csv_file_path):
    """
    Process the CSV file downloaded from Metabase.
    
    Args:
        csv_file_path (str): Path to the CSV file
        
    Returns:
        list: List of dictionaries containing offering information
    """
    results = []
    
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Create the CSV reader
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                # Get slug and amount_raised from the CSV
                slug = row['slug']
                
                # Remove commas and convert to float
                amount_str = row['amount_raised'].replace(',', '')
                try:
                    amount_raised = float(amount_str)
                except ValueError:
                    # Handle any remaining formatting issues
                    amount_raised = 0
                    print(f"Warning: Could not convert '{row['amount_raised']}' to a number")
                
                formatted_row = {
                    'slug': slug,
                    'amount_raised': amount_raised,
                    'amount_raised_formatted': "${:,.2f}".format(amount_raised)
                }
                
                results.append(formatted_row)
            
            return results
    
    except Exception as e:
        print(f"Error processing CSV results: {e}")
        return []

if __name__ == "__main__":
    # Get command line arguments
    limit = 10
    headless = False
    
    # Parse limit argument
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            print(f"Invalid limit value: {sys.argv[1]}. Using default limit of 10.")
    
    # Parse headless argument (if provided)
    if len(sys.argv) > 2:
        headless_arg = sys.argv[2].lower()
        if headless_arg in ('true', 't', 'yes', 'y', '1'):
            headless = True
    
    # Get top offerings
    top_offerings = get_top_offerings(limit, headless)
    
    if top_offerings:
        print(f"\nTop {len(top_offerings)} Offerings by Amount Raised:")
        print("-" * 60)
        for i, offering in enumerate(top_offerings, 1):
            print(f"{i}. {offering['slug']}")
            print(f"   Amount Raised: {offering['amount_raised_formatted']}")
            print("-" * 60)
        
        # Calculate and print summary statistics
        total_amount = sum(offering['amount_raised'] for offering in top_offerings)
        print(f"\nSummary:")
        print(f"  Total Amount Raised: ${total_amount:,.2f}")
        print(f"  Average Raise per Offering: ${total_amount/len(top_offerings):,.2f}")
    else:
        print("\nNo results found or error with Metabase query.")
        print("Please check your Metabase credentials and try again.")
    
    print("\nUsage:")
    print("  python -m examples.top_issuers_example [limit] [headless]")
    print("  - limit: Number of offerings to retrieve (default: 10)")
    print("  - headless: Run without browser UI (true/false, default: false)")
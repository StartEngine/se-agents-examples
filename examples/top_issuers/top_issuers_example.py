"""
Example demonstrating how to retrieve top offerings by amount raised using the Metabase agent.

This example shows how to:
1. Initialize the Metabase session
2. Run a SQL query against the primary facade database through Metabase
3. Process and display the results to console
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from creds.env
load_dotenv(dotenv_path="creds.env", override=True)

# Import our modular components
from .metabase_session import PersistentMetabaseSession
from .queries import QUERIES, QUERY_FIELD_MAPPING
from .utils.sql_formatter import clean_sql_query
from .utils.csv_processor import process_csv_results
from .formatters import print_detailed_offerings_summary

def run_metabase_query(session, query, temp_dir):
    """
    Runs a query against Metabase and returns the processed results.
    
    Args:
        session: The PersistentMetabaseAgent to use
        query (str): The SQL query to run
        temp_dir (str): The directory to save the results to
        
    Returns:
        list: List of processed results from the query
    """
    # Make sure temp_dir is a string path, not a Path object
    if isinstance(temp_dir, Path):
        temp_dir = str(temp_dir)
        
    try:
        # Run the query and download results to temp directory
        csv_file_path = session.run_query(
            sql_query=query,
            database="primary_facade",
            download_path=temp_dir
        )
        
        if not csv_file_path or not Path(csv_file_path).exists():
            print("Error: Failed to download query results.")
            return []
        
        # Process the CSV file
        return process_csv_results(csv_file_path)
        
    except Exception as e:
        print(f"Error running Metabase query: {e}")
        return []

def get_offering_data(session, slug, temp_dir, amount_raised=None, amount_raised_formatted=None):
    """
    Get all data for a specific offering by running multiple queries.
    
    Args:
        session: The PersistentMetabaseAgent to use
        slug (str): The offering slug to get data for
        temp_dir (str): Temporary directory to store downloads
        amount_raised (float, optional): Already known amount raised
        amount_raised_formatted (str, optional): Formatted amount raised
        
    Returns:
        dict: All data for the offering
    """
    # Initialize with slug and any pre-known amount raised
    offering_data = {'slug': slug}
    if amount_raised is not None:
        offering_data['amount_raised'] = amount_raised
        offering_data['amount_raised_formatted'] = amount_raised_formatted or "${:,.2f}".format(amount_raised)
    
    print(f"Gathering complete data for {slug}...")
    
    # Setup for dynamic queries
    PER_OFFERING_QUERIES = {
        k: v for k, v in QUERIES.items()
        if k != "top_offerings_by_amount_raised" and "{slug}" in v
    }
    
    try:
        # The issue is with double-quoting in the SQL queries
        # We need to ensure the slug is properly quoted in the SQL
        # For PostgreSQL, string values should be surrounded by single quotes
        quoted_slug = f"'{slug}'"
        
        # Dynamically run all queries for this offering
        for query_key, query_sql in PER_OFFERING_QUERIES.items():
            # Skip if this query key isn't in our mapping
            if query_key not in QUERY_FIELD_MAPPING:
                continue
                
            # Print user-friendly query description - for combined queries just use the query key
            print(f"  - Getting data for {query_key.replace('offering_', '').replace('_', ' ')}...")
                
            # Format and clean the query for better compatibility
            raw_query = query_sql.format(slug=quoted_slug)
            query = clean_sql_query(raw_query)
            print(f"DEBUG - Query being sent: {query}")
            
            # Run the query
            results = run_metabase_query(session, query, temp_dir)
            
            # Process results
            if results and len(results) > 0:
                # Process the combined query results
                column_mappings = QUERY_FIELD_MAPPING.get(query_key, {})
                
                if column_mappings:
                    # For combined queries, process each column with its mapping
                    for column, mapping in column_mappings.items():
                        field_name = mapping["field_name"]
                        is_currency = mapping["is_currency"]
                        
                        # Get the value from the results
                        value = results[0].get(column, 0)
                        
                        # Store the raw value
                        offering_data[field_name] = value
                        
                        # For currency fields, add a formatted version
                        if is_currency:
                            formatted_value = "${:,.2f}".format(float(value) if value else 0)
                            offering_data[f"{field_name}_formatted"] = formatted_value
        
        return offering_data
        
    except Exception as e:
        print(f"Error getting data for {slug}: {e}")
        return offering_data

def main(limit=10, headless=False):
    """
    Main function to orchestrate the top offerings data collection.
    
    Args:
        limit (int): Number of top offerings to retrieve
        headless (bool): Whether to run in headless mode
    """
    # Check if Metabase credentials are set
    if not os.getenv("METABASE_USERNAME") or not os.getenv("METABASE_PASSWORD"):
        print("Error: Metabase credentials are not set.")
        print("Please ensure the following environment variables are set in creds.env:")
        print("  - METABASE_USERNAME")
        print("  - METABASE_PASSWORD")
        return 1
        
    try:
        # Create a temporary directory for all downloads
        with tempfile.TemporaryDirectory() as temp_dir:
            # Use a single persistent Metabase session for all queries
            with PersistentMetabaseSession(headless=headless) as session:
                # First, get the list of top offerings with their amount raised
                print("\nFetching top offerings by amount raised...")
                raw_query = QUERIES["top_offerings_by_amount_raised"].format(limit=limit)
                query = clean_sql_query(raw_query)
                print(f"DEBUG - Query being sent: {query}")
                top_offerings_with_data = run_metabase_query(session, query, temp_dir)
                
                if not top_offerings_with_data:
                    print("No offerings found. Check your query and try again.")
                    return 1
                    
                # Extract the slugs and create a map of slug to amount raised
                top_slugs = []
                slug_to_amount = {}
                
                for offering in top_offerings_with_data:
                    slug = offering.get('slug')
                    if slug:
                        top_slugs.append(slug)
                        slug_to_amount[slug] = {
                            'amount_raised': offering.get('amount_raised', 0),
                            'amount_raised_formatted': offering.get('amount_raised_formatted', '$0.00')
                        }
                
                print(f"Found {len(top_slugs)} top offerings: {', '.join(top_slugs)}")
                
                # Initialize a dictionary to store all offering data
                all_offerings_data = {}
                
                # Process each slug one by one, gathering all data
                print("\nRetrieving detailed data for each offering...")
                
                # Process each offering with the known amount_raised
                for i, slug in enumerate(top_slugs, 1):
                    print(f"\n[{i}/{len(top_slugs)}] Processing offering: {slug}")
                    
                    # Get the pre-known amount raised
                    amount_data = slug_to_amount.get(slug, {})
                    amount_raised = amount_data.get('amount_raised')
                    amount_raised_formatted = amount_data.get('amount_raised_formatted')
                    
                    # Get all detailed data for this offering
                    offering_data = get_offering_data(
                        session,
                        slug,
                        temp_dir,
                        amount_raised=amount_raised,
                        amount_raised_formatted=amount_raised_formatted
                    )
                    
                    # Store the complete data for this offering
                    all_offerings_data[slug] = offering_data
            
            # After all offerings have been processed, print a final summary
            print_detailed_offerings_summary(all_offerings_data)
            
        return 0
            
    except Exception as e:
        print(f"Error running script: {e}")
        print("Full error details:")
        traceback.print_exc()
        return 1

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
    
    # Call the main function
    sys.exit(main(limit=limit, headless=headless))
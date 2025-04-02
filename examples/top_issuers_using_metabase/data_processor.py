"""
Data processing module for top issuers data collection.
"""

import base64
import time
from pathlib import Path

from .queries import QUERY_FIELD_MAPPING, get_per_offering_queries
from .utils.sql_formatter import clean_sql_query

def run_metabase_query(session, query, temp_dir):
    """
    Runs a query against Metabase and returns the processed results.
    
    Args:
        session: The PersistentMetabaseSession to use
        query (str): The SQL query to run
        temp_dir (str): The directory to save the results to
        
    Returns:
        list: List of processed results from the query
    """
    # Make sure temp_dir is a string path, not a Path object
    if isinstance(temp_dir, Path):
        temp_dir = str(temp_dir)
        
    try:
        # Initialize the session first (ensure we're logged in)
        session.initialize_session()
        
        # Run the query and download results to temp directory
        csv_file_path = session.run_query(
            sql_query=query,
            database="primary_facade",
            download_path=temp_dir
        )
        
        if not csv_file_path or not Path(csv_file_path).exists():
            print("Error: Failed to download query results.")
            return []
        
        # Import here to avoid circular imports
        from .utils.csv_processor import process_csv_results
        
        # Process the CSV file
        return process_csv_results(csv_file_path)
        
    except Exception as e:
        print(f"Error running Metabase query: {e}")
        # Try to take a screenshot to help debug the issue
        try:
            if session.browser:
                timestamp = int(time.time())
                screenshot_path = Path(temp_dir) / f"error_screenshot_{timestamp}.png"
                screenshot = session.browser.screenshot()
                with open(screenshot_path, "wb") as f:
                    f.write(base64.b64decode(screenshot))
                print(f"Error screenshot saved to: {screenshot_path}")
        except Exception as screenshot_error:
            print(f"Could not take error screenshot: {screenshot_error}")
        return []

def get_offering_data(session, slug, temp_dir, amount_raised=None, amount_raised_formatted=None):
    """
    Get all data for a specific offering by running multiple queries.
    
    Args:
        session: The PersistentMetabaseSession to use
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
    PER_OFFERING_QUERIES = get_per_offering_queries()
    
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
                
            # Get field name and currency flag from mapping
            field_name, is_currency = QUERY_FIELD_MAPPING.get(query_key, (None, False))
            if not field_name:
                continue
                
            # Print user-friendly query description
            print(f"  - Getting {field_name.replace('_', ' ')}...")
                
            # Format and clean the query for better compatibility
            raw_query = query_sql.format(slug=quoted_slug)
            query = clean_sql_query(raw_query)
            print(f"DEBUG - Query being sent: {query}")
            
            # Run the query
            results = run_metabase_query(session, query, temp_dir)
            
            # Process results
            if results and len(results) > 0:
                # Get the first result value, looking for either 'number_of_investors' or 'amount_raised'
                # based on the query type
                value_key = 'amount_raised' if is_currency else 'number_of_investors'
                value = results[0].get(value_key, 0)
                
                # Store the raw value
                offering_data[field_name] = value
                
                # For currency fields, add a formatted version
                if is_currency:
                    formatted_value = "${:,.2f}".format(float(value) if value else 0)
                    offering_data[f"{field_name}_formatted"] = formatted_value
        
        from .formatters import print_offering_summary
        print_offering_summary(offering_data)
        
        return offering_data
        
    except Exception as e:
        print(f"Error getting data for {slug}: {e}")
        return offering_data
# Top Issuers Example

This directory contains a modular example that demonstrates how to retrieve and visualize offering data from the Metabase database using browser automation with a persistent session.

## Code Flow Overview

The top_issuers_example.py demonstrates a streamlined approach to retrieving and presenting offering data using a persistent Metabase browser session. Here's how it works:

1. **Setup and Initialization**
   - Loads environment variables for Metabase credentials
   - Creates a temporary directory for CSV downloads
   - Establishes a single persistent browser session with PersistentMetabaseSession

2. **Top Offerings Query**
   - Runs an initial query to get top offerings by amount raised
   - Processes and extracts slugs and basic offering data
   - Creates a mapping of slug to amount raised for reference

3. **Per-Offering Data Collection**
   - For each slug, dynamically runs a set of predefined queries:
     - offering_amount_raises (total, 7-day, 30-day)
     - offering_number_of_investors (total, 7-day, 30-day)
     - offering_followers (total, 7-day, 30-day)
     - offering_updates (7-day, 30-day)
   - Handles SQL query formatting with proper slug quoting
   - Stores all results in a structured offering_data dictionary

4. **Data Processing**
   - CSV results are processed via csv_processor.py
   - Numeric values are identified and converted
   - Currency values get formatted versions ($XXX.XX)
   - Each offering's data is consolidated into a complete profile

5. **Field Mapping System**
   - Uses a QUERY_FIELD_MAPPING dictionary to map database columns to application fields
   - Determines which fields are currency values
   - Handles combined queries by mapping multiple columns to different fields

6. **Output Formatting**
   - Structures output into logical sections (totals, 7-day, 30-day)
   - Calculates aggregate metrics across all offerings
   - Provides both summary and detailed views

7. **Browser Automation**
   - PersistentMetabaseSession maintains a single browser session
   - Handles login, navigation, query execution, and result download
   - Uses multiple selector fallbacks for reliable element targeting
   - Captures screenshots on errors for debugging

## Key Components

- **metabase_session.py**: Implements PersistentMetabaseSession for browser automation
- **queries.py**: Contains SQL query definitions and field mappings
- **formatters.py**: Provides output formatting utilities
- **utils/csv_processor.py**: Processes CSV results from Metabase
- **utils/sql_formatter.py**: Ensures SQL queries are properly formatted
- **top_issuers_example.py**: Main script that orchestrates the entire process

## Usage

To run the example:

```bash
python -m examples.top_issuers.top_issuers_example [limit] [headless]
```

- `limit`: Number of top offerings to retrieve (default: 10)
- `headless`: Set to "true" to run in headless mode without visible browser

## Adding New Queries

To add a new query:

1. Add the SQL query to the `QUERIES` dictionary in queries.py
2. Add a field mapping to the `QUERY_FIELD_MAPPING` dictionary
3. Update the formatters.py file to display the new fields

Example:

```python
# In queries.py
QUERIES = {
    # Existing queries...
    "new_query_name": """
        SELECT ...
        FROM ...
        WHERE ...
    """
}

QUERY_FIELD_MAPPING = {
    # Existing mappings...
    "new_query_name": {
        "column_name": {"field_name": "app_field_name", "is_currency": False}
    }
}
```

## Important Considerations

- **Persistent Session**: The browser session remains active for all queries, avoiding repeated logins
- **Selector Fallbacks**: Multiple selector strategies are used for reliable element targeting
- **Error Handling**: Screenshots are captured on errors and empty files are created as fallbacks
- **Flexible Field Mapping**: The mapping system can handle various query result structures

## Dependencies

- Playwright for browser automation
- Python-dotenv for environment variable management
- CSV module for processing downloads
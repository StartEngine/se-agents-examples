"""
CSV processing utilities for Metabase query results.
"""

import os
import csv
import re
from datetime import datetime

def process_csv_results(csv_file_path):
    """
    Process the CSV file downloaded from Metabase.
    
    Args:
        csv_file_path (str): Path to the CSV file
        
    Returns:
        list: List of dictionaries containing query results
    """
    results = []
    file_name = os.path.basename(csv_file_path)
    file_size = os.path.getsize(csv_file_path) / 1024  # Size in KB
    
    print(f"Processing Metabase CSV file: {file_name} ({file_size:.2f} KB)")
    
    try:
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as csvfile:
            # Read the content for feedback
            content = csvfile.read()
            line_count = content.count('\n') + 1
            print(f"  - CSV contains {line_count} lines (including header)")
            csvfile.seek(0)  # Reset file pointer to beginning
            
            # Create the CSV reader
            reader = csv.DictReader(csvfile)
            
            # Get columns for feedback
            columns = reader.fieldnames
            print(f"  - CSV columns: {', '.join(columns)}")
            
            row_count = 0
            for row in reader:
                row_count += 1
                # Copy the row so we can modify it
                processed_row = {}
                
                # Process each column
                for col, value in row.items():
                    # Skip empty or None values
                    if not value or value == 'null':
                        processed_row[col] = None
                        continue
                    
                    # Try to convert to float if the column looks like a number or contains specific terms
                    numeric_cols = [
                        'amount_raised', 'amount', 'number_of_investors', 'total_raised', 
                        'raised_past_7_days', 'raised_past_30_days', 'total_investors',
                        'investors_past_7_days', 'investors_past_30_days', 'total_followers',
                        'followers_past_7_days', 'followers_past_30_days', 'updates_past_7_days',
                        'updates_past_30_days'
                    ]
                    
                    # Date fields to format
                    date_cols = ['start_date', 'closing_date', 'funding_start_date', 'funding_end_date']
                    
                    # Boolean fields to convert
                    bool_cols = ['closing_soon', 'new_launch']
                    
                    if any(term in col.lower() for term in numeric_cols) or 'count' in col.lower() or 'total' in col.lower() or 'raised' in col.lower() or 'investors' in col.lower():
                        # Remove commas from numbers
                        clean_value = value.replace(',', '')
                        try:
                            processed_row[col] = float(clean_value)
                            # For amount/money columns, also add formatted version
                            if any(term in col.lower() for term in ['amount', 'raised', 'total_raised', 'raised_past']):
                                processed_row[f"{col}_formatted"] = "${:,.2f}".format(float(clean_value))
                        except ValueError:
                            # If not a number, keep as string
                            processed_row[col] = value
                            print(f"Warning: Could not convert '{value}' to a number for column '{col}'")
                    elif col in date_cols or any(date_term in col.lower() for date_term in ['date', '_at', '_on']):
                        # Try to parse as date/timestamp in standard formats
                        try:
                            # Check for ISO format or common postgres timestamp format
                            if 'T' in value and re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}', value):
                                # ISO format
                                dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                                processed_row[col] = dt.strftime('%Y-%m-%d %H:%M:%S')
                            elif re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}', value):
                                # Postgres timestamp
                                dt = datetime.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
                                processed_row[col] = dt.strftime('%Y-%m-%d %H:%M:%S') 
                            elif re.match(r'\d{4}-\d{2}-\d{2}', value):
                                # Just date
                                dt = datetime.strptime(value.split('T')[0], '%Y-%m-%d')
                                processed_row[col] = dt.strftime('%Y-%m-%d')
                            else:
                                # If we can't parse, keep as is
                                processed_row[col] = value
                        except (ValueError, TypeError):
                            # If it doesn't parse as a date, keep as string
                            processed_row[col] = value
                    elif col in bool_cols or col.endswith('_flag') or col.startswith('is_'):
                        # Convert to proper boolean
                        if value.lower() in ('t', 'true', 'yes', 'y', '1'):
                            processed_row[col] = True
                        elif value.lower() in ('f', 'false', 'no', 'n', '0'):
                            processed_row[col] = False
                        else:
                            # If not a recognized boolean value, keep as string
                            processed_row[col] = value
                    else:
                        # Keep non-numeric values as strings
                        processed_row[col] = value
                
                results.append(processed_row)
            
            print(f"  - Processed {row_count} rows from {file_name}")
            return results
    
    except Exception as e:
        print(f"Error processing CSV results: {e}")
        return []
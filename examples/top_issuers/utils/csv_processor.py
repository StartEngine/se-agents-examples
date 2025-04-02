"""
CSV processing utilities for Metabase query results.
"""

import os
import csv

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
                    
                    # Try to convert to float if the column looks like a number
                    if col.lower() in ('amount_raised', 'amount', 'number_of_investors') or 'count' in col.lower():
                        # Remove commas from numbers
                        clean_value = value.replace(',', '')
                        try:
                            processed_row[col] = float(clean_value)
                            # For amount columns, also add formatted version
                            if 'amount' in col.lower() or 'raised' in col.lower():
                                processed_row[f"{col}_formatted"] = "${:,.2f}".format(float(clean_value))
                        except ValueError:
                            # If not a number, keep as string
                            processed_row[col] = value
                            print(f"Warning: Could not convert '{value}' to a number for column '{col}'")
                    else:
                        # Keep non-numeric values as strings
                        processed_row[col] = value
                
                results.append(processed_row)
            
            print(f"  - Processed {row_count} rows from {file_name}")
            return results
    
    except Exception as e:
        print(f"Error processing CSV results: {e}")
        return []
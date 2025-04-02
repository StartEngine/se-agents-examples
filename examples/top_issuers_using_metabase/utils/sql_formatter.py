"""
SQL query formatting utilities for Metabase compatibility.
"""

import re

def clean_sql_query(query):
    """
    Clean and format a SQL query for better readability and compatibility with Metabase.
    Specifically handles the interval syntax correctly for PostgreSQL.
    
    Args:
        query (str): The raw SQL query
        
    Returns:
        str: Cleaned SQL query
    """
    # Remove extra whitespace
    clean = query.strip()
    
    # Remove leading/trailing newlines
    clean = clean.strip('\n')
    
    # Preserve interval expressions like 'now() - interval '7 days'' by temporarily replacing them
    # This ensures we don't break the interval syntax when formatting
    interval_pattern = r'(now\(\)\s*-\s*interval\s*\'[^\']*\')'
    interval_replacements = {}
    
    for i, match in enumerate(re.finditer(interval_pattern, clean, re.IGNORECASE)):
        placeholder = f"__INTERVAL_PLACEHOLDER_{i}__"
        interval_replacements[placeholder] = match.group(0)
        clean = clean.replace(match.group(0), placeholder)
    
    # Also preserve other special operators like >=, <=, != etc.
    compound_ops = ['>=', '<=', '!=', '<>', '==']
    op_replacements = {}
    
    for i, op in enumerate(compound_ops):
        placeholder = f"__OP_PLACEHOLDER_{i}__"
        op_replacements[placeholder] = op
        clean = clean.replace(op, placeholder)
    
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean)
    
    # Now add spacing around basic operators
    for op in ['=', '<', '>', '+', '-', '*', '/', '%']:
        clean = clean.replace(op, f' {op} ')
    
    # Re-normalize whitespace
    clean = re.sub(r'\s+', ' ', clean)
    
    # Fix double spaces
    while '  ' in clean:
        clean = clean.replace('  ', ' ')
    
    # Put back the compound operators with proper spacing
    for placeholder, op in op_replacements.items():
        # First remove any spaces around the placeholder
        clean = re.sub(f"\\s*{re.escape(placeholder)}\\s*", f" {op} ", clean)
    
    # Properly format interval expressions in a way that works with PostgreSQL
    for placeholder, interval in interval_replacements.items():
        # Format the interval expression with proper spacing
        # First remove the placeholder with its surroundings
        clean = re.sub(f"\\s*{re.escape(placeholder)}\\s*", " " + interval + " ", clean)
    
    # Fix any spacing issues that might have been created
    clean = re.sub(r'\s+', ' ', clean)
    while '  ' in clean:
        clean = clean.replace('  ', ' ')
        
    # Ensure intervals are properly formatted
    # PostgreSQL requires the syntax: INTERVAL '7 days'
    clean = re.sub(r'INTERVAL\s+\'', 'INTERVAL \'', clean)
    
    # Special debugging for interval syntax
    if 'INTERVAL' in clean:
        print("DEBUG - Interval syntax check:")
        interval_matches = re.findall(r'(INTERVAL\s*\'[^\']*\')', clean)
        for i, match in enumerate(interval_matches):
            print(f"  Interval {i+1}: '{match}'")
            # Ensure proper format: INTERVAL '7 days'
            if not re.match(r'INTERVAL\s*\'[^\']+\'', match):
                print(f"  WARNING: Interval {i+1} might have incorrect format")
                # Try to fix it
                fixed = re.sub(r'INTERVAL\s*\'', 'INTERVAL \'', match)
                clean = clean.replace(match, fixed)
                print(f"  Fixed to: '{fixed}'")
        
    # Finally, ensure compound operators are correct
    for op in ['>=', '<=', '<>', '!=']:
        # Fix any broken compound operators like > = or < =
        broken_op = ' '.join(list(op))
        if broken_op in clean:
            print(f"DEBUG - Found broken operator: '{broken_op}'")
            clean = clean.replace(broken_op, op)
            print(f"DEBUG - Fixed to: '{op}'")
    
    # Replace SQL keywords with uppercase for readability
    sql_keywords = [
        'select', 'from', 'where', 'join', 'left join', 'right join', 'inner join',
        'group by', 'order by', 'having', 'limit', 'and', 'or', 'not', 'in', 'between',
        'union', 'insert', 'update', 'delete', 'create', 'alter', 'drop', 'interval'
    ]
    
    for keyword in sql_keywords:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + keyword + r'\b'
        clean = re.sub(pattern, keyword.upper(), clean, flags=re.IGNORECASE)
    
    return clean
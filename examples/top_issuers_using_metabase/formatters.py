"""
Formatting and display utilities for offering data.
"""

import re
from datetime import datetime

def safe_int(val, default=0):
    """Convert a value to int, handling None values and exceptions."""
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default
        
def safe_float(val, default=0.0):
    """Convert a value to float, handling None values and exceptions."""
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def print_offering_summary(offering_data):
    """
    Print summary data for a single offering.
    
    Args:
        offering_data (dict): Data for a single offering
    """
    slug = offering_data.get('slug', 'unknown')
    name = offering_data.get('name', slug)  # Use name as primary identifier, fallback to slug
    print(f"\nData for {name}:")
    
    # Display status indicators
    if offering_data.get('new_launch'):
        print(f"  ⭐ NEW LAUNCH")
    if offering_data.get('closing_soon'):
        print(f"  ⚠️ CLOSING SOON")
    
    # Display dates with more user-friendly format
    if 'start_date' in offering_data:
        start_date = offering_data.get('start_date')
        try:
            if isinstance(start_date, str) and re.match(r'\d{4}-\d{2}-\d{2}', start_date):
                formatted_date = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d').strftime('%B %d, %Y')
                print(f"  Start date: {formatted_date}")
            else:
                print(f"  Start date: {start_date}")
        except Exception:
            print(f"  Start date: {start_date}")
            
    if 'closing_date' in offering_data:
        closing_date = offering_data.get('closing_date')
        try:
            if isinstance(closing_date, str) and re.match(r'\d{4}-\d{2}-\d{2}', closing_date):
                formatted_date = datetime.strptime(closing_date.split(' ')[0], '%Y-%m-%d').strftime('%B %d, %Y')
                print(f"  Closing date: {formatted_date}")
            else:
                print(f"  Closing date: {closing_date}")
        except Exception:
            print(f"  Closing date: {closing_date}")
    
    # Display total amount raised if available
    if 'amount_raised_formatted' in offering_data:
        print(f"  Total amount raised: {offering_data.get('amount_raised_formatted', '$0.00')}")
    
    # Display amount raised metrics
    for period in ['7d', '30d']:
        field_name = f'amount_raised_{period}'
        if field_name in offering_data:
            display_name = f"Amount raised ({period.replace('d', ' days')})"
            formatted_field = f"{field_name}_formatted"
            if formatted_field in offering_data:
                print(f"  {display_name}: {offering_data.get(formatted_field, '$0.00')}")
            else:
                value = offering_data.get(field_name, 0)
                print(f"  {display_name}: ${safe_float(value):,.2f}")
    
    # Display investor metrics
    if 'investors_total' in offering_data:
        print(f"  Total investors: {safe_int(offering_data.get('investors_total', 0)):,}")
    
    for period in ['7d', '30d']:
        field_name = f'investors_{period}'
        if field_name in offering_data:
            display_name = f"Investors ({period.replace('d', ' days')})"
            print(f"  {display_name}: {safe_int(offering_data.get(field_name, 0)):,}")
    
    print("-" * 80)

def print_offerings_data(offerings_dict):
    """
    Print offering data from a dictionary.
    
    Args:
        offerings_dict: Dictionary with slugs as keys and offering data as values
    """
    if not offerings_dict:
        print("\nNo results found.")
        return
    
    # Calculate and store total amount
    total_amount = sum(safe_float(data.get('amount_raised', 0)) for data in offerings_dict.values())
    
    # Print header
    print(f"\nTop {len(offerings_dict)} Offerings by Amount Raised:")
    print("-" * 100)
    
    # Sort by amount raised (descending) and print
    sorted_slugs = sorted(
        offerings_dict.keys(), 
        key=lambda slug: safe_float(offerings_dict[slug].get('amount_raised', 0)), 
        reverse=True
    )
    
    # Print each offering with all available details
    for i, slug in enumerate(sorted_slugs, 1):
        data = offerings_dict[slug]
        offering_name = data.get('name', slug)  # Use name as primary identifier, fallback to slug
        print(f"{i}. {offering_name}")
        
        # Status indicators
        status_tags = []
        if data.get('new_launch'):
            status_tags.append("⭐ NEW LAUNCH")
        if data.get('closing_soon'):
            status_tags.append("⚠️ CLOSING SOON")
            
        if status_tags:
            print(f"   Status: {', '.join(status_tags)}")
        
        # Dates with nicer formatting
        if 'start_date' in data:
            start_date = data.get('start_date')
            try:
                if isinstance(start_date, str) and re.match(r'\d{4}-\d{2}-\d{2}', start_date):
                    formatted_date = datetime.strptime(start_date.split(' ')[0], '%Y-%m-%d').strftime('%B %d, %Y')
                    print(f"   Start Date: {formatted_date}")
                else:
                    print(f"   Start Date: {start_date}")
            except Exception:
                print(f"   Start Date: {start_date}")
                
        if 'closing_date' in data:
            closing_date = data.get('closing_date')
            try:
                if isinstance(closing_date, str) and re.match(r'\d{4}-\d{2}-\d{2}', closing_date):
                    formatted_date = datetime.strptime(closing_date.split(' ')[0], '%Y-%m-%d').strftime('%B %d, %Y')
                    print(f"   Closing Date: {formatted_date}")
                else:
                    print(f"   Closing Date: {closing_date}")
            except Exception:
                print(f"   Closing Date: {closing_date}")
        
        # Print all available data for this offering
        if 'amount_raised' in data:
            print(f"   Total Amount Raised: {data.get('amount_raised_formatted', '$0.00')}")
        
        # 7-day metrics
        if 'amount_raised_7d' in data:
            print(f"   Amount Raised (7 days): {data.get('amount_raised_7d_formatted', '$0.00')}")
        if 'investors_7d' in data:
            print(f"   Investors (7 days): {safe_int(data.get('investors_7d', 0)):,}")
        if 'followers_7d' in data:
            print(f"   Followers (7 days): {safe_int(data.get('followers_7d', 0)):,}")
        if 'updates_7d' in data:
            print(f"   Updates (7 days): {safe_int(data.get('updates_7d', 0)):,}")
            
        # 30-day metrics
        if 'amount_raised_30d' in data:
            print(f"   Amount Raised (30 days): {data.get('amount_raised_30d_formatted', '$0.00')}")
        if 'investors_30d' in data:
            print(f"   Investors (30 days): {safe_int(data.get('investors_30d', 0)):,}")
        if 'followers_30d' in data:
            print(f"   Followers (30 days): {safe_int(data.get('followers_30d', 0)):,}")
        if 'updates_30d' in data:
            print(f"   Updates (30 days): {safe_int(data.get('updates_30d', 0)):,}")
            
        # Total counts
        if 'investors_total' in data:
            print(f"   Total Investors: {safe_int(data.get('investors_total', 0)):,}")
        if 'followers_total' in data:
            print(f"   Total Followers: {safe_int(data.get('followers_total', 0)):,}")
            
        print("-" * 100)
    
    # Print summary statistics
    print(f"\nSummary:")
    print(f"  Total Amount Raised Across All Offerings: ${total_amount:,.2f}")
    if offerings_dict:
        print(f"  Average Raise per Offering: ${total_amount/len(offerings_dict):,.2f}")

def print_detailed_offerings_summary(all_offerings_data):
    """
    Print a detailed summary of all offerings data with aggregated metrics.
    
    Args:
        all_offerings_data (dict): Dictionary with slugs as keys and offering data as values
    """
    # Calculate basic metrics
    total_amount = sum(safe_float(data.get('amount_raised', 0)) for data in all_offerings_data.values())
    
    # Print header
    print("\n" + "=" * 100)
    print(f"SUMMARY OF TOP {len(all_offerings_data)} OFFERINGS")
    print("=" * 100)
    
    # Basic metrics
    print(f"Total amount raised across all offerings: ${total_amount:,.2f}")
    if all_offerings_data:
        print(f"Average raised per offering: ${total_amount/len(all_offerings_data):,.2f}")
    
    # Define summary fields
    SUMMARY_FIELD_MAPPING = {
        # Field_name: (display name, is_currency)
        'investors_total': ('Total investors across all offerings', False),
        'followers_total': ('Total followers across all offerings', False),
        'amount_raised_7d': ('Total amount raised in last 7 days', True),
        'amount_raised_30d': ('Total amount raised in last 30 days', True),
        'investors_7d': ('Total new investors in last 7 days', False),
        'investors_30d': ('Total new investors in last 30 days', False),
        'followers_7d': ('Total new followers in last 7 days', False),
        'followers_30d': ('Total new followers in last 30 days', False),
        'updates_7d': ('Total updates in last 7 days', False),
        'updates_30d': ('Total updates in last 30 days', False),
    }
    
    # Calculate totals dynamically
    totals = {}
    for field_name, (_, is_currency) in SUMMARY_FIELD_MAPPING.items():
        converter = safe_float if is_currency else safe_int
        totals[field_name] = sum(
            converter(data.get(field_name, 0)) 
            for data in all_offerings_data.values()
        )
    
    # Print aggregate metrics dynamically
    for field_name, (display_name, is_currency) in SUMMARY_FIELD_MAPPING.items():
        if field_name in totals:
            value = totals[field_name]
            if is_currency:
                print(f"{display_name}: ${value:,.2f}")
            else:
                print(f"{display_name}: {value:,}")
    
    # Print detailed offering information
    print_detailed_offering_list(all_offerings_data)
    
def print_detailed_offering_list(all_offerings_data):
    """
    Print detailed information for each offering with consistent formatting.
    
    Args:
        all_offerings_data (dict): Dictionary with slugs as keys and offering data as values
    """
    # Sort offerings by amount raised (high to low)
    sorted_slugs = sorted(
        all_offerings_data.keys(),
        key=lambda s: safe_float(all_offerings_data[s].get('amount_raised', 0)),
        reverse=True
    )
    
    # Define display groups for the detailed offering view
    DISPLAY_GROUPS = {
        'total': {
            'title': None,  # Top level doesn't need a title
            'fields': [
                ('amount_raised', 'Total Amount Raised', True),
                ('investors_total', 'Total Investors', False),
                ('followers_total', 'Total Followers', False)
            ]
        },
        'dates': {
            'title': 'Dates:',
            'fields': [
                ('start_date', 'Start Date', False, True),  # Added date formatting flag
                ('closing_date', 'Closing Date', False, True)  # Added date formatting flag
            ]
        },
        'status': {
            'title': 'Status:',
            'fields': [
                ('new_launch', 'New Launch', False),
                ('closing_soon', 'Closing Soon', False)
            ]
        },
        '7d': {
            'title': 'Last 7 Days:',
            'fields': [
                ('amount_raised_7d', 'Amount Raised', True),
                ('investors_7d', 'New Investors', False),
                ('followers_7d', 'New Followers', False),
                ('updates_7d', 'Updates', False)
            ]
        },
        '30d': {
            'title': 'Last 30 Days:',
            'fields': [
                ('amount_raised_30d', 'Amount Raised', True),
                ('investors_30d', 'New Investors', False),
                ('followers_30d', 'New Followers', False),
                ('updates_30d', 'Updates', False)
            ]
        }
    }
    
    # Print offerings list header
    print("\nOfferings by amount raised (high to low):")
    
    # Display each offering in order
    for i, slug in enumerate(sorted_slugs, 1):
        data = all_offerings_data[slug]
        name = data.get('name', slug)  # Use name as primary identifier, fallback to slug
        print(f"\n{i}. {name}")
        
        # Display each group of metrics
        for group_key, group_config in DISPLAY_GROUPS.items():
            # Print group title if any
            if group_config['title']:
                print(f"   {group_config['title']}")
                
            # Indent level depends on if we have a group title
            indent = "     " if group_config['title'] else "   "
            
            # Print each field in the group
            for field_info in group_config['fields']:
                # Unpack field info, handling both 3 and 4 element tuples
                if len(field_info) >= 4:
                    field_name, display_name, is_currency, is_date = field_info
                else:
                    field_name, display_name, is_currency = field_info
                    is_date = False
                
                # Skip fields that don't exist in the data
                if field_name not in data and f"{field_name}_formatted" not in data:
                    continue
                
                # Special handling for name field (already displayed as the title)
                if field_name == 'name':
                    continue
                
                # For currency fields, prefer formatted version if available
                if is_currency and f"{field_name}_formatted" in data:
                    value = data.get(f"{field_name}_formatted", '$0.00')
                    print(f"{indent}{display_name}: {value}")
                elif is_date:
                    # Format dates in a more human-readable format
                    date_value = data.get(field_name)
                    if date_value and isinstance(date_value, str) and re.match(r'\d{4}-\d{2}-\d{2}', date_value):
                        try:
                            formatted_date = datetime.strptime(date_value.split(' ')[0], '%Y-%m-%d').strftime('%B %d, %Y')
                            print(f"{indent}{display_name}: {formatted_date}")
                        except Exception:
                            print(f"{indent}{display_name}: {date_value}")
                    else:
                        print(f"{indent}{display_name}: {date_value}")
                else:
                    # For non-currency fields or if formatted not available
                    raw_value = data.get(field_name, 0)
                    if is_currency:
                        value = f"${safe_float(raw_value):,.2f}"
                    else:
                        if isinstance(raw_value, bool):
                            value = "Yes" if raw_value else "No"
                        else:
                            value = f"{safe_int(raw_value):,}"
                    print(f"{indent}{display_name}: {value}")
        
        # Add a separator between offerings
        print("-" * 50)
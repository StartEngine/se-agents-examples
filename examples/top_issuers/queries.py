"""
SQL query definitions for the top issuers example.
"""

# Define dictionary of queries for Metabase
QUERIES = {
    "top_offerings_by_amount_raised": """
        select sum(i.amount) + sum(i.investor_fee) as amount_raised, o.slug
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.status = 'APPROVED'
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        group by o.slug
        order by amount_raised DESC
        LIMIT {limit}
    """,
    
    "offering_amount_raised_last_7_days": """
        select sum(i.amount) + sum(i.investor_fee) as amount_raised
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '7 days'
    """,
    
    "offering_amount_raised_last_30_days": """
        select sum(i.amount) + sum(i.investor_fee) as amount_raised
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '30 days'
    """,
    
    "offering_number_of_investors": """
        select count(distinct(i.investor_profile_id)) as number_of_investors
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
    """,
    
    "offering_number_of_investors_last_7_days": """
        select count(distinct(i.investor_profile_id)) as number_of_investors
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '7 days'
    """,
    
    "offering_number_of_investors_last_30_days": """
        select count(distinct(i.investor_profile_id)) as number_of_investors
        from primary_facade.investment i
        join primary_facade.offering o on i.offering_id = o.id
        where o.slug = {slug}
        and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
        and i.submitted_at >= now() - interval '30 days'
    """
    # Additional queries can be added here in the future
}

# Field mapping configuration - maps query keys to field names for processing
QUERY_FIELD_MAPPING = {
    # Each query key maps to a tuple of (field name, is_currency)
    "offering_amount_raised_last_7_days": ("amount_raised_7d", True),
    "offering_amount_raised_last_30_days": ("amount_raised_30d", True),
    "offering_number_of_investors": ("investors_total", False),
    "offering_number_of_investors_last_7_days": ("investors_7d", False),
    "offering_number_of_investors_last_30_days": ("investors_30d", False),
    # Add any new queries to this mapping with proper field names
}

# Create filtered query dict for per-offering queries
def get_per_offering_queries():
    """Get queries that apply to individual offerings."""
    return {
        k: v for k, v in QUERIES.items() 
        if k != "top_offerings_by_amount_raised" and "{slug}" in v
    }
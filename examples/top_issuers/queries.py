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
    
    "offering_amount_raises": """
        with total_raise as (select sum(i.amount) + sum(i.investor_fee) as amount_raised
                     from primary_facade.investment i
                              join primary_facade.offering o on i.offering_id = o.id
                     where o.slug = {slug}
                       and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')),
             raise_past_7_days as (select sum(i.amount) + sum(i.investor_fee) as amount_raised
                                   from primary_facade.investment i
                                            join primary_facade.offering o on i.offering_id = o.id
                                   where o.slug = {slug}
                                     and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
                                     and i.submitted_at >= now() - interval '7 days'),
             raise_past_30_days as (select sum(i.amount) + sum(i.investor_fee) as amount_raised
                                    from primary_facade.investment i
                                             join primary_facade.offering o on i.offering_id = o.id
                                    where o.slug = {slug}
                                      and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
                                      and i.submitted_at >= now() - interval '30 days')
    select (select amount_raised from total_raise)        as total_raised,
           (select amount_raised from raise_past_7_days)  as raised_past_7_days,
           (select amount_raised from raise_past_30_days) as raised_past_30_days;
    """,
    
    "offering_number_of_investors": """
    with total_investors as (select count(distinct (i.investor_profile_id)) as total_count
                         from primary_facade.investment i
                                  join primary_facade.offering o on i.offering_id = o.id
                         where o.slug = {slug}
                           and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')),
         investors_past_7_days as (select count(distinct (i.investor_profile_id)) as count_7_days
                                   from primary_facade.investment i
                                            join primary_facade.offering o on i.offering_id = o.id
                                   where o.slug = {slug}
                                     and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
                                     and i.submitted_at >= now() - interval '7 days'),
         investors_past_30_days as (select count(distinct (i.investor_profile_id)) as count_30_days
                                    from primary_facade.investment i
                                             join primary_facade.offering o on i.offering_id = o.id
                                    where o.slug = {slug}
                                      and i.status in ('NOT_RECEIVED', 'RECEIVED', 'INVESTED', 'HOLD')
                                      and i.submitted_at >= now() - interval '30 days')
    select (select total_count from total_investors)          as total_investors,
           (select count_7_days from investors_past_7_days)   as investors_past_7_days,
           (select count_30_days from investors_past_30_days) as investors_past_30_days;
    """
    # Additional queries can be added here in the future
}

# Field mapping configuration for the combined queries
QUERY_FIELD_MAPPING = {
    # Each query key maps to a dictionary with column-to-field mappings and whether they're currency values
    "offering_amount_raises": {
        "total_raised": {"field_name": "amount_raised", "is_currency": True},
        "raised_past_7_days": {"field_name": "amount_raised_7d", "is_currency": True},
        "raised_past_30_days": {"field_name": "amount_raised_30d", "is_currency": True}
    },
    "offering_number_of_investors": {
        "total_investors": {"field_name": "investors_total", "is_currency": False},
        "investors_past_7_days": {"field_name": "investors_7d", "is_currency": False},
        "investors_past_30_days": {"field_name": "investors_30d", "is_currency": False}
    }
}

# Create filtered query dict for per-offering queries
def get_per_offering_queries():
    """Get queries that apply to individual offerings."""
    return {
        k: v for k, v in QUERIES.items() 
        if k != "top_offerings_by_amount_raised" and "{slug}" in v
    }
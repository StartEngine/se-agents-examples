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
    "offering_data_points": """
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
                                  and i.submitted_at >= now() - interval '30 days'),
         total_investors as (select count(distinct (i.investor_profile_id)) as total_count
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
                                      and i.submitted_at >= now() - interval '30 days'),
         total_followers as (select count(ifo.id) as total_count
                             from primary_facade.investor_followed_offering ifo
                                      join primary_facade.offering o on ifo.offering_id = o.id
                             where o.slug = {slug}),
         followers_past_7_days as (select count(ifo.id) as count_7_days
                                   from primary_facade.investor_followed_offering ifo
                                            join primary_facade.offering o on ifo.offering_id = o.id
                                   where o.slug = {slug}
                                     and ifo.follow_date >= now() - interval '7 days'),
         followers_past_30_days as (select count(ifo.id) as count_30_days
                                    from primary_facade.investor_followed_offering ifo
                                             join primary_facade.offering o on ifo.offering_id = o.id
                                    where o.slug = {slug}
                                      and ifo.follow_date >= now() - interval '30 days'),
         updates_past_7_days as (select count(ouq.id) as count_7_days
                                 from primary_facade.offering_update_queue ouq
                                          join primary_facade.offering o on ouq.offering_id = o.id
                                 where o.slug = {slug}
                                   and ouq.status = 'DONE'
                                   and ouq.deployed_at >= now() - interval '7 days'),
         updates_past_30_days as (select count(ouq.id) as count_30_days
                                  from primary_facade.offering_update_queue ouq
                                           join primary_facade.offering o on ouq.offering_id = o.id
                                  where o.slug = {slug}
                                    and ouq.status = 'DONE'
                                    and ouq.deployed_at >= now() - interval '30 days')
    select (select amount_raised from total_raise)            as total_raised,
           (select amount_raised from raise_past_7_days)      as raised_past_7_days,
           (select amount_raised from raise_past_30_days)     as raised_past_30_days,
           (select total_count from total_investors)          as total_investors,
           (select count_7_days from investors_past_7_days)   as investors_past_7_days,
           (select count_30_days from investors_past_30_days) as investors_past_30_days,
           (select total_count from total_followers)          as total_followers,
           (select count_7_days from followers_past_7_days)   as followers_past_7_days,
           (select count_30_days from followers_past_30_days) as followers_past_30_days,
           (select count_7_days from updates_past_7_days)     as updates_past_7_days,
           (select count_30_days from updates_past_30_days)   as updates_past_30_days;
    """
    # Additional queries can be added here in the future
}

# Field mapping configuration for the combined queries
QUERY_FIELD_MAPPING = {
    # Map the combined query - offering_data_points contains all metrics
    "offering_data_points": {
        "total_raised": {"field_name": "amount_raised", "is_currency": True},
        "raised_past_7_days": {"field_name": "amount_raised_7d", "is_currency": True},
        "raised_past_30_days": {"field_name": "amount_raised_30d", "is_currency": True},
        "total_investors": {"field_name": "investors_total", "is_currency": False},
        "investors_past_7_days": {"field_name": "investors_7d", "is_currency": False},
        "investors_past_30_days": {"field_name": "investors_30d", "is_currency": False},
        "total_followers": {"field_name": "followers_total", "is_currency": False},
        "followers_past_7_days": {"field_name": "followers_7d", "is_currency": False},
        "followers_past_30_days": {"field_name": "followers_30d", "is_currency": False},
        "updates_past_7_days": {"field_name": "updates_7d", "is_currency": False},
        "updates_past_30_days": {"field_name": "updates_30d", "is_currency": False}
    }
}

# Create filtered query dict for per-offering queries
def get_per_offering_queries():
    """Get queries that apply to individual offerings."""
    return {
        k: v for k, v in QUERIES.items() 
        if k != "top_offerings_by_amount_raised" and "{slug}" in v
    }
"""Selectors for JIRA UI elements.

This module provides selector dictionaries for various parts of the JIRA UI,
allowing the agent to locate and interact with UI elements consistently.
"""

# Default selectors for common elements in JIRA UI
DEFAULT_SELECTORS = {
    "login_page": {
        "username_field": "input[name='username'], input[id='username'], input[name='email'], input[type='email']",
        "password_field": "input[name='password'], input[id='password'], input[type='password']",
        "login_button": "button[id='login-submit'], button[type='submit'], button:contains('Log in')",
        "sso_options": {
            "google": [
                "button:contains('Continue with Google')",
                "button:contains('Sign in with Google')",
                "a:contains('Google')",
                "button:contains('Google')",
                "button[data-provider='google']",
                "div:contains('Google') button",
                "a[data-provider='google']",
                "a.google",
                "a[href*='google']",
                ".google-button",
                "[id*='google']",
                "[class*='google']",
                "button[data-testid*='google']",
                "img[alt*='Google']",
                "img[src*='google']",
                "*[aria-label*='Google']"
            ],
            "microsoft": [
                "button:contains('Continue with Microsoft')",
                "button:contains('Sign in with Microsoft')",
                "a:contains('Microsoft')",
                "button:contains('Microsoft')"
            ],
            "okta": [
                "button:contains('Continue with Okta')",
                "button:contains('Sign in with Okta')",
                "a:contains('Okta')"
            ],
            "generic_sso": [
                "button:contains('Log in with SSO')",
                "a:contains('Single Sign-on')",
                "button:contains('SSO')"
            ]
        }
    },
    "ticket_page": {
        "summary": "[data-test-id='issue.views.issue-base.foundation.summary.heading']",
        "description": "[data-test-id='issue.views.field.rich-text.description']",
        "status": "[data-test-id='issue.views.issue-base.foundation.status.status-field-wrapper']",
        "assignee": "[data-test-id='issue.views.field.user.assignee']",
        "priority": "[data-test-id='issue.views.field.select.priority']",
        "type": "[data-test-id='issue.views.issue-base.foundation.issue-type.issue-type-field-wrapper']",
        "reporter": "[data-test-id='issue.views.field.user.reporter']",
        "created": "[data-test-id='issue.views.field.date.created']",
        "updated": "[data-test-id='issue.views.field.date.updated']",
        "comments": "[data-test-id='issue.views.comments.comment-container']",
        "labels": "[data-test-id='issue.views.field.labels']",
        "components": "[data-test-id='issue.views.field.select.components']",
        "fix_versions": "[data-test-id='issue.views.field.select.fixversions']",
        "add_comment": {
            "button": "[data-testid='comment-button'], button:contains('Comment')",
            "field": "[data-testid='comment-field'], div[role='textbox']",
            "submit": "button[type='submit'], button:contains('Save')"
        },
        "status_transition": {
            "dropdown": "[data-testid='status-dropdown'], button:contains('In Progress')",
            "options": {
                "in_progress": "button:contains('In Progress')",
                "done": "button:contains('Done')",
                "to_do": "button:contains('To Do')"
            }
        }
    }
}

# Common field selectors for extracting ticket data
FIELD_SELECTORS = DEFAULT_SELECTORS["ticket_page"]

# Authentication providers and their selectors
SSO_SELECTORS = DEFAULT_SELECTORS["login_page"]["sso_options"] 
"""
Example demonstrating how to use the browser automation framework to interact with JIRA tickets.

This example shows how to:
1. Initialize a local browser instance using the LocalPlaywrightBrowser
2. Navigate to a JIRA ticket
3. Log in (if necessary)
4. Extract the ticket summary, description, and other fields
5. Debug selector issues with element info
"""

import os
import json
from app.browser_agent.local_playwright import LocalPlaywrightBrowser
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)


def read_jira_ticket(ticket_id, jira_url=None, use_sso=True, prefer_google=True, extract_fields=None):
    """
    Opens a JIRA ticket and extracts its information.

    Args:
        ticket_id (str): The JIRA ticket ID (e.g., "PROJ-123")
        jira_url (str, optional): The JIRA instance URL. Defaults to environment variable.
        use_sso (bool): Whether to try SSO login flow (default: True)
        prefer_google (bool): Whether to prefer Google SSO if available (default: True)
        extract_fields (list, optional): List of additional fields to extract (e.g., ["status", "assignee"])

    Returns:
        dict: Ticket information including summary, description, and other fields
    """
    # Default fields to extract if not specified
    if extract_fields is None:
        extract_fields = ["status", "assignee", "priority", "type"]

    # Get JIRA URL from environment variable if not provided
    jira_url = jira_url or os.getenv("JIRA_URL", "https://mydomain.atlassian.net")

    # Credentials from environment variables
    username = os.getenv("JIRA_USERNAME")
    password = os.getenv("JIRA_PASSWORD")

    print(f"Opening JIRA ticket {ticket_id}...")

    # Create a browser instance (set headless=False to see the browser)
    with LocalPlaywrightBrowser(headless=False) as browser:
        # Navigate to the JIRA ticket
        ticket_url = f"{jira_url}/browse/{ticket_id}"
        browser.goto(ticket_url)

        # Wait for the page to load
        browser.wait(3000)  # 3 seconds

        # Check if login is required
        if _is_login_page(browser):
            if not username or not password:
                print("Login required but no credentials provided in environment variables.")
                return {"error": "Login required but no credentials provided"}

            print("Login required. Attempting to log in...")
            _login(browser, username, password, use_sso=use_sso, prefer_google=prefer_google)

            # Wait for redirect after login
            browser.wait(5000)

            # Navigate to ticket again if needed
            current_url = browser.get_current_url()
            if ticket_id not in current_url:
                browser.goto(ticket_url)
                browser.wait(3000)

        # Initialize ticket information
        ticket_info = {
            "id": ticket_id,
            "url": browser.get_current_url(),
        }

        # Extract ticket fields
        _extract_ticket_fields(browser, ticket_info, extract_fields)

        return ticket_info


def _is_login_page(browser):
    """Check if we're on a login page."""
    login_selectors = [
        "input[name='username']",
        "input[id='login-submit']",
        "input[name='password']",
        "button:contains('Continue with Google')",
        "button:contains('Log in with SSO')",
        "a:contains('Single Sign-on')"
    ]

    for selector in login_selectors:
        # Use get_element_info for better detection
        element_info = browser.get_element_info(selector)
        if element_info:
            print(f"Login element detected: {element_info['tag']}")
            return True

        # Fallback to wait_for_selector for complex selectors
        if browser.wait_for_selector(selector, timeout=1000):
            return True

    return False


def _extract_ticket_fields(browser, ticket_info, extract_fields):
    """Extract all requested fields from the JIRA ticket.

    Args:
        browser: Browser instance
        ticket_info: Dictionary to update with extracted data
        extract_fields: List of fields to extract
    """
    # Standard fields with their selectors
    field_selectors = {
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
        "fix_versions": "[data-test-id='issue.views.field.select.fixversions']"
    }

    # Always extract summary and description
    fields_to_extract = ["summary", "description"] + extract_fields

    # Remove duplicates
    fields_to_extract = list(dict.fromkeys(fields_to_extract))

    for field in fields_to_extract:
        if field in field_selectors:
            selector = field_selectors[field]
            try:
                # First check if the element exists and is visible
                element_info = browser.get_element_info(selector)

                if element_info and element_info.get('isVisible', False):
                    text = browser.extract_text(selector)
                    ticket_info[field] = text
                    print(f"Extracted {field}: {text[:50]}..." if len(text) > 50 else f"Extracted {field}: {text}")
                else:
                    # Log debug info
                    if element_info:
                        print(f"{field} element found but not visible: {element_info}")
                    else:
                        print(f"{field} element not found")

                    # Try alternative selectors
                    alt_selector = f"[data-testid*='{field}'], [id*='{field}'], [class*='{field}']"
                    if browser.wait_for_selector(alt_selector, timeout=1000):
                        text = browser.extract_text(alt_selector)
                        ticket_info[field] = text
                        print(f"Extracted {field} (alt): {text[:50]}..." if len(
                            text) > 50 else f"Extracted {field} (alt): {text}")
                    else:
                        ticket_info[field] = "Not found"
            except Exception as e:
                print(f"Error extracting {field}: {e}")
                ticket_info[field] = "Error extracting"

    # Extract comments as a list if present
    if "comments" in fields_to_extract:
        try:
            comments_selector = field_selectors["comments"]
            if browser.wait_for_selector(comments_selector, timeout=1000):
                # Get all comment elements
                comment_elements = browser._page.query_selector_all(comments_selector)
                comments = []
                for i, element in enumerate(comment_elements, 1):
                    comment_text = element.text_content()
                    if comment_text:
                        comments.append({
                            "number": i,
                            "text": comment_text.strip()
                        })
                ticket_info["comments"] = comments
                print(f"Extracted {len(comments)} comments")
            else:
                ticket_info["comments"] = []
        except Exception as e:
            print(f"Error extracting comments: {e}")
            ticket_info["comments"] = []

    # As a fallback, get the entire HTML if extraction fails
    if "summary" not in ticket_info or ticket_info["summary"] == "Not found":
        try:
            # Save HTML for debugging
            ticket_info["_html"] = browser.get_page_html()
            print("Saved page HTML as fallback")
        except Exception as e:
            print(f"Error getting page HTML: {e}")


def _login(browser, username, password, use_sso=True, prefer_google=True):
    """Handle JIRA login with support for SSO.

    Args:
        browser: Browser instance
        username: JIRA username/email
        password: JIRA password/API token
        use_sso: Whether to attempt SSO login (default: True)
        prefer_google: Whether to prefer Google SSO if available (default: True)
    """
    try:
        # First check for SSO options if requested
        if use_sso:
            # Prioritize Google SSO if preferred
            if prefer_google:
                google_sso_selectors = [
                    "button:contains('Continue with Google')",
                    "button:contains('Sign in with Google')",
                    "a:contains('Google')",
                    "button:contains('Google')",
                    "button[data-provider='google']",
                    "div:contains('Google') button"
                ]

                for selector in google_sso_selectors:
                    # Better element detection
                    element_info = browser.get_element_info(selector)
                    if element_info:
                        print(f"Found Google SSO option: {element_info['tag']} (visible: {element_info['isVisible']})")
                        if element_info['isVisible']:
                            browser.click_selector(selector)
                            browser.wait(5000)  # Wait for redirect

                            # Handle Google SSO provider page
                            return _handle_google_sso(browser, username, password)

                    # Fallback
                    if browser.wait_for_selector(selector, timeout=1000):
                        print(f"Found Google SSO option: {selector}")
                        browser.click_selector(selector)
                        browser.wait(5000)  # Wait for redirect

                        # Handle Google SSO provider page
                        return _handle_google_sso(browser, username, password)

            # If Google not found or not preferred, try other SSO options
            sso_selectors = [
                "button:contains('Log in with SSO')",
                "a:contains('Single Sign-on')",
                "button:contains('SSO')",
                "button:contains('Continue with Microsoft')",
                "button:contains('Continue with Okta')"
            ]

            for selector in sso_selectors:
                if browser.wait_for_selector(selector, timeout=1000):
                    print(f"Found SSO option: {selector}")
                    browser.click_selector(selector)
                    browser.wait(5000)  # Wait for redirect

                    # Handle SSO provider page
                    return _handle_sso_provider(browser, username, password)

        # Regular username/password flow if no SSO or SSO not requested
        # Enter username
        username_selector = "input[name='username'], input[id='username'], input[name='email']"
        if browser.wait_for_selector(username_selector, timeout=3000):
            browser.click_selector(username_selector)
            browser.type(username)

            # Look for Continue or Submit button
            continue_selector = "button[id='login-submit'], button[type='submit'], button:contains('Continue')"
            if browser.wait_for_selector(continue_selector, timeout=2000):
                browser.click_selector(continue_selector)
                browser.wait(3000)

        # Enter password (might be on a second screen after username)
        password_selector = "input[name='password'], input[id='password']"
        if browser.wait_for_selector(password_selector, timeout=3000):
            browser.click_selector(password_selector)
            browser.type(password)

            # Click login button
            login_selector = "button[id='login-submit'], button[type='submit'], button:contains('Log in')"
            if browser.wait_for_selector(login_selector, timeout=2000):
                browser.click_selector(login_selector)
                browser.wait(5000)  # Wait longer for login to complete

        return True
    except Exception as e:
        print(f"Login error: {e}")
        return False


def _handle_sso_provider(browser, username, password):
    """Handle SSO provider authentication flow.

    This function attempts to detect and handle various SSO providers like
    Google, Microsoft, Okta, etc.
    """
    # Wait for SSO page to load
    browser.wait(3000)

    # Get current URL to determine provider
    current_url = browser.get_current_url()
    print(f"SSO redirect URL: {current_url}")

    # Google SSO
    if "google" in current_url.lower():
        return _handle_google_sso(browser, username, password)
    # Microsoft/Azure SSO
    elif any(provider in current_url.lower() for provider in ["microsoft", "azure", "live"]):
        return _handle_microsoft_sso(browser, username, password)
    # Okta SSO
    elif "okta" in current_url.lower():
        return _handle_okta_sso(browser, username, password)
    # Generic SSO as fallback
    else:
        return _handle_generic_sso(browser, username, password)


def _handle_google_sso(browser, username, password):
    """Handle Google SSO login flow."""
    try:
        # Enter email
        email_selector = "input[type='email']"
        if browser.wait_for_selector(email_selector, timeout=5000):
            # Check element state
            element_info = browser.get_element_info(email_selector)
            if element_info:
                print(f"Found email input: {element_info.get('attributes', {})}")

            browser.click_selector(email_selector)
            browser.type(username)

            # Click next
            next_selector = "button:contains('Next'), button[id='identifierNext']"
            if browser.wait_for_selector(next_selector, timeout=2000):
                browser.click_selector(next_selector)
                browser.wait(3000)

        # Enter password
        password_selector = "input[type='password']"
        if browser.wait_for_selector(password_selector, timeout=5000):
            browser.click_selector(password_selector)
            browser.type(password)

            # Click next/sign in
            signin_selector = "button:contains('Next'), button[id='passwordNext']"
            if browser.wait_for_selector(signin_selector, timeout=2000):
                browser.click_selector(signin_selector)
                browser.wait(5000)

        return True
    except Exception as e:
        print(f"Google SSO error: {e}")
        return False


def _handle_microsoft_sso(browser, username, password):
    """Handle Microsoft/Azure SSO login flow."""
    try:
        # Enter email
        email_selector = "input[type='email'], input[name='loginfmt']"
        if browser.wait_for_selector(email_selector, timeout=5000):
            element_info = browser.get_element_info(email_selector)
            if element_info:
                print(f"Found Microsoft email input: {element_info.get('attributes', {})}")

            browser.click_selector(email_selector)
            browser.type(username)

            # Click next
            next_selector = "input[type='submit'], button:contains('Next')"
            if browser.wait_for_selector(next_selector, timeout=2000):
                browser.click_selector(next_selector)
                browser.wait(3000)

        # Enter password
        password_selector = "input[type='password'], input[name='passwd']"
        if browser.wait_for_selector(password_selector, timeout=5000):
            browser.click_selector(password_selector)
            browser.type(password)

            # Click sign in
            signin_selector = "input[type='submit'], button:contains('Sign in')"
            if browser.wait_for_selector(signin_selector, timeout=2000):
                browser.click_selector(signin_selector)
                browser.wait(3000)

            # Handle "Stay signed in?" if it appears
            stay_selector = "input[type='submit'][value='Yes'], button:contains('Yes')"
            if browser.wait_for_selector(stay_selector, timeout=3000):
                browser.click_selector(stay_selector)
                browser.wait(3000)

        return True
    except Exception as e:
        print(f"Microsoft SSO error: {e}")
        return False


def _handle_okta_sso(browser, username, password):
    """Handle Okta SSO login flow."""
    try:
        # Enter username/email
        username_selector = "input[name='username'], input[id='okta-signin-username']"
        if browser.wait_for_selector(username_selector, timeout=5000):
            element_info = browser.get_element_info(username_selector)
            if element_info:
                print(f"Found Okta username input: {element_info.get('attributes', {})}")

            browser.click_selector(username_selector)
            browser.type(username)

        # Enter password
        password_selector = "input[name='password'], input[id='okta-signin-password']"
        if browser.wait_for_selector(password_selector, timeout=3000):
            browser.click_selector(password_selector)
            browser.type(password)

        # Click sign in
        submit_selector = "input[type='submit'], button[type='submit'], button:contains('Sign in')"
        if browser.wait_for_selector(submit_selector, timeout=2000):
            browser.click_selector(submit_selector)
            browser.wait(5000)

        # Handle MFA if present (this is very org-specific)
        # This is a simplified example - real MFA handling would need to be customized
        push_selector = "button:contains('Send Push'), a:contains('Send Push')"
        if browser.wait_for_selector(push_selector, timeout=3000):
            browser.click_selector(push_selector)
            print("MFA push notification sent - please approve on your device")
            browser.wait(20000)  # Wait longer for MFA approval

        return True
    except Exception as e:
        print(f"Okta SSO error: {e}")
        return False


def _handle_generic_sso(browser, username, password):
    """Handle a generic SSO login flow for unknown providers."""
    try:
        # Look for common username/email fields
        username_selectors = [
            "input[type='email']",
            "input[name='username']",
            "input[id='username']",
            "input[name='email']"
        ]

        for selector in username_selectors:
            element_info = browser.get_element_info(selector)
            if element_info and element_info.get('isVisible', False):
                print(
                    f"Found username input: {element_info['tag']} with attributes: {element_info.get('attributes', {})}")
                browser.click_selector(selector)
                browser.type(username)
                browser.wait(1000)

                # Look for a next/continue button
                next_selectors = [
                    "button:contains('Next')",
                    "button:contains('Continue')",
                    "input[type='submit']",
                    "button[type='submit']"
                ]

                for next_selector in next_selectors:
                    if browser.wait_for_selector(next_selector, timeout=1000):
                        browser.click_selector(next_selector)
                        browser.wait(3000)
                        break
                break
            elif browser.wait_for_selector(selector, timeout=1000):
                browser.click_selector(selector)
                browser.type(username)
                browser.wait(1000)

                # Look for a next/continue button
                for next_selector in ["button:contains('Next')", "button:contains('Continue')", "input[type='submit']"]:
                    if browser.wait_for_selector(next_selector, timeout=1000):
                        browser.click_selector(next_selector)
                        browser.wait(3000)
                        break
                break

        # Look for common password fields
        password_selectors = [
            "input[type='password']",
            "input[name='password']",
            "input[id='password']"
        ]

        for selector in password_selectors:
            element_info = browser.get_element_info(selector)
            if element_info and element_info.get('isVisible', False):
                browser.click_selector(selector)
                browser.type(password)
                browser.wait(1000)

                # Look for a login/submit button
                submit_selectors = [
                    "button:contains('Sign in')",
                    "button:contains('Log in')",
                    "input[type='submit']",
                    "button[type='submit']"
                ]

                for submit_selector in submit_selectors:
                    if browser.wait_for_selector(submit_selector, timeout=1000):
                        browser.click_selector(submit_selector)
                        browser.wait(5000)
                        break
                break
            elif browser.wait_for_selector(selector, timeout=3000):
                browser.click_selector(selector)
                browser.type(password)
                browser.wait(1000)

                # Look for a login/submit button
                for submit_selector in ["button:contains('Sign in')", "button:contains('Log in')",
                                        "input[type='submit']"]:
                    if browser.wait_for_selector(submit_selector, timeout=1000):
                        browser.click_selector(submit_selector)
                        browser.wait(5000)
                        break
                break

        return True
    except Exception as e:
        print(f"Generic SSO error: {e}")
        return False


def save_ticket_data(ticket_info, output_dir=None):
    """Save ticket data to a JSON file.

    Args:
        ticket_info: Dictionary of ticket data
        output_dir: Directory to save file (defaults to ./ticket_data)

    Returns:
        Path to saved file
    """
    if output_dir is None:
        output_dir = os.path.join(os.getcwd(), "ticket_data")

    # Create directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Filename from ticket ID
    filename = f"{ticket_info['id'].replace('-', '_').lower()}.json"
    filepath = os.path.join(output_dir, filename)

    # Save data
    with open(filepath, 'w') as f:
        json.dump(ticket_info, f, indent=2)

    print(f"Ticket data saved to: {filepath}")
    return filepath


if __name__ == "__main__":
    # Example usage
    ticket_id = input("Enter JIRA ticket ID (e.g., PROJ-123): ")

    # Additional fields to extract
    fields = input("Enter comma-separated list of additional fields to extract (leave blank for defaults): ")
    if fields.strip():
        extract_fields = [f.strip() for f in fields.split(",")]
    else:
        extract_fields = None

    # Automatically use Google SSO by default
    ticket_info = read_jira_ticket(ticket_id, use_sso=True, prefer_google=True, extract_fields=extract_fields)

    # Save to file option
    save_option = input("Save ticket data to file? (y/n): ").lower()
    if save_option == 'y':
        save_path = save_ticket_data(ticket_info)

    print("\nTicket Information:")
    for key, value in ticket_info.items():
        # Skip HTML content in the output
        if key == "_html":
            print(f"  {key}: [HTML content saved]")
        # Format comments
        elif key == "comments" and isinstance(value, list):
            print(f"  {key}: {len(value)} comments")
            if value and len(value) > 0:
                print(f"    First comment: {value[0]['text'][:100]}..." if len(
                    value[0]['text']) > 100 else f"    First comment: {value[0]['text']}")
        # Format long strings
        elif isinstance(value, str) and len(value) > 150:
            print(f"  {key}: {value[:150]}...")
        else:
            print(f"  {key}: {value}")

    print("\nNote: This example demonstrates JIRA ticket retrieval.")
    print("To use with your JIRA instance, set the following environment variables:")
    print("  - JIRA_URL: Your JIRA instance URL (e.g., https://your-company.atlassian.net)")
    print("  - JIRA_USERNAME: Your JIRA username/email")
    print("  - JIRA_PASSWORD: Your JIRA password or API token")

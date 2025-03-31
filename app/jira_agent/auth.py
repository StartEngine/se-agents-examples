"""Authentication utilities for JIRA.

This module provides functions for authenticating with JIRA using various methods:
- Username/password
- SSO providers (Google, Microsoft, Okta, etc.)
- API tokens
"""

import logging
from typing import Optional, Tuple
from app.browser_agent.browser import Browser
from app.jira_agent.selectors import DEFAULT_SELECTORS, SSO_SELECTORS

logger = logging.getLogger(__name__)


def is_login_page(browser: Browser) -> bool:
    """Check if we're on a login page.
    
    Args:
        browser: Browser instance
        
    Returns:
        True if this appears to be a login page
    """
    login_selectors = [
        DEFAULT_SELECTORS["login_page"]["username_field"],
        DEFAULT_SELECTORS["login_page"]["password_field"],
        DEFAULT_SELECTORS["login_page"]["login_button"]
    ]
    
    # Add SSO selectors
    for provider_selectors in SSO_SELECTORS.values():
        login_selectors.extend(provider_selectors)
    
    for selector in login_selectors:
        # Use get_element_info for better detection
        element_info = browser.get_element_info(selector)
        if element_info:
            logger.info(f"Login element detected: {element_info['tag']}")
            return True
            
        # Fallback to wait_for_selector for complex selectors
        if browser.wait_for_selector(selector, timeout=1000):
            return True
            
    return False


def login(browser: Browser, username: str, password: str, use_sso: bool = True, 
          prefer_google: bool = True) -> bool:
    """Handle JIRA login with support for SSO.
    
    Args:
        browser: Browser instance
        username: JIRA username/email
        password: JIRA password/API token
        use_sso: Whether to attempt SSO login (default: True)
        prefer_google: Whether to prefer Google SSO if available (default: True)
        
    Returns:
        True if login appears successful
    """
    try:
        # First check for SSO options if requested
        if use_sso:
            # Prioritize Google SSO if preferred
            if prefer_google:
                return _try_sso_provider(browser, username, password, provider="google")
            
            # Otherwise try each SSO option in order
            for provider in ["generic_sso", "google", "microsoft", "okta"]:
                if _try_sso_provider(browser, username, password, provider):
                    return True
        
        # Regular username/password flow if no SSO or SSO not requested
        return _standard_login(browser, username, password)
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False


def _try_sso_provider(browser: Browser, username: str, password: str, provider: str) -> bool:
    """Try to log in using a specific SSO provider.
    
    Args:
        browser: Browser instance
        username: SSO username/email
        password: SSO password
        provider: Provider name ("google", "microsoft", "okta", or "generic_sso")
        
    Returns:
        True if login appears successful
    """
    if provider not in SSO_SELECTORS:
        logger.warning(f"Unknown SSO provider: {provider}")
        return False
        
    # Get selectors for the provider
    provider_selectors = SSO_SELECTORS[provider]
    
    # Look for any SSO buttons for this provider
    for selector in provider_selectors:
        # Check if element exists and is visible
        element_info = browser.get_element_info(selector)
        if element_info and element_info.get('isVisible', False):
            logger.info(f"Found {provider} SSO option: {element_info['tag']} (visible: {element_info['isVisible']})")
            browser.click_selector(selector)
            browser.wait(5000)  # Wait for redirect
            
            # Handle provider-specific login
            return _handle_sso_flow(browser, username, password, provider)
        
        # Fallback to simple selector check
        if browser.wait_for_selector(selector, timeout=1000):
            logger.info(f"Found {provider} SSO option: {selector}")
            browser.click_selector(selector)
            browser.wait(5000)  # Wait for redirect
            
            # Handle provider-specific login
            return _handle_sso_flow(browser, username, password, provider)
    
    return False


def _handle_sso_flow(browser: Browser, username: str, password: str, provider: str) -> bool:
    """Handle SSO provider authentication flow.
    
    Args:
        browser: Browser instance
        username: SSO username/email
        password: SSO password
        provider: Provider name ("google", "microsoft", "okta", or "generic_sso")
        
    Returns:
        True if login appears successful
    """
    # Wait for SSO page to load
    browser.wait(3000)
    
    # Get current URL to determine provider if not explicitly specified
    if provider == "generic_sso":
        current_url = browser.get_current_url()
        logger.info(f"SSO redirect URL: {current_url}")
        
        # Detect provider from URL
        if "google" in current_url.lower():
            provider = "google"
        elif any(p in current_url.lower() for p in ["microsoft", "azure", "live"]):
            provider = "microsoft"
        elif "okta" in current_url.lower():
            provider = "okta"
    
    # Handle different providers
    if provider == "google":
        return _handle_google_sso(browser, username, password)
    elif provider == "microsoft":
        return _handle_microsoft_sso(browser, username, password)
    elif provider == "okta":
        return _handle_okta_sso(browser, username, password)
    else:
        return _handle_generic_sso(browser, username, password)


def _standard_login(browser: Browser, username: str, password: str) -> bool:
    """Handle standard username/password login flow.
    
    Args:
        browser: Browser instance
        username: JIRA username
        password: JIRA password
        
    Returns:
        True if login appears successful
    """
    # Enter username
    username_selector = DEFAULT_SELECTORS["login_page"]["username_field"]
    if browser.wait_for_selector(username_selector, timeout=3000):
        browser.click_selector(username_selector)
        browser.type(username)
        
        # Look for Continue or Submit button
        continue_selector = "button[id='login-submit'], button[type='submit'], button:contains('Continue')"
        if browser.wait_for_selector(continue_selector, timeout=2000):
            browser.click_selector(continue_selector)
            browser.wait(3000)
    
    # Enter password (might be on a second screen after username)
    password_selector = DEFAULT_SELECTORS["login_page"]["password_field"]
    if browser.wait_for_selector(password_selector, timeout=3000):
        browser.click_selector(password_selector)
        browser.type(password)
        
        # Click login button
        login_selector = DEFAULT_SELECTORS["login_page"]["login_button"]
        if browser.wait_for_selector(login_selector, timeout=2000):
            browser.click_selector(login_selector)
            browser.wait(5000)  # Wait longer for login to complete
    
    return True


def _handle_google_sso(browser: Browser, username: str, password: str) -> bool:
    """Handle Google SSO login flow.
    
    Args:
        browser: Browser instance
        username: Google email
        password: Google password
        
    Returns:
        True if login appears successful
    """
    try:
        # Enter email
        email_selector = "input[type='email']"
        if browser.wait_for_selector(email_selector, timeout=5000):
            # Check element state
            element_info = browser.get_element_info(email_selector)
            if element_info:
                logger.info(f"Found email input: {element_info.get('attributes', {})}")
            
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
        logger.error(f"Google SSO error: {e}")
        return False


def _handle_microsoft_sso(browser: Browser, username: str, password: str) -> bool:
    """Handle Microsoft/Azure SSO login flow.
    
    Args:
        browser: Browser instance
        username: Microsoft email
        password: Microsoft password
        
    Returns:
        True if login appears successful
    """
    try:
        # Enter email
        email_selector = "input[type='email'], input[name='loginfmt']"
        if browser.wait_for_selector(email_selector, timeout=5000):
            element_info = browser.get_element_info(email_selector)
            if element_info:
                logger.info(f"Found Microsoft email input: {element_info.get('attributes', {})}")
                
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
        logger.error(f"Microsoft SSO error: {e}")
        return False


def _handle_okta_sso(browser: Browser, username: str, password: str) -> bool:
    """Handle Okta SSO login flow.
    
    Args:
        browser: Browser instance
        username: Okta username/email
        password: Okta password
        
    Returns:
        True if login appears successful
    """
    try:
        # Enter username/email
        username_selector = "input[name='username'], input[id='okta-signin-username']"
        if browser.wait_for_selector(username_selector, timeout=5000):
            element_info = browser.get_element_info(username_selector)
            if element_info:
                logger.info(f"Found Okta username input: {element_info.get('attributes', {})}")
                
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
            logger.info("MFA push notification sent - please approve on your device")
            browser.wait(20000)  # Wait longer for MFA approval
            
        return True
    except Exception as e:
        logger.error(f"Okta SSO error: {e}")
        return False


def _handle_generic_sso(browser: Browser, username: str, password: str) -> bool:
    """Handle a generic SSO login flow for unknown providers.
    
    Args:
        browser: Browser instance
        username: SSO username/email
        password: SSO password
        
    Returns:
        True if login appears successful
    """
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
                logger.info(f"Found username input: {element_info['tag']} with attributes: {element_info.get('attributes', {})}")
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
                for submit_selector in ["button:contains('Sign in')", "button:contains('Log in')", "input[type='submit']"]:
                    if browser.wait_for_selector(submit_selector, timeout=1000):
                        browser.click_selector(submit_selector)
                        browser.wait(5000)
                        break
                break
                
        return True
    except Exception as e:
        logger.error(f"Generic SSO error: {e}")
        return False 
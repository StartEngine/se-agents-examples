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
    try:
        # First wait to ensure page is fully loaded
        browser.wait(2000)
        
        login_selectors = [
            DEFAULT_SELECTORS["login_page"]["username_field"],
            DEFAULT_SELECTORS["login_page"]["password_field"],
            DEFAULT_SELECTORS["login_page"]["login_button"]
        ]
        
        # Add SSO selectors
        for provider_selectors in SSO_SELECTORS.values():
            login_selectors.extend(provider_selectors)
        
        for selector in login_selectors:
            try:
                # Use get_element_info for better detection
                element_info = browser.get_element_info(selector)
                if element_info:
                    logger.info(f"Login element detected: {element_info['tag']}")
                    return True
            except Exception as e:
                logger.debug(f"Error checking selector {selector}: {e}")
                continue
                
            # Fallback to wait_for_selector for complex selectors
            try:
                if browser.wait_for_selector(selector, timeout=1000):
                    return True
            except Exception as e:
                logger.debug(f"Error waiting for selector {selector}: {e}")
                continue
                
        return False
    except Exception as e:
        logger.warning(f"Error checking if on login page: {e}")
        # If we can't determine, assume we're not on a login page
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
            logger.info("Attempting SSO login")
            
            # First check what SSO options are available
            available_sso = []
            
            # Check for Google
            google_present = browser.execute_script("""
                const googleTexts = ['google', 'continue with google', 'sign in with google'];
                const elements = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
                
                for (const el of elements) {
                    const text = el.innerText ? el.innerText.toLowerCase() : '';
                    if (googleTexts.some(gt => text.includes(gt))) {
                        return true;
                    }
                    
                    // Check for Google images
                    const images = el.querySelectorAll('img');
                    for (const img of images) {
                        if ((img.alt && img.alt.toLowerCase().includes('google')) ||
                            (img.src && img.src.toLowerCase().includes('google'))) {
                            return true;
                        }
                    }
                }
                return false;
            """)
            
            # Check for Microsoft
            microsoft_present = browser.execute_script("""
                const microsoftTexts = ['microsoft', 'continue with microsoft', 'sign in with microsoft', 'azure', 'office 365'];
                const elements = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
                
                for (const el of elements) {
                    const text = el.innerText ? el.innerText.toLowerCase() : '';
                    if (microsoftTexts.some(mt => text.includes(mt))) {
                        return true;
                    }
                    
                    // Check for Microsoft images
                    const images = el.querySelectorAll('img');
                    for (const img of images) {
                        if ((img.alt && img.alt.toLowerCase().includes('microsoft')) ||
                            (img.src && img.src.toLowerCase().includes('microsoft'))) {
                            return true;
                        }
                    }
                }
                return false;
            """)
            
            if google_present:
                available_sso.append("google")
                logger.info("Google SSO option detected")
            
            if microsoft_present:
                available_sso.append("microsoft")
                logger.info("Microsoft SSO option detected")
            
            # Prioritize Google SSO if preferred and available
            if prefer_google and "google" in available_sso:
                logger.info("Attempting Google SSO login (preferred)")
                if _try_sso_provider(browser, username, password, provider="google", avoid_providers=["microsoft"]):
                    logger.info("Google SSO login successful")
                    
                    # Wait to make sure we're fully logged in
                    browser.wait(10000)
                    
                    # Check if we're still on a login page
                    if not is_login_page(browser):
                        return True
            
            # Otherwise try each SSO option in order
            for provider in ["generic_sso", "google", "microsoft", "okta"]:
                if provider in available_sso or provider == "generic_sso":
                    logger.info(f"Trying {provider} SSO")
                    avoid = []
                    if provider != "microsoft":
                        avoid = ["microsoft"]  # Avoid clicking Microsoft when trying other providers
                    
                    if _try_sso_provider(browser, username, password, provider=provider, avoid_providers=avoid):
                        logger.info(f"{provider} SSO login successful")
                        
                        # Wait to make sure we're fully logged in
                        browser.wait(10000)
                        
                        # Check if we're still on a login page
                        if not is_login_page(browser):
                            return True
        
        # Regular username/password flow if no SSO or SSO not requested
        logger.info("Attempting standard login")
        if _standard_login(browser, username, password):
            # Wait to make sure we're fully logged in
            browser.wait(10000)
            
            # Check if we're still on a login page
            if not is_login_page(browser):
                logger.info("Standard login successful")
                return True
            else:
                logger.warning("Still on login page after login attempt")
                return False
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return False
        
    logger.warning("Login process completed but result unclear")
    return True  # Default to True as we want to continue trying


def _try_sso_provider(browser: Browser, username: str, password: str, provider: str, avoid_providers: list = None) -> bool:
    """Try to log in using a specific SSO provider.
    
    Args:
        browser: Browser instance
        username: SSO username/email
        password: SSO password
        provider: Provider name ("google", "microsoft", "okta", or "generic_sso")
        avoid_providers: List of providers to avoid clicking (e.g., ["microsoft"])
        
    Returns:
        True if login appears successful
    """
    if avoid_providers is None:
        avoid_providers = []
        
    if provider not in SSO_SELECTORS:
        logger.warning(f"Unknown SSO provider: {provider}")
        return False
        
    # Get selectors for the provider
    provider_selectors = SSO_SELECTORS[provider]
    
    # Output debug info about the current page
    try:
        html = browser.get_page_html()
        logger.info(f"Current page HTML length: {len(html)}")
        logger.info(f"Current URL: {browser.get_current_url()}")
        
        # Look for provider-related content in the HTML
        if provider.lower() in html.lower():
            logger.info(f"Page contains '{provider}' references")
    except Exception as e:
        logger.warning(f"Error getting page debug info: {e}")
    
    # JavaScript fallback for finding and clicking login buttons
    try:
        logger.info(f"Trying JavaScript fallback to find {provider} button")
        found = browser.execute_script(f"""
            // Look for buttons/links containing the text {provider}
            function findElement() {{
                // Convert provider to lowercase for case-insensitive matching
                const providerLower = "{provider}".toLowerCase();
                
                // List of providers to avoid
                const avoidProviders = {avoid_providers};
                
                // First look for buttons/links with text containing the provider name
                const elements = Array.from(document.querySelectorAll('button, a, div[role="button"], span[role="button"]'));
                
                for (const el of elements) {{
                    // Skip any privacy policy links
                    if (el.href && (
                        el.href.includes("policies.google.com/privacy") ||
                        el.href.includes("privacy") ||
                        el.href.includes("terms")
                    )) {{
                        console.log("Skipping privacy/terms link:", el);
                        continue;
                    }}
                    
                    // Skip elements that are likely not login buttons
                    if (el.innerText && (
                        el.innerText.toLowerCase().includes("privacy") ||
                        el.innerText.toLowerCase().includes("policy") ||
                        el.innerText.toLowerCase().includes("terms") ||
                        el.innerText.toLowerCase().includes("cookie")
                    )) {{
                        console.log("Skipping policy/terms text element:", el);
                        continue;
                    }}
                    
                    // Skip elements for providers we want to avoid
                    let shouldAvoid = false;
                    for (const avoidProvider of avoidProviders) {{
                        if (el.innerText && el.innerText.toLowerCase().includes(avoidProvider.toLowerCase())) {{
                            console.log(`Skipping element containing avoided provider '${avoidProvider}':`, el);
                            shouldAvoid = true;
                            break;
                        }}
                        
                        // Check if any images contain the avoid provider
                        const images = el.querySelectorAll('img');
                        for (const img of images) {{
                            if ((img.alt && img.alt.toLowerCase().includes(avoidProvider.toLowerCase())) ||
                                (img.src && img.src.toLowerCase().includes(avoidProvider.toLowerCase()))) {{
                                console.log(`Skipping element with image of avoided provider '${avoidProvider}':`, el);
                                shouldAvoid = true;
                                break;
                            }}
                        }}
                        
                        if (shouldAvoid) {{
                            break;
                        }}
                    }}
                    
                    if (shouldAvoid) {{
                        continue;
                    }}
                    
                    // Check the text content for login-related text
                    if (el.innerText && el.innerText.toLowerCase().includes(providerLower)) {{
                        // Make sure it's a login button by checking for login-related text
                        if (
                            el.innerText.toLowerCase().includes("sign in") ||
                            el.innerText.toLowerCase().includes("login") ||
                            el.innerText.toLowerCase().includes("log in") ||
                            el.innerText.toLowerCase().includes("continue with")
                        ) {{
                            console.log("Found login button by text content:", el);
                            return el;
                        }}
                        
                        // If it mentions the provider prominently, it's likely a login button
                        if (el.tagName === "BUTTON" || el.role === "button") {{
                            console.log("Found button with provider mention:", el);
                            return el;
                        }}
                    }}
                    
                    // For Google specific detection
                    if (providerLower === "google" && el.innerText && 
                        (el.innerText.toLowerCase().includes("google") || 
                         el.innerText.toLowerCase() === "g")) {{
                        console.log("Found Google-specific button:", el);
                        return el;
                    }}
                    
                    // For Microsoft specific detection
                    if (providerLower === "microsoft" && el.innerText && 
                        (el.innerText.toLowerCase().includes("microsoft") || 
                         el.innerText.toLowerCase().includes("azure") ||
                         el.innerText.toLowerCase().includes("office 365"))) {{
                        console.log("Found Microsoft-specific button:", el);
                        return el;
                    }}
                    
                    // Check aria-label for login-related text
                    if (el.getAttribute('aria-label') && 
                        el.getAttribute('aria-label').toLowerCase().includes(providerLower)) {{
                        if (
                            el.getAttribute('aria-label').toLowerCase().includes("sign in") ||
                            el.getAttribute('aria-label').toLowerCase().includes("login") ||
                            el.getAttribute('aria-label').toLowerCase().includes("log in")
                        ) {{
                            console.log("Found by aria-label:", el);
                            return el;
                        }}
                    }}
                    
                    // Check for nested images with alt text or src containing provider
                    const images = el.querySelectorAll('img');
                    for (const img of images) {{
                        if ((img.alt && img.alt.toLowerCase().includes(providerLower)) ||
                            (img.src && img.src.toLowerCase().includes(providerLower))) {{
                            // Skip if the parent has href to privacy
                            if (el.href && (
                                el.href.includes("policies.google.com") ||
                                el.href.includes("privacy") ||
                                el.href.includes("terms")
                            )) {{
                                console.log("Skipping privacy link with provider image:", el);
                                continue;
                            }}
                            console.log("Found via nested image:", el);
                            return el;
                        }}
                    }}
                    
                    // Check for class or id containing provider and looks like a login button
                    if ((el.id && el.id.toLowerCase().includes(providerLower)) ||
                        (el.className && el.className.toLowerCase().includes(providerLower))) {{
                        // Skip if looks like a privacy element
                        if (
                            (el.id && (el.id.toLowerCase().includes("privacy") || el.id.toLowerCase().includes("term"))) ||
                            (el.className && (el.className.toLowerCase().includes("privacy") || el.className.toLowerCase().includes("term")))
                        ) {{
                            console.log("Skipping privacy/terms element:", el);
                            continue;
                        }}
                        console.log("Found by class/id:", el);
                        return el;
                    }}
                }}
                
                return null;
            }}
            
            const element = findElement();
            if (element) {{
                // Get element details for logging
                const details = {{
                    tag: element.tagName,
                    text: element.innerText,
                    className: element.className,
                    id: element.id,
                    href: element.href || null
                }};
                
                console.log("Clicking element:", details);
                element.click();
                return details;
            }}
            return null;
        """)
        
        if found:
            logger.info(f"JavaScript found and clicked {provider} button: {found}")
            browser.wait(10000)  # Wait for redirect
            return _handle_sso_flow(browser, username, password, provider)
    except Exception as e:
        logger.error(f"Error using JavaScript fallback: {e}")
        
    # Now try the regular selectors as fallback
    logger.info(f"Trying {len(provider_selectors)} {provider} selectors: {provider_selectors}")
    
    # Look for any SSO buttons for this provider
    for selector in provider_selectors:
        try:
            # Check if element exists and is visible
            element_info = browser.get_element_info(selector)
            if element_info:
                # Skip if it looks like a privacy policy link
                href = element_info.get('attributes', {}).get('href', '')
                if href and ('privacy' in href or 'policies.google.com' in href or 'terms' in href):
                    logger.info(f"Skipping privacy/terms link: {href}")
                    continue
                
                # Check if this element contains text of a provider we want to avoid
                should_avoid = False
                for avoid_provider in avoid_providers:
                    text = element_info.get('text', '').lower()
                    if avoid_provider.lower() in text:
                        logger.info(f"Skipping element containing avoided provider '{avoid_provider}': {text}")
                        should_avoid = True
                        break
                
                if should_avoid:
                    continue
                
                logger.info(f"Found {provider} element with selector '{selector}': {element_info}")
                if element_info.get('isVisible', False):
                    logger.info(f"VISIBLE {provider} SSO option: {element_info['tag']} with selector '{selector}'")
                    browser.click_selector(selector)
                    browser.wait(8000)  # Increased wait for redirect
                    
                    # Handle provider-specific login
                    return _handle_sso_flow(browser, username, password, provider)
                else:
                    logger.info(f"Element found but NOT VISIBLE: {element_info}")
            else:
                logger.debug(f"No element found with selector: {selector}")
            
            # Fallback to simple selector check
            if browser.wait_for_selector(selector, timeout=2000):  # Increased timeout
                # Check if it's a privacy policy link before clicking
                avoid_check = browser.execute_script(f"""
                    const el = document.querySelector("{selector}");
                    if (!el) return null;
                    
                    // Check for privacy policy
                    if (el.href && (
                        el.href.includes("privacy") || 
                        el.href.includes("policies.google.com") || 
                        el.href.includes("terms")
                    )) {{
                        return "privacy";
                    }}
                    
                    // Check for avoided providers
                    const avoidProviders = {avoid_providers};
                    for (const avoid of avoidProviders) {{
                        if (el.innerText && el.innerText.toLowerCase().includes(avoid.toLowerCase())) {{
                            return avoid;
                        }}
                    }}
                    
                    return null;
                """)
                
                if avoid_check:
                    logger.info(f"Skipping element with '{avoid_check}' content: {selector}")
                    continue
                    
                logger.info(f"Successfully waited for {provider} SSO option: {selector}")
                browser.click_selector(selector)
                browser.wait(8000)  # Increased wait for redirect
                
                # Handle provider-specific login
                return _handle_sso_flow(browser, username, password, provider)
        except Exception as e:
            logger.debug(f"Error trying SSO selector {selector}: {e}")
            continue
    
    logger.warning(f"Could not find any {provider} SSO options on the page")
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
    browser.wait(5000)  # Increased wait time
    
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
        if browser.wait_for_selector(email_selector, timeout=10000):  # Increased timeout
            # Check element state
            element_info = browser.get_element_info(email_selector)
            if element_info:
                logger.info(f"Found email input: {element_info.get('attributes', {})}")
            
            browser.click_selector(email_selector)
            browser.type(username)
            
            # Click next
            next_selector = "button:contains('Next'), button[id='identifierNext']"
            if browser.wait_for_selector(next_selector, timeout=5000):  # Increased timeout
                browser.click_selector(next_selector)
                browser.wait(5000)  # Increased wait time
        
        # Enter password
        password_selector = "input[type='password']"
        if browser.wait_for_selector(password_selector, timeout=10000):  # Increased timeout
            browser.click_selector(password_selector)
            browser.type(password)
            
            # Click sign in
            signin_selector = "button:contains('Sign in'), button[id='passwordNext']"
            if browser.wait_for_selector(signin_selector, timeout=5000):  # Increased timeout
                browser.click_selector(signin_selector)
                
                # Wait longer for Google authentication to complete and redirect back
                browser.wait(15000)  # Substantially increased wait time
                
                # Check if we're redirected back to JIRA
                current_url = browser.get_current_url()
                logger.info(f"Current URL after Google auth: {current_url}")
                
                # Check if we successfully returned to JIRA
                if "atlassian" in current_url or "jira" in current_url:
                    # Wait for JIRA UI to fully load
                    browser.wait(5000)
                    return True
        
        # Handle potential 2FA challenge or other authentication steps
        browser.wait(5000)
        verify_selectors = [
            "input[id='totpPin']",  # TOTP verification code
            "button:contains('Try another way')",
            "button:contains('Verify')"
        ]
        
        for selector in verify_selectors:
            if browser.wait_for_selector(selector, timeout=2000):
                logger.warning("Additional verification detected - may require manual intervention")
                # Wait longer for manual intervention
                browser.wait(30000)
                return True  # Hope the user has completed manual verification
        
        return True  # Assume success if we got this far
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
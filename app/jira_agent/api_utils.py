"""Utilities for interacting with APIs and parsing documentation.

This module provides functions for:
1. Parsing API documentation using LLMs
2. Extracting endpoints and authentication requirements
3. Fallback methods using rule-based parsing
"""

import json
import re
import requests
import logging
import os
from typing import Dict, List, Optional, Any, Union

# Set up logging
logger = logging.getLogger(__name__)

# Default LLM settings
DEFAULT_LLM_MODEL = "gpt-4"  # For OpenAI
DEFAULT_ANTHROPIC_MODEL = "claude-3-opus-20240229"  # For Anthropic


def parse_api_docs_with_llm(
    documentation: Union[Dict, str], 
    llm_api_key: Optional[str] = None,
    llm_api_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Use an LLM to parse API documentation and extract endpoints intelligently.
    
    Args:
        documentation: API documentation as text or JSON
        llm_api_key: API key for the LLM service (OpenAI, Anthropic, etc.)
        llm_api_url: URL for the LLM API endpoint
        
    Returns:
        Dictionary with extracted endpoints and usage information
    """
    if not documentation:
        logger.warning("No documentation provided for parsing")
        return {"endpoints": [], "analysis_endpoint": None}
    
    # Convert documentation to string if it's a dictionary
    doc_text = json.dumps(documentation) if isinstance(documentation, dict) else str(documentation)
    
    # Check if we have an LLM API key (from args or environment)
    llm_api_key = llm_api_key or os.getenv("LLM_API_KEY", "")
    llm_api_url = llm_api_url or os.getenv("LLM_API_URL", "https://api.openai.com/v1/chat/completions")
    
    if not llm_api_key:
        logger.warning("No LLM API key provided. Using rule-based parsing as fallback.")
        return extract_endpoints_rule_based(documentation)
    
    try:
        logger.info("Using LLM to intelligently parse API documentation...")
        
        # Prepare prompt for the LLM
        prompt = f"""
        You are an AI assistant helping to parse API documentation and extract useful information.
        Please analyze this API documentation and extract:
        1. A list of all available endpoints
        2. Which endpoint would be best for sending JIRA ticket data for analysis
        3. Any required headers or authentication methods
        4. Any specific request format requirements
        
        Here's the documentation:
        {doc_text[:4000]}  # Truncate if too large
        
        Response format:
        {{
            "endpoints": ["list", "of", "endpoints"],
            "analysis_endpoint": "recommended_endpoint_for_analysis",
            "auth_method": "authentication method if specified",
            "required_headers": {{"header_name": "description"}},
            "request_format": "description of request format if specified"
        }}
        """
        
        # Make request to LLM API
        headers = {
            "Authorization": f"Bearer {llm_api_key}",
            "Content-Type": "application/json"
        }
        
        # Determine which model to use based on the API URL
        is_openai = "openai" in llm_api_url.lower()
        model = DEFAULT_LLM_MODEL if is_openai else DEFAULT_ANTHROPIC_MODEL
        
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,  # Low temperature for more deterministic results
            "max_tokens": 2000
        }
        
        # Make the actual API call to the LLM
        response = requests.post(llm_api_url, headers=headers, json=payload)
        
        if response.status_code == 200:
            llm_response = response.json()
            
            # Extract content based on API format (different for OpenAI vs Anthropic vs others)
            content = ""
            if is_openai and "choices" in llm_response:  # OpenAI format
                content = llm_response["choices"][0]["message"]["content"]
            elif not is_openai and "content" in llm_response:  # Anthropic format
                content = llm_response["content"][0]["text"]
            else:
                content = str(llm_response)
                logger.warning(f"Unexpected LLM response format: {content[:100]}...")
            
            try:
                # Parse the JSON response
                extracted_data = json.loads(content)
                logger.info(f"LLM successfully parsed documentation and found {len(extracted_data.get('endpoints', []))} endpoints")
                return extracted_data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse LLM response as JSON: {content[:100]}...")
                # Try to extract JSON from the content if it's embedded in other text
                json_match = re.search(r'({.*})', content.replace('\n', ''))
                if json_match:
                    try:
                        extracted_data = json.loads(json_match.group(1))
                        logger.info(f"Extracted JSON from LLM response and found {len(extracted_data.get('endpoints', []))} endpoints")
                        return extracted_data
                    except:
                        pass
        else:
            logger.error(f"LLM API call failed with status {response.status_code}: {response.text}")
        
        # If we get here, something went wrong with the LLM parsing
        logger.warning("Falling back to rule-based parsing")
        return extract_endpoints_rule_based(documentation)
        
    except Exception as e:
        logger.exception(f"Error using LLM to parse documentation: {e}")
        logger.warning("Falling back to rule-based parsing")
        return extract_endpoints_rule_based(documentation)


def extract_endpoints_rule_based(documentation: Union[Dict, str]) -> Dict[str, Any]:
    """
    Extract endpoints from documentation using simple rules.
    Used as a fallback when LLM parsing fails.
    
    Args:
        documentation: Dictionary or string of API documentation
        
    Returns:
        Dictionary with extracted endpoints and analysis endpoint
    """
    endpoints = []
    
    if isinstance(documentation, dict):
        # Look for endpoints in various common documentation formats
        if "paths" in documentation:  # OpenAPI/Swagger format
            endpoints = list(documentation["paths"].keys())
        elif "endpoints" in documentation:
            endpoints = documentation["endpoints"]
        elif "resources" in documentation:
            endpoints = documentation["resources"]
        else:
            # Try to find endpoints by looking at all keys
            for key, value in documentation.items():
                if isinstance(value, dict) and ("url" in value or "path" in value or "endpoint" in value):
                    endpoints.append(key)
    else:
        # For text documentation, try to extract paths using regex
        doc_text = str(documentation)
        endpoints = re.findall(r'["\']?(/[a-zA-Z0-9/_-]+)', doc_text)
        endpoints = list(set(endpoints))  # Remove duplicates
    
    # Determine which endpoint to use for analysis
    analysis_endpoint = None
    for endpoint in endpoints:
        if "analy" in endpoint.lower():
            analysis_endpoint = endpoint
            break
    
    logger.info(f"Rule-based parsing found {len(endpoints)} endpoints")
    return {
        "endpoints": endpoints,
        "analysis_endpoint": analysis_endpoint
    }


def get_api_documentation(api_url: str, guide_path: str = "/docs/guide") -> Dict[str, Any]:
    """
    Fetch API documentation from the given URL.
    
    Args:
        api_url: Base URL of the API
        guide_path: Path to the API documentation or guide
        
    Returns:
        Tuple of (documentation_content, content_type)
    """
    guide_url = f"{api_url.rstrip('/')}{guide_path}"
    logger.info(f"Fetching API documentation from {guide_url}")
    
    try:
        response = requests.get(guide_url, timeout=5)
        
        if response.status_code == 200:
            content_type = response.headers.get('Content-Type', '')
            
            # Return the appropriate format based on content type
            if 'application/json' in content_type:
                return response.json(), 'json'
            else:
                return response.text, 'text'
        else:
            logger.warning(f"Failed to get documentation: HTTP {response.status_code}")
            return None, None
            
    except Exception as e:
        logger.exception(f"Error fetching API documentation: {e}")
        return None, None


def determine_headers(parsed_docs: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, str]:
    """
    Determine the headers to use for API requests based on parsed documentation.
    
    Args:
        parsed_docs: Documentation parsed by LLM or rule-based methods
        api_key: API key to use for authentication (if required)
        
    Returns:
        Dictionary of headers to use for requests
    """
    headers = {}
    
    # If we have information about required headers from the documentation
    if "required_headers" in parsed_docs:
        for header, _ in parsed_docs.get("required_headers", {}).items():
            if header.lower() == "authorization" and api_key:
                auth_method = parsed_docs.get("auth_method", "Bearer").split()[0]
                headers["Authorization"] = f"{auth_method} {api_key}"
                logger.info(f"Added authentication header: {header}")
    # Default to Bearer token if no specific auth method is specified
    elif api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        logger.info("Added default Bearer token authentication header")
        
    return headers 
import os
import json
import re
from typing import List, Dict, Optional, Any
from openai import OpenAI
from app.utils import check_blocklisted_url

class OpenAIWebSearch:
    """Implementation of WebSearch using OpenAI's capabilities."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """Initialize the OpenAI web search client.
        
        Args:
            api_key: OpenAI API key (optional, will use env var if not provided)
            model: OpenAI model to use for completions
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it to the constructor.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
    
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Perform a web search simulation using OpenAI's LLM capabilities.
        
        Note: This is a simulated search that generates plausible results
        rather than an actual web search.
        
        Args:
            query: The search query
            num_results: Number of results to return (default 5)
            
        Returns:
            List of search results with title, url, and snippet
        """
        try:
            # Create a prompt asking for simulated search results
            prompt = f"""
            Simulate a web search for: "{query}"
            
            Return {num_results} plausible search results in this format:
            
            ```json
            [
                {{
                    "title": "Result title",
                    "url": "https://example.com/result-path",
                    "snippet": "Brief description of what this result contains..."
                }},
                ...
            ]
            ```
            
            Rules:
            1. Generate realistic titles, URLs, and snippets
            2. Use real domain names of reputable sites that would have information on this topic
            3. Make URLs look realistic with proper paths
            4. Snippets should be informative and relevant to the query
            5. Return exactly {num_results} results
            6. Return ONLY the JSON array, no other text
            """
            
            # Create a completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # Extract the JSON part using regex
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                # If no code block, try to find array directly
                json_match = re.search(r'\[\s*\{.*\}\s*\]', content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # Fallback to the entire content
                    json_str = content
            
            # Clean up the string and parse JSON
            try:
                results = json.loads(json_str)
                return results[:num_results]  # Ensure we don't exceed requested count
            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")
                print(f"Content received: {content}")
                return [{"title": "Search error", "url": "", "snippet": "Failed to parse search results"}]
                
        except Exception as e:
            print(f"Search error: {str(e)}")
            return [{"title": "Search error", "url": "", "snippet": str(e)}]
    
    def get_content(self, url: str) -> Optional[str]:
        """Simulate fetching content from a webpage using OpenAI.
        
        Note: This is a simulation that generates plausible content
        rather than actually fetching the web page.
        
        Args:
            url: The URL to simulate content from
            
        Returns:
            Simulated string content of the webpage
        """
        try:
            # Check if the URL is blocked
            check_blocklisted_url(url)
            
            # Create a prompt asking for simulated webpage content
            prompt = f"""
            Simulate the main content of a webpage at this URL: {url}
            
            Based on the URL, generate plausible, informative content that might be found on this page.
            Focus on:
            1. The main textual content (articles, information, etc.)
            2. A realistic structure with sections and paragraphs
            3. Relevant information to what the URL suggests
            4. Factual information where possible
            
            Don't include navigation menus, comments, ads, or other non-content elements.
            Write at least 3-4 paragraphs of realistic content.
            """
            
            # Create a completion
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
            
        except ValueError as e:
            print(f"URL blocked: {url}, {str(e)}")
            return None
        except Exception as e:
            print(f"Error simulating content from {url}: {str(e)}")
            return None
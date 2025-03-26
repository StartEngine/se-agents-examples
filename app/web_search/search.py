from typing import Protocol, List, Dict, Optional

class WebSearch(Protocol):
    """Defines the interface for web search capabilities."""
    
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search the web with the given query and return top results.
        
        Args:
            query: The search query string
            num_results: Number of results to return (default 5)
            
        Returns:
            List of result dictionaries with 'title', 'url', and 'snippet' keys
        """
        ...
    
    def get_content(self, url: str) -> Optional[str]:
        """Fetch and return the content of a webpage.
        
        Args:
            url: The URL to fetch content from
            
        Returns:
            String content of the webpage, or None if retrieval fails
        """
        ...
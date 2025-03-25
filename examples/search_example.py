"""
Example demonstrating how to use the browser automation framework for web searches.

This example shows how to:
1. Initialize a browser instance
2. Perform a search
3. Extract and interact with search results
"""

import time
from app.browser_agent.local_playwright import LocalPlaywrightComputer
from app.utils import show_image_cv2

def perform_search(query, num_results=3):
    """
    Performs a web search and extracts the top results.
    
    Args:
        query (str): The search query
        num_results (int): Number of results to extract
        
    Returns:
        list: Top search results
    """
    print(f"Searching for: {query}")
    
    results = []
    
    with LocalPlaywrightComputer(headless=False) as computer:
        # Navigate to search engine
        computer.goto("https://www.bing.com")
        
        # Wait for page to load
        computer.wait(1000)
        
        # Take a screenshot of the search page
        screenshot = computer.screenshot()
        show_image_cv2(screenshot, timeout=1)
        
        # Find and click the search box (approximate coordinates)
        computer.click(500, 300)
        
        # Type the search query
        computer.type(query)
        
        # Press Enter to search
        computer.keypress(["Enter"])
        
        # Wait for results to load
        computer.wait(2000)
        
        # Take a screenshot of the results
        screenshot = computer.screenshot()
        show_image_cv2(screenshot, timeout=2)
        
        # This is a placeholder - in a real application, you would:
        # 1. Extract the actual search results from the page
        # 2. Parse the titles, URLs, and descriptions
        
        # For demo purposes, we'll just create placeholder results
        for i in range(1, num_results + 1):
            results.append({
                "position": i,
                "title": f"Result {i} for '{query}'",
                "url": f"https://example.com/result{i}",
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
        
    return results

if __name__ == "__main__":
    # Example usage
    search_query = "python browser automation"
    search_results = perform_search(search_query)
    
    print("\nSearch Results:")
    for result in search_results:
        print(f"\n  Position: {result['position']}")
        print(f"  Title: {result['title']}")
        print(f"  URL: {result['url']}")
        print(f"  Time: {result['timestamp']}")
    
    print("\nNote: This is a demonstration example. In a real application,")
    print("you would extract actual search results from the page content.")
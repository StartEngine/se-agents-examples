"""
Example demonstrating how to use the web search capability.

This example shows how to:
1. Initialize an OpenAI web search client
2. Perform a web search query (simulated)
3. Retrieve content from a resulting URL (simulated)
"""

from app.web_search.openai_search import OpenAIWebSearch
import json

def perform_web_research(topic: str):
    """
    Uses web search to research a topic and gather information.
    
    Args:
        topic: The research topic
        
    Returns:
        dict: Research results and sources
    """
    print(f"Researching topic: {topic}...")
    
    # Create a web search client
    # Using GPT-4o as the default model for high-quality responses
    search_client = OpenAIWebSearch(model="gpt-4o")
    
    # Perform the search (simulated)
    print(f"Searching for: {topic} latest information...")
    search_results = search_client.search(f"{topic} latest information", num_results=3)
    
    print(f"\nFound {len(search_results)} search results:")
    for i, result in enumerate(search_results, 1):
        print(f"\n{i}. {result['title']}")
        print(f"   URL: {result['url']}")
        print(f"   {result['snippet']}")
    
    # Fetch content from the first relevant result (simulated)
    content = None
    if search_results and search_results[0]['url']:
        first_url = search_results[0]['url']
        print(f"\nFetching content from: {first_url}...")
        content = search_client.get_content(first_url)
        
        if content:
            print(f"\nContent excerpt (first 200 chars):")
            print(f"{content[:200]}...")
        else:
            print("Failed to retrieve content.")
    
    # Prepare and return research results
    research_data = {
        "topic": topic,
        "search_results": search_results,
        "content_sample": content[:500] if content else None,
        "sources": [result['url'] for result in search_results if result['url']]
    }
    
    return research_data

if __name__ == "__main__":
    # Example usage
    research_topic = "artificial intelligence advances 2025"
    results = perform_web_research(research_topic)
    
    print("\n=== Research Summary ===")
    print(f"Topic: {results['topic']}")
    print(f"Number of sources: {len(results['sources'])}")
    
    print("\nNote: This example demonstrates the web search capabilities.")
    print("In a real application, you could perform more in-depth analysis of the content.")
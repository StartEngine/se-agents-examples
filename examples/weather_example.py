"""
Example demonstrating how to use the browser automation framework to check weather.

This example shows how to:
1. Initialize a local browser instance using the LocalPlaywrightComputer
2. Navigate to a weather website
3. Take screenshots
4. Extract weather information
"""

import time
from app.browser_agent.local_playwright import LocalPlaywrightComputer
from app.utils import show_image, show_image_cv2

def check_weather(location):
    """
    Checks the weather for a given location using a browser.
    
    Args:
        location (str): The city or location to check weather for
        
    Returns:
        dict: Weather information including temperature and conditions
    """
    print(f"Checking weather for {location}...")
    
    # Create a headless browser instance (set headless=False to see the browser)
    with LocalPlaywrightComputer(headless=False) as computer:
        # Navigate to Bing for weather search
        computer.goto(f"https://www.bing.com/search?q=weather+in+{location}")
        
        # Wait for the page to load
        computer.wait(2000)  # 2 seconds
        
        # Take a screenshot
        screenshot = computer.screenshot()
        
        # Display the screenshot
        print("Displaying screenshot (will close after 2 seconds)...")
        show_image_cv2(screenshot, timeout=2)
        
        # Print the current URL
        print(f"Current URL: {computer.get_current_url()}")
        
        # You could also perform interactions here, like:
        # - Clicking on elements
        # - Typing in search boxes
        # - Scrolling the page
        
        # This is a simple example - in a real application, you would extract
        # the weather information from the page content
        
        return {
            "location": location,
            "checked_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": computer.get_current_url()
        }

if __name__ == "__main__":
    # Example usage
    location = "Hyderabad"
    weather_info = check_weather(location)
    
    print("\nWeather check completed:")
    for key, value in weather_info.items():
        print(f"  {key}: {value}")
    
    print("\nNote: This is a demonstration example. In a real application,")
    print("you would extract actual weather data from the page content.")
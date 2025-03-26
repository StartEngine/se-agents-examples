# SE Agents Examples

This project provides a framework for browser automation using Playwright, designed to be used with agent systems.

## Overview

The framework allows for programmatic control of web browsers through a simple interface. It can be used to:

- Automate web browsing tasks
- Take screenshots
- Handle user interactions (clicks, typing, scrolling)
- Block access to specified domains for safety

## Features

- **Computer Protocol**: Defines a standard interface for browser automation
- **Playwright Integration**: Uses the Playwright library for browser control
- **Safety Measures**: Includes URL blocking for specified domains
- **Image Handling**: Utilities for displaying and processing screenshots
- **API Integration**: Helper functions for OpenAI API communication

## Getting Started

### Prerequisites

- Python 3.9+
- Playwright browser binaries
- OpenCV for image processing
- OpenAI API key (for certain integrations)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/startengine/se-agents-examples.git
   cd se-agents-examples
   ```

2. Set up a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Playwright browsers:
   ```bash
   playwright install
   ```

5. Create a `.env` file with your API keys (you can copy from the provided template):
   ```bash
   cp .env.example .env
   # Then edit .env with your actual API keys
   ```

## Usage

### Basic Example

```python
from app.browser_agent.local_playwright import LocalPlaywrightComputer

# Create a computer instance (headless=False to see the browser window)
with LocalPlaywrightComputer(headless=False) as computer:
    # Navigate to a URL
    computer.goto("https://example.com")
    
    # Take a screenshot
    screenshot = computer.screenshot()
    
    # Click on coordinates
    computer.click(100, 200)
    
    # Type text
    computer.type("Hello, world!")
    
    # Press keys
    computer.keypress(["Enter"])
    
    # Wait for page to load
    computer.wait(2000)  # milliseconds
```

### Displaying Screenshots

```python
from app.utils import show_image, show_image_cv2

# Display screenshot using PIL
show_image(screenshot)

# Display screenshot using OpenCV (with auto-close after 2 seconds)
show_image_cv2(screenshot, timeout=2)
```

## Examples

The project includes example scripts in the `examples/` directory to help you get started:

### Browser Automation Examples

#### Weather Example

The `weather_example.py` script demonstrates how to:
- Launch a browser and navigate to a weather search page
- Take and display screenshots
- Handle basic browser automation for weather information

Run it with:
```bash
python -m examples.weather_example
```

#### Search Example

The `search_example.py` script shows how to:
- Perform web searches using a browser
- Interact with search results
- Process and extract information from search pages

Run it with:
```bash
python -m examples.search_example
```

### Web Search API Example

#### Web Search Example

The `web_search_example.py` script demonstrates how to:
- Use OpenAI's capabilities to simulate web search
- Perform searches without browser automation
- Generate plausible content based on URLs

Run it with:
```bash
python -m examples.web_search_example
```

These examples provide a starting point for building more complex automation and search tasks.

## Project Structure

- `app/`: Main package directory
  - `browser_agent/`: Browser automation implementations
    - `computer.py`: Protocol defining the browser interface
    - `base_playwright.py`: Base class for Playwright-based browser automation
    - `local_playwright.py`: Implementation for local browser automation
  - `web_search/`: Web search implementations
    - `search.py`: Protocol defining the web search interface
    - `openai_search.py`: Implementation using OpenAI's web search capability
  - `computers/`: Alternative implementation path (identical to browser_agent)
  - `utils.py`: Utility functions for image handling, URL safety, API communication
- `examples/`: Example scripts demonstrating usage
  - `weather_example.py`: Example for checking weather information with browser
  - `search_example.py`: Example for performing web searches with browser
  - `web_search_example.py`: Example for web searches using OpenAI API

## Safety Features

The project includes domain blocking functionality to prevent navigation to specified domains. This is handled through the `BLOCKED_DOMAINS` list in `utils.py`. You can customize this list to add additional domains that should be blocked.

```python
BLOCKED_DOMAINS = [
    "maliciousbook.com",
    "evilvideos.com",
    # Add your own domains to block
]
```

## Agent Integration

This project is designed to be used with LLM agents by providing a "Computer" tool that gives agents the ability to control a web browser. The agent can be given access to browser controls through a simple protocol interface.

### Computer Protocol

The `Computer` protocol defines the interface an agent can use to control the browser:

```python
class Computer(Protocol):
    """Defines the 'shape' (methods/properties) our loop expects."""

    @property
    def environment(self) -> Literal["windows", "mac", "linux", "browser"]: ...
    @property
    def dimensions(self) -> tuple[int, int]: ...

    def screenshot(self) -> str: ...
    def click(self, x: int, y: int, button: str = "left") -> None: ...
    def double_click(self, x: int, y: int) -> None: ...
    def scroll(self, x: int, y: int, scroll_x: int, scroll_y: int) -> None: ...
    def type(self, text: str) -> None: ...
    def wait(self, ms: int = 1000) -> None: ...
    def move(self, x: int, y: int) -> None: ...
    def keypress(self, keys: List[str]) -> None: ...
    def drag(self, path: List[Dict[str, int]]) -> None: ...
    def get_current_url() -> str: ...
```

When integrated with an agent system, the agent can use this interface to control the browser and perform complex tasks.

## Utilities

The project includes several utility functions:

- `show_image()`: Display a base64-encoded image using PIL
- `show_image_cv2()`: Display a base64-encoded image using OpenCV with auto-close
- `calculate_image_dimensions()`: Get width and height of an image
- `check_blocklisted_url()`: Validate URLs against blocked domains
- `create_response()`: Helper for OpenAI API communication

## License

[MIT License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
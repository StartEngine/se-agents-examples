"""
This file redirects to the actual implementation in the top_issuers directory.
This provides backwards compatibility for existing imports.
"""

import sys
from pathlib import Path

# Import from the actual implementation
try:
    from examples.top_issuers.top_issuers_example import *
except ImportError:
    # If run directly
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from examples.top_issuers.top_issuers_example import *

# If this file is run directly
if __name__ == "__main__":
    # Import and run the main function from the actual implementation
    from examples.top_issuers.top_issuers_example import run_query_and_download
    
    # Redirect to the actual implementation
    print("This file has been moved to examples/top_issuers/top_issuers_example.py")
    print("Redirecting to the actual implementation...")
    
    # Import the __main__ block code and run it
    import examples.top_issuers.top_issuers_example as actual_implementation
    
    # Run the code in the actual implementation's __main__ block
    sys.argv[0] = "examples/top_issuers/top_issuers_example.py"
    
    # Execute the main code
    if hasattr(actual_implementation, '__main__'):
        main_code = getattr(actual_implementation, '__main__')
        exec(main_code)
    else:
        # If there's no __main__ attribute (unlikely), run the file directly
        import runpy
        runpy.run_path(
            str(Path(__file__).resolve().parent / "top_issuers" / "top_issuers_example.py"), 
            run_name="__main__"
        )
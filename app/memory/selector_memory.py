"""Selector memory system for web automation agents.

Provides a simple but effective memory system for storing and retrieving
CSS/XPath selectors used by browser automation agents. Each agent gets
its own isolated memory space to avoid cross-contamination.
"""

import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, Optional, Any

class SelectorMemory:
    """Memory system for storing UI element selectors used by browser agents.
    
    Maintains a JSON-based memory store for each agent to remember successful
    selectors for common UI elements (buttons, forms, etc.) with metadata
    like success rate and timestamp.
    
    Example:
        memory = SelectorMemory("metabase")
        login_button = memory.get_selector("login_page", "login_button")
        
        # After successful interaction
        memory.update_selector("login_page", "login_button", ".login-btn", success=True)
    """
    
    def __init__(self, agent_name: str, cache_dir: str = "./cache"):
        """Initialize a new selector memory for a specific agent.
        
        Args:
            agent_name: Unique name of the agent (e.g., "metabase", "hubspot")
            cache_dir: Base directory for storing memory files
        """
        self.agent_name = agent_name
        self.cache_dir = Path(cache_dir) / agent_name
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.memory_file = self.cache_dir / "selector_memory.json"
        self.memory = self._load_memory()
        self.logger = logging.getLogger(f"SelectorMemory.{agent_name}")
        
    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from disk or create empty memory if file doesn't exist."""
        if self.memory_file.exists():
            try:
                with open(self.memory_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                self.logger.warning(f"Memory file corrupted, creating new memory")
                return {}
        return {}
        
    def save(self) -> None:
        """Save current memory state to disk."""
        with open(self.memory_file, "w") as f:
            json.dump(self.memory, f, indent=2)
            
    def get_selector(self, page: str, element_name: str) -> Optional[str]:
        """Retrieve a selector for a specific UI element.
        
        Args:
            page: The logical page/screen name (e.g., "login_page", "dashboard")
            element_name: Name of the UI element (e.g., "submit_button")
            
        Returns:
            The selector string if found, None otherwise
        """
        if page in self.memory and element_name in self.memory[page]:
            # Update last accessed time
            self.memory[page][element_name]["last_accessed"] = time.time()
            self.save()
            return self.memory[page][element_name]["selector"]
        return None
        
    def update_selector(self, page: str, element_name: str, selector: str, success: bool = True) -> None:
        """Store or update a selector with success information.
        
        Args:
            page: The logical page/screen name
            element_name: Name of the UI element
            selector: The CSS/XPath selector string
            success: Whether the selector worked successfully
        """
        if page not in self.memory:
            self.memory[page] = {}
            
        # If entry exists, update confidence score
        if element_name in self.memory[page]:
            entry = self.memory[page][element_name]
            # Simple exponential moving average for confidence score
            current_rate = entry.get("success_rate", 0.5)
            alpha = 0.3  # Weight for new observation
            new_rate = (alpha * (1.0 if success else 0.0)) + ((1-alpha) * current_rate)
            
            self.memory[page][element_name].update({
                "selector": selector,
                "success_rate": new_rate,
                "last_updated": time.time(),
                "last_accessed": time.time(),
                "uses": entry.get("uses", 0) + 1
            })
        else:
            # Create new entry
            self.memory[page][element_name] = {
                "selector": selector,
                "success_rate": 1.0 if success else 0.0,
                "last_updated": time.time(),
                "last_accessed": time.time(),
                "uses": 1
            }
            
        self.save()
    
    def get_selectors_for_page(self, page: str) -> Dict[str, str]:
        """Get all remembered selectors for a specific page.
        
        Args:
            page: The logical page name
            
        Returns:
            Dictionary mapping element names to their selectors
        """
        if page not in self.memory:
            return {}
            
        return {elem: data["selector"] 
                for elem, data in self.memory[page].items() 
                if data.get("success_rate", 0) > 0.3}  # Only return selectors with decent success rate
    
    def forget_selector(self, page: str, element_name: str) -> None:
        """Remove a selector from memory."""
        if page in self.memory and element_name in self.memory[page]:
            del self.memory[page][element_name]
            self.save()
            
    def clear_memory(self) -> None:
        """Reset memory completely."""
        self.memory = {}
        self.save()
        self.logger.info(f"Memory cleared for agent {self.agent_name}")
        
    def clean_old_selectors(self, max_age_days: int = 30) -> int:
        """Remove selectors that haven't been used recently.
        
        Args:
            max_age_days: Number of days after which unused selectors are removed
            
        Returns:
            Number of selectors removed
        """
        count = 0
        now = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        for page in list(self.memory.keys()):
            for element in list(self.memory[page].keys()):
                last_access = self.memory[page][element].get("last_accessed", 0)
                if now - last_access > max_age_seconds:
                    del self.memory[page][element]
                    count += 1
                    
            # Clean up empty pages
            if not self.memory[page]:
                del self.memory[page]
                
        if count > 0:
            self.save()
            self.logger.info(f"Cleaned {count} old selectors")
            
        return count

# Madison Boyd
# CSC 405
# Iteration 3

# models/usersettings.py

# Import dataclass to automatically generate standard methods like __init__
from dataclasses import dataclass, field 

# Import field to customize the initialization of our lists/dictionaries
from typing import List, Dict 

@dataclass # Decorator that converts the class into a data-container
class UserSettings: # Define the blueprint for user settings
    # Define purchase_history as a list of strings, defaulting to an empty list
    purchase_history: List[str] = field(default_factory=list) 
    # Define wishlist as a list of strings, defaulting to an empty list
    wishlist: List[str] = field(default_factory=list) 
    # Define view_info as a dictionary,  to ensure a fresh dict for every instance
    view_info: Dict = field(default_factory=lambda: {"theme": "light", "display": "compact"})
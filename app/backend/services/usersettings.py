# Madison  Boyd
# CSC 405
# Iteration 3

# services/usersettings.py

# Import the UserSettings class from the models folder
from backend.models.usersettings import UserSettings 

# create an object to act as our primary data store
_data = UserSettings(
    purchase_history=["Product A", "Product B"], # Pre-populate with data
    wishlist=[], # Start with an empty list for wishlist
    view_info={"theme": "dark"} # Default theme setting
)

# Define a function to retrieve the current state of settings
def get_settings() -> UserSettings:
    return _data # Return the data object

# Define a function to add items, c
def update_wishlist(item_name: str) -> bool:
    # Logic: Only add if the item is not already present to avoid duplicates
    if item_name not in _data.wishlist: 
        _data.wishlist.append(item_name) # Add the item to the list
        return True # Return true to indicate success
    return False # Return false to indicate it was a duplicate


def update_purchase_history(item_name: str) -> None:
    # Append purchased item to purchase history in insertion order.
    _data.purchase_history.append(item_name)
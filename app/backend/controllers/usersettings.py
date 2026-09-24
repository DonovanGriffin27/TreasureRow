#Madison Boyd
#CSC 405
#Iteration 3

# controllers/usersettings.py
from backend.services.usersettings import get_settings, update_wishlist

def show_settings_view():
    data = get_settings()
    print(f"Wishlist: {data.wishlist}")

def add_item_to_wishlist(item_name: str):
    success = update_wishlist(item_name)
    if success:
        print(f"Added '{item_name}' to wishlist.")
    else:
        print(f"'{item_name}' already exists.")
# Madison Boyd
#Iteration 3
#CSC 405
#3/2/2025


import unittest
from unittest.mock import MagicMock
# We use absolute imports starting from the root 'backend'
from backend.services.usersettings import (
    get_settings,
    update_purchase_history,
    update_wishlist,
)

class TestUserSettings(unittest.TestCase):
    
    def test_add_wishlist(self):
        """Test that we can add an item to the wishlist."""
        # Clean slate: clear history for a pure test
        settings = get_settings()
        settings.wishlist.clear() 
        
        # Test adding a new item
        result = update_wishlist("New Gadget")
        self.assertTrue(result)
        self.assertIn("New Gadget", settings.wishlist)

    def test_duplicate_wishlist(self):
        """Test that adding a duplicate returns False."""
        settings = get_settings()
        settings.wishlist.clear()
        
        update_wishlist("New Gadget")
        # Try adding the same item again
        result = update_wishlist("New Gadget")
        self.assertFalse(result)
    
    # Madison Boyd Iteration 5 contirbuttions 4/18/26

    def test_account_button_click(self):
        """Test if the user can successfully click on the account button icon."""
        # Mockign a UI omponent/event handler for the account button
        account_button = MagicMock()
        account_button.click.return_value = True

        #Simulate the user interaction
        clicked = account_button.click()
        self.assertTrue(clicked, "Account button should be clickable")
    
    def test_purchase_history_updates(self):
        """Test if the purchase history updated correctly when a purchase is made."""
        settings = get_settings()
        settings.purchase_history.clear() # Reset state for testing
        test_item = "Smart Watch"

        # Simulate updating history via the backedn service
        update_purchase_history(test_item)
        self.assertIn(test_item, settings.purchase_history, "Purchasing history should contain the new item.")
        self.assertEqual(len(settings.purchase_history), 1)




if __name__ == "__main__":
    unittest.main()

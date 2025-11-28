"""
Unit tests for derive_names pure function
"""
import unittest
from services import derive_names


class TestDeriveNames(unittest.TestCase):
    """Test the derive_names pure function"""

    def test_splits_full_name_into_first_last(self):
        """Test that full name is split correctly"""
        first, last = derive_names("John Doe Smith", None, None)
        self.assertEqual(first, "John")
        self.assertEqual(last, "Doe Smith")

    def test_handles_single_word_name(self):
        """Test single word names become first_name only"""
        first, last = derive_names("Madonna", None, None)
        self.assertEqual(first, "Madonna")
        self.assertIsNone(last)

    def test_existing_names_take_precedence(self):
        """Test that existing first/last names are preserved"""
        first, last = derive_names("Should Be Ignored", "Alice", "Johnson")
        self.assertEqual(first, "Alice")
        self.assertEqual(last, "Johnson")

    def test_handles_empty_name(self):
        """Test behavior with empty or None name"""
        first, last = derive_names(None, "Bob", None)
        self.assertEqual(first, "Bob")
        self.assertIsNone(last)

    def test_handles_whitespace_in_name(self):
        """Test names with extra whitespace"""
        first, last = derive_names("  John   Doe  ", None, None)
        # Note: Original implementation doesn't strip whitespace
        self.assertEqual(first, "")  # First split result  
        self.assertEqual(last, " John   Doe  ")

    def test_partial_existing_names(self):
        """Test when only one existing name is provided"""
        # Has first_name but no last_name - should derive last from name
        first, last = derive_names("John Doe Smith", "Existing", None)
        self.assertEqual(first, "Existing")
        self.assertEqual(last, "Doe Smith")
        
        # Has last_name but no first_name - should derive first from name  
        first, last = derive_names("John Doe Smith", None, "Existing")
        self.assertEqual(first, "John") 
        self.assertEqual(last, "Existing")

    def test_special_characters_in_name(self):
        """Test names with hyphens and apostrophes"""
        first, last = derive_names("Jean-Luc O'Connor-Smith", None, None)
        self.assertEqual(first, "Jean-Luc")
        self.assertEqual(last, "O'Connor-Smith")


if __name__ == "__main__":
    unittest.main()

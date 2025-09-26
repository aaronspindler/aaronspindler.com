from django.test import TestCase
from pages.utils import get_books


class GetBooksTest(TestCase):
    """Test the get_books utility function."""
    
    def test_get_books_returns_list(self):
        """Test that get_books returns a list."""
        books = get_books()
        
        self.assertIsInstance(books, list)
        self.assertTrue(len(books) > 0)
        
    def test_get_books_structure(self):
        """Test that books have the correct structure."""
        books = get_books()
        
        for book in books:
            self.assertIn('name', book)
            self.assertIn('author', book)
            self.assertIn('cover_image', book)
            
            self.assertIsInstance(book['name'], str)
            self.assertIsInstance(book['author'], str)
            self.assertIsInstance(book['cover_image'], str)
            
    def test_get_books_sorting(self):
        """Test that books are sorted alphabetically by name."""
        books = get_books()
        
        # Get the book names
        names = [book['name'] for book in books]
        
        # Check that they're sorted
        sorted_names = sorted(names)
        self.assertEqual(names, sorted_names)
        
    def test_get_books_specific_books(self):
        """Test that specific known books are present."""
        books = get_books()
        book_names = [book['name'] for book in books]
        
        # Check for some specific books
        self.assertIn('Permanent Record', book_names)
        self.assertIn('Principles', book_names)
        self.assertIn('Cracking the Coding Interview', book_names)
        
    def test_get_books_optional_fields(self):
        """Test that some books have optional fields."""
        books = get_books()
        
        # Find a book with favourite_quote
        books_with_quotes = [
            book for book in books 
            if 'favourite_quote' in book
        ]
        
        self.assertTrue(len(books_with_quotes) > 0)
        
        # Check the structure of books with quotes
        for book in books_with_quotes:
            self.assertIsInstance(book['favourite_quote'], str)
            self.assertTrue(len(book['favourite_quote']) > 0)
            
    def test_get_books_cover_images(self):
        """Test that cover images have correct format."""
        books = get_books()
        
        for book in books:
            cover = book['cover_image']
            
            # Should start with 'images/'
            self.assertTrue(cover.startswith('images/'))
            
            # Should have an image extension
            valid_extensions = ['.jpg', '.jpeg', '.png']
            has_valid_extension = any(
                cover.endswith(ext) for ext in valid_extensions
            )
            self.assertTrue(
                has_valid_extension,
                f"Book '{book['name']}' has invalid cover image extension: {cover}"
            )
            
    def test_get_books_consistency(self):
        """Test that get_books returns consistent results."""
        books1 = get_books()
        books2 = get_books()
        
        self.assertEqual(books1, books2)
        
    def test_get_books_no_duplicates(self):
        """Test that there are no duplicate books."""
        books = get_books()
        
        book_names = [book['name'] for book in books]
        unique_names = set(book_names)
        
        self.assertEqual(len(book_names), len(unique_names))
        
    def test_get_books_author_format(self):
        """Test that authors are properly formatted."""
        books = get_books()
        
        for book in books:
            author = book['author']
            
            # Author should not be empty
            self.assertTrue(len(author) > 0)
            
            # Author should not have leading/trailing whitespace
            self.assertEqual(author, author.strip())
            
    def test_get_books_known_count(self):
        """Test that we have the expected number of books."""
        books = get_books()
        
        # We know from the code there are 16 books
        self.assertEqual(len(books), 16)
        
    def test_get_books_edward_snowden(self):
        """Test that Edward Snowden's book has specific quote."""
        books = get_books()
        
        snowden_book = next(
            (book for book in books if book['author'] == 'Edward Snowden'),
            None
        )
        
        self.assertIsNotNone(snowden_book)
        self.assertEqual(snowden_book['name'], 'Permanent Record')
        self.assertIn('favourite_quote', snowden_book)
        self.assertIn('Credit cards', snowden_book['favourite_quote'])
        
    def test_get_books_django_books(self):
        """Test that Django-related books are present."""
        books = get_books()
        
        django_books = [
            book for book in books 
            if 'django' in book['name'].lower()
        ]
        
        # Should have at least 2 Django books
        self.assertGreaterEqual(len(django_books), 2)
        
        # Check specific Django books
        book_names = [book['name'] for book in django_books]
        self.assertIn('Django 3 By Example', book_names)
        self.assertIn('Django For Professionals', book_names)

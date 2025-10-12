from django.test import TestCase
from pathlib import Path
from unittest.mock import patch
import os
import tempfile
import shutil
from pages.templatetags.css_version import versioned_css


class VersionedCssTemplateTagTest(TestCase):
    """Test the versioned_css template tag."""
    
    def setUp(self):
        # Create a temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.static_css_dir = os.path.join(self.temp_dir, 'static', 'css')
        os.makedirs(self.static_css_dir)
        
    def tearDown(self):
        # Clean up temporary directory
        shutil.rmtree(self.temp_dir)
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_with_versioned_file(self, mock_settings):
        """Test that versioned CSS file is found and returned."""
        mock_settings.BASE_DIR = self.temp_dir
        
        # Create a versioned CSS file
        versioned_file = os.path.join(self.static_css_dir, 'combined.min.abc123.css')
        Path(versioned_file).touch()
        
        result = versioned_css()
        
        self.assertEqual(result, 'css/combined.min.abc123.css')
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_fallback(self, mock_settings):
        """Test fallback when no versioned CSS file exists."""
        mock_settings.BASE_DIR = self.temp_dir
        
        # No versioned files exist
        result = versioned_css()
        
        self.assertEqual(result, 'css/combined.min.css')
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_multiple_versions(self, mock_settings):
        """Test that the most recent versioned file is selected."""
        mock_settings.BASE_DIR = self.temp_dir
        
        # Create multiple versioned files with different timestamps
        import time
        
        file1 = os.path.join(self.static_css_dir, 'combined.min.old123.css')
        Path(file1).touch()
        time.sleep(0.01)  # Ensure different modification times
        
        file2 = os.path.join(self.static_css_dir, 'combined.min.newer456.css')
        Path(file2).touch()
        time.sleep(0.01)
        
        file3 = os.path.join(self.static_css_dir, 'combined.min.newest789.css')
        Path(file3).touch()
        
        result = versioned_css()
        
        self.assertEqual(result, 'css/combined.min.newest789.css')
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_with_non_matching_files(self, mock_settings):
        """Test that only properly formatted versioned files are considered."""
        mock_settings.BASE_DIR = self.temp_dir
        
        # Create files that shouldn't match
        Path(os.path.join(self.static_css_dir, 'combined.css')).touch()
        Path(os.path.join(self.static_css_dir, 'style.min.abc123.css')).touch()
        Path(os.path.join(self.static_css_dir, 'combined.min.css')).touch()
        
        result = versioned_css()
        
        # Should fallback since no versioned combined.min.*.css exists
        self.assertEqual(result, 'css/combined.min.css')
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_with_hash_format(self, mock_settings):
        """Test with various hash formats in filename."""
        mock_settings.BASE_DIR = self.temp_dir
        
        # Test with different hash lengths
        test_files = [
            'combined.min.a1b2c3d4.css',  # 8 chars (typical MD5 prefix)
            'combined.min.abc123def456.css',  # 12 chars
            'combined.min.short.css',  # Short hash
        ]
        
        for filename in test_files:
            # Clean up previous files
            for f in Path(self.static_css_dir).glob('combined.min.*.css'):
                f.unlink()
                
            # Create test file
            Path(os.path.join(self.static_css_dir, filename)).touch()
            
            result = versioned_css()
            
            self.assertEqual(result, f'css/{filename}')
            
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_handles_missing_directory(self, mock_settings):
        """Test graceful handling when CSS directory doesn't exist."""
        mock_settings.BASE_DIR = '/nonexistent/path'
        
        result = versioned_css()
        
        # Should return fallback
        self.assertEqual(result, 'css/combined.min.css')
        
    @patch('pages.templatetags.css_version.Path.glob')
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_handles_glob_error(self, mock_settings, mock_glob):
        """Test error handling in glob operation."""
        mock_settings.BASE_DIR = self.temp_dir
        mock_glob.side_effect = Exception('Glob error')
        
        result = versioned_css()
        
        # Should return fallback on error
        self.assertEqual(result, 'css/combined.min.css')
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_preserves_path_format(self, mock_settings):
        """Test that returned path format is consistent."""
        mock_settings.BASE_DIR = self.temp_dir
        
        # Create a versioned file
        Path(os.path.join(self.static_css_dir, 'combined.min.v123.css')).touch()
        
        result = versioned_css()
        
        # Should start with 'css/' and end with '.css'
        self.assertTrue(result.startswith('css/'))
        self.assertTrue(result.endswith('.css'))
        
        # Should not contain full path
        self.assertNotIn(self.temp_dir, result)
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_with_similar_names(self, mock_settings):
        """Test that only exact pattern matches are considered."""
        mock_settings.BASE_DIR = self.temp_dir
        
        # Create files with similar but not matching patterns
        Path(os.path.join(self.static_css_dir, 'combined.min.abc.css.bak')).touch()
        Path(os.path.join(self.static_css_dir, 'combined.abc.min.css')).touch()
        Path(os.path.join(self.static_css_dir, 'combined-min.abc.css')).touch()
        
        result = versioned_css()
        
        # None of these should match, so fallback
        self.assertEqual(result, 'css/combined.min.css')
        
    @patch('pages.templatetags.css_version.settings')
    def test_versioned_css_modification_time_ordering(self, mock_settings):
        """Test that files are correctly ordered by modification time."""
        mock_settings.BASE_DIR = self.temp_dir
        
        import time
        
        # Create files in reverse order
        file3 = os.path.join(self.static_css_dir, 'combined.min.third.css')
        Path(file3).touch()
        os.utime(file3, (time.time() - 300, time.time() - 300))  # 5 minutes ago
        
        file2 = os.path.join(self.static_css_dir, 'combined.min.second.css')
        Path(file2).touch()
        os.utime(file2, (time.time() - 600, time.time() - 600))  # 10 minutes ago
        
        file1 = os.path.join(self.static_css_dir, 'combined.min.first.css')
        Path(file1).touch()
        os.utime(file1, (time.time() - 900, time.time() - 900))  # 15 minutes ago
        
        result = versioned_css()
        
        # Should return the most recent (third)
        self.assertEqual(result, 'css/combined.min.third.css')

from django.test import TestCase
from django.core.management import call_command
from unittest.mock import patch, MagicMock
from io import StringIO
import os
import tempfile
import shutil
from pathlib import Path


class ClearCacheCommandTest(TestCase):
    """Test the clear_cache management command."""
    
    @patch('pages.management.commands.clear_cache.cache')
    def test_clear_cache_command(self, mock_cache):
        """Test that clear_cache command clears the cache."""
        call_command('clear_cache')
        
        mock_cache.clear.assert_called_once()
        

class CollectStaticOptimizeCommandTest(TestCase):
    """Test the collectstatic_optimize management command."""
    
    @patch('pages.management.commands.collectstatic_optimize.call_command')
    @patch('pages.management.commands.collectstatic_optimize.Image')
    @patch('pages.management.commands.collectstatic_optimize.os.walk')
    def test_collectstatic_optimize_command(self, mock_walk, mock_image_class, mock_call_command):
        """Test collectstatic_optimize command."""
        # Setup mock file structure
        mock_walk.return_value = [
            ('/static', [], ['test.png', 'test.jpg', 'test.txt'])
        ]
        
        # Setup mock image
        mock_image = MagicMock()
        mock_image_class.open.return_value.__enter__.return_value = mock_image
        
        # Mock file sizes and existence
        with patch('pages.management.commands.collectstatic_optimize.os.path.getsize') as mock_getsize:
            with patch('pages.management.commands.collectstatic_optimize.os.path.exists', return_value=True):
                mock_getsize.side_effect = [1000, 800, 1200, 900]  # Original then optimized for each image
                
                out = StringIO()
                call_command('collectstatic_optimize', stdout=out)
            
        # Verify collectstatic was called
        mock_call_command.assert_called_with('collectstatic', interactive=False, verbosity=0)
        
        # Verify images were processed (Image.open called for each file)
        self.assertEqual(mock_image_class.open.call_count, 2)  # PNG and JPG
        
        output = out.getvalue()
        self.assertIn('Static files collected and images optimized successfully', output)
        
    @patch('pages.management.commands.collectstatic_optimize.Image')
    def test_collectstatic_optimize_handles_errors(self, mock_image_class):
        """Test that command handles image optimization errors."""
        mock_image_class.open.side_effect = Exception('Image error')
        
        with patch('pages.management.commands.collectstatic_optimize.call_command'):
            with patch('pages.management.commands.collectstatic_optimize.os.walk') as mock_walk:
                mock_walk.return_value = [('/static', [], ['test.png'])]
                
                err = StringIO()
                call_command('collectstatic_optimize', stderr=err)
                
                error_output = err.getvalue()
                self.assertIn('Error optimizing', error_output)


class OptimizeJsCommandTest(TestCase):
    """Test the optimize_js management command."""
    
    @patch('pages.management.commands.optimize_js.subprocess.run')
    @patch('pages.management.commands.optimize_js.os.path.exists')
    @patch('pages.management.commands.optimize_js.os.path.getsize')
    def test_optimize_js_success(self, mock_getsize, mock_exists, mock_run):
        """Test successful JS optimization."""
        mock_run.return_value = MagicMock(returncode=0)
        mock_exists.return_value = True
        mock_getsize.return_value = 1024  # Return consistent size for all calls
        
        out = StringIO()
        call_command('optimize_js', stdout=out)
        
        # Verify npm commands were called
        self.assertEqual(mock_run.call_count, 2)
        
        output = out.getvalue()
        self.assertIn('JavaScript optimization complete', output)
        
    @patch('pages.management.commands.optimize_js.subprocess.run')
    def test_optimize_js_minify_failure(self, mock_run):
        """Test JS optimization when minification fails."""
        mock_run.return_value = MagicMock(returncode=1, stderr='Minification failed')
        
        out = StringIO()
        call_command('optimize_js', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Minification failed', output)
        
    def test_optimize_js_skip_options(self):
        """Test skip options for JS optimization."""
        with patch('pages.management.commands.optimize_js.subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            
            # Test skip minify
            call_command('optimize_js', skip_minify=True)
            self.assertEqual(mock_run.call_count, 1)  # Only compression
            
            mock_run.reset_mock()
            
            # Test skip compress
            call_command('optimize_js', skip_compress=True)
            self.assertEqual(mock_run.call_count, 1)  # Only minification


class BuildCssCommandTest(TestCase):
    """Test the build_css management command."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.css_dir = os.path.join(self.temp_dir, 'static', 'css')
        os.makedirs(self.css_dir)
        
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        
    @patch('pages.management.commands.build_css.settings')
    @patch('pages.management.commands.build_css.subprocess.run')
    @patch('pages.management.commands.build_css.os.path.getsize')
    def test_build_css_production_mode(self, mock_getsize, mock_run, mock_settings):
        """Test CSS build in production mode."""
        mock_settings.BASE_DIR = self.temp_dir
        mock_run.return_value = MagicMock(returncode=0)
        mock_getsize.return_value = 1024  # 1KB
        
        # Create test CSS files
        for filename in ['base.css', 'theme-toggle.css']:
            Path(os.path.join(self.css_dir, filename)).write_text('body { color: red; }')
        
        # Create the expected output files that PostCSS would create
        processed_css = Path(self.css_dir) / 'combined.processed.css'
        processed_css.write_text('body{color:red}')
        
        # Create the expected minified file
        minified_css = Path(self.css_dir) / 'combined.min.css'
        minified_css.write_text('body{color:red}')
            
        out = StringIO()
        call_command('build_css', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Running in production mode', output)
        self.assertIn('CSS optimization complete', output)
        
    @patch('pages.management.commands.build_css.settings')
    @patch('pages.management.commands.build_css.subprocess.run')
    @patch('pages.management.commands.build_css.os.path.getsize')
    def test_build_css_dev_mode(self, mock_getsize, mock_run, mock_settings):
        """Test CSS build in development mode."""
        mock_settings.BASE_DIR = self.temp_dir
        mock_run.return_value = MagicMock(returncode=0)
        mock_getsize.return_value = 512  # 0.5KB
        
        # Create test CSS files
        Path(os.path.join(self.css_dir, 'base.css')).write_text('body { }')
        
        # Create the expected output files that PostCSS would create
        processed_css = Path(self.css_dir) / 'combined.processed.css'
        processed_css.write_text('body{}')
        
        # Create the expected minified file
        minified_css = Path(self.css_dir) / 'combined.min.css'
        minified_css.write_text('body{}')
        
        out = StringIO()
        call_command('build_css', dev=True, stdout=out)
        
        output = out.getvalue()
        self.assertIn('Running in development mode', output)
        
    @patch('pages.management.commands.build_css.settings')
    @patch('pages.management.commands.build_css.os.path.getsize')
    def test_build_css_optimization(self, mock_getsize, mock_settings):
        """Test CSS optimization logic."""
        mock_settings.BASE_DIR = self.temp_dir
        mock_getsize.return_value = 512  # 0.5KB
        
        # Create test CSS with optimizable content
        css_content = """
        body {
            margin-top: 10px;
            margin-right: 10px;
            margin-bottom: 10px;
            margin-left: 10px;
            color: #ffffff;
        }
        """
        
        css_file = os.path.join(self.css_dir, 'base.css')
        Path(css_file).write_text(css_content)
        
        # Create the expected output files that PostCSS would create
        processed_css = Path(self.css_dir) / 'combined.processed.css'
        processed_css.write_text('body{margin:10px;color:#fff}')
        
        # Create the expected minified file
        minified_css = Path(self.css_dir) / 'combined.min.css'
        minified_css.write_text('body{margin:10px;color:#fff}')
        
        with patch('pages.management.commands.build_css.subprocess.run'):
            out = StringIO()
            call_command('build_css', dev=True, stdout=out)
            
            # Check that file was optimized
            optimized_content = Path(css_file).read_text()
            # Should have consolidated margin
            self.assertIn('margin:', optimized_content)
            # Should have shortened color
            self.assertIn('#fff', optimized_content.lower())
            
    @patch('pages.management.commands.build_css.settings')
    @patch('pages.management.commands.build_css.subprocess.run')
    def test_build_css_postcss_failure(self, mock_run, mock_settings):
        """Test handling of PostCSS failure."""
        import subprocess
        mock_settings.BASE_DIR = self.temp_dir
        mock_run.side_effect = subprocess.CalledProcessError(1, 'postcss', output='', stderr='PostCSS failed')
        
        Path(os.path.join(self.css_dir, 'base.css')).write_text('body { }')
        
        out = StringIO()
        # Should not raise exception
        call_command('build_css', dev=True, stdout=out)
        
        output = out.getvalue()
        self.assertIn('PostCSS failed', output)
        
    @patch('pages.management.commands.build_css.settings')
    @patch('pages.management.commands.build_css.os.path.getsize')
    def test_build_css_creates_versioned_file(self, mock_getsize, mock_settings):
        """Test that build creates versioned CSS file."""
        mock_settings.BASE_DIR = self.temp_dir
        mock_getsize.return_value = 512  # 0.5KB
        
        Path(os.path.join(self.css_dir, 'base.css')).write_text('body { }')
        
        # Create the expected output files that PostCSS would create
        processed_css = Path(self.css_dir) / 'combined.processed.css'
        processed_css.write_text('body{}')
        
        # Create the expected minified file
        minified_css = Path(self.css_dir) / 'combined.min.css'
        minified_css.write_text('body{}')
        
        with patch('pages.management.commands.build_css.subprocess.run'):
            call_command('build_css')
            
            # Check for versioned file
            versioned_files = list(Path(self.css_dir).glob('combined.min.*.css'))
            self.assertTrue(len(versioned_files) > 0)
            
    @patch('pages.management.commands.build_css.settings')
    @patch('pages.management.commands.build_css.os.path.getsize')
    def test_build_css_compression(self, mock_getsize, mock_settings):
        """Test CSS compression (gzip/brotli)."""
        mock_settings.BASE_DIR = self.temp_dir
        mock_getsize.return_value = 1024  # 1KB
        
        Path(os.path.join(self.css_dir, 'base.css')).write_text('body { color: red; }')
        
        # Create the expected output files that PostCSS would create
        processed_css = Path(self.css_dir) / 'combined.processed.css'
        processed_css.write_text('body{color:red}')
        
        # Create the expected minified file
        minified_css = Path(self.css_dir) / 'combined.min.css'
        minified_css.write_text('body{color:red}')
        
        with patch('pages.management.commands.build_css.subprocess.run'):
            call_command('build_css')
            
            # Check for compressed versions
            css_files = list(Path(self.css_dir).glob('combined.min.css*'))
            gz_files = [f for f in css_files if f.suffix == '.gz']
            
            self.assertTrue(len(gz_files) > 0)

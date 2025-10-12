from django.core.management.base import BaseCommand
import os
import subprocess
from django.conf import settings
import hashlib
from pathlib import Path
import concurrent.futures
import gzip
import time
import re
from functools import wraps
from collections import defaultdict, OrderedDict


def timer(func):
    """Decorator to time function execution"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(f"  ⏱️  {func.__name__}: {end - start:.2f}s")
        return result
    return wrapper


class Command(BaseCommand):
    help = 'Build and optimize CSS with advanced minification techniques'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dev',
            action='store_true',
            help='Development mode: skip purging, keep source maps and artifacts'
        )

    def handle(self, *args, **options):
        # Set up options based on dev mode
        if options.get('dev'):
            self.options = {
                'dev': True,
                'skip_purge': True,
                'source_maps': True,
                'keep_artifacts': True,
                'parallel': True,
                'aggressive': False
            }
            self.stdout.write(self.style.WARNING('🔧 Running in development mode'))
        else:
            self.options = {
                'dev': False,
                'skip_purge': False,
                'source_maps': False,
                'keep_artifacts': False,
                'parallel': True,
                'aggressive': True
            }
            self.stdout.write(self.style.SUCCESS('🚀 Running in production mode'))
        
        # Always run both optimize and build
        self.stdout.write(self.style.SUCCESS('\n🎯 Phase 1: Optimizing Individual CSS Files...\n'))
        self._optimize_individual_files()
        
        self.stdout.write(self.style.SUCCESS('\n🚀 Phase 2: Building Combined CSS Pipeline...\n'))
        self._build_combined_css()
        
        # Always clean up in production mode
        if not self.options.get('dev'):
            self._cleanup_backup_files()
            self._cleanup_old_versions()
        
        self.stdout.write(self.style.SUCCESS('\n✅ CSS optimization complete!\n'))
    
    def _optimize_individual_files(self):
        """Optimize individual CSS files"""
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'css')
        css_files = ['category-colors.css', 'base.css', 'theme-toggle.css', 'books.css', 'knowledge_graph.css', 'photos.css', 'blog.css', 'autocomplete.css']
        
        if self.options.get('parallel'):
            self._parallel_optimize_files(static_dir, css_files)
        else:
            self._sequential_optimize_files(static_dir, css_files)
        
        self._print_optimization_summary(static_dir, css_files)
    
    def _build_combined_css(self):
        """Build combined and minified CSS"""
        base_dir = settings.BASE_DIR
        static_dir = os.path.join(base_dir, 'static', 'css')
        
        css_files = ['category-colors.css', 'base.css', 'theme-toggle.css', 'books.css', 'knowledge_graph.css', 'photos.css', 'blog.css', 'autocomplete.css']
        
        # Step 1: Combine CSS files
        combined_path = self._combine_css_files(static_dir, css_files)
        original_size = os.path.getsize(combined_path)  # Store original size before cleanup
        
        # Step 2: Run PostCSS with advanced configuration
        processed_path = self._run_postcss(base_dir, combined_path, static_dir)
        
        # Step 3: Purge unused CSS
        if not self.options.get('skip_purge'):
            processed_path = self._purge_css(base_dir, processed_path, static_dir)
        
        # Step 4: Extract critical CSS
        if self.options.get('extract_critical'):
            self._extract_critical_css(processed_path, static_dir)
        
        # Step 5: Final minification and versioning
        final_path = self._final_minification(processed_path, static_dir)
        
        # Step 6: Create compressed versions
        self._create_compressed_versions(final_path)
        
        # Step 7: Clean up intermediate files
        self._cleanup_temp_files(static_dir, final_path)
        
        # Final summary
        self._print_build_summary(original_size, final_path)
    
    @timer
    def _parallel_optimize_files(self, static_dir, css_files):
        """Optimize CSS files in parallel"""
        self.stdout.write('⚡ Optimizing CSS files in parallel...')
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for css_file in css_files:
                file_path = os.path.join(static_dir, css_file)
                if os.path.exists(file_path):
                    future = executor.submit(self._optimize_single_file, file_path)
                    futures.append((css_file, future))
            
            for css_file, future in futures:
                try:
                    original_size, new_size = future.result()
                    reduction = ((original_size - new_size) / original_size) * 100 if original_size > 0 else 0
                    self.stdout.write(f'  ✓ {css_file}: {reduction:.1f}% reduction')
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'  ⚠ Failed to optimize {css_file}: {e}'))
    
    def _sequential_optimize_files(self, static_dir, css_files):
        """Fallback sequential optimization"""
        self.stdout.write('📝 Optimizing CSS files sequentially...')
        
        for css_file in css_files:
            file_path = os.path.join(static_dir, css_file)
            if os.path.exists(file_path):
                original_size, new_size = self._optimize_single_file(file_path)
                reduction = ((original_size - new_size) / original_size) * 100 if original_size > 0 else 0
                self.stdout.write(f'  ✓ {css_file}: {reduction:.1f}% reduction')
    
    def _optimize_single_file(self, file_path):
        """Apply advanced optimizations to a single CSS file"""
        with open(file_path, 'r') as f:
            content = f.read()
        
        original_size = len(content)
        
        # Parse CSS into rules
        rules = self._parse_css(content)
        
        # Apply optimizations
        rules = self._merge_duplicate_selectors(rules)
        rules = self._consolidate_media_queries(rules)
        rules = self._optimize_selectors(rules)
        rules = self._optimize_properties(rules)
        
        if self.options.get('aggressive'):
            rules = self._aggressive_optimizations(rules)
        
        # Rebuild CSS
        optimized_content = self._rebuild_css(rules)
        
        # Additional text-level optimizations
        optimized_content = self._text_level_optimizations(optimized_content)
        
        # Save optimized version (always create backup for safety)
        backup_path = file_path + '.backup'
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy2(file_path, backup_path)
        
        with open(file_path, 'w') as f:
            f.write(optimized_content)
        
        new_size = len(optimized_content)
        
        return original_size, new_size
    
    @timer
    def _combine_css_files(self, static_dir, css_files):
        """Combine CSS files intelligently"""
        self.stdout.write('🔗 Combining CSS files...')
        
        combined_path = os.path.join(static_dir, 'combined.css')
        seen_imports = set()
        
        with open(combined_path, 'w') as combined_file:
            # Add source map comment if requested
            if self.options.get('source_maps'):
                combined_file.write('/*# sourceMappingURL=combined.css.map */\n')
            
            for css_file in css_files:
                file_path = os.path.join(static_dir, css_file)
                
                if os.path.exists(file_path):
                    with open(file_path, 'r') as f:
                        content = f.read()
                        
                        # Replace relative font URLs with S3 URLs when in production mode
                        if not self.options.get('dev'):
                            content = self._replace_font_urls(content)
                        
                        # Remove duplicate @import statements
                        lines = []
                        for line in content.split('\n'):
                            if line.strip().startswith('@import'):
                                import_stmt = line.strip()
                                if import_stmt not in seen_imports:
                                    seen_imports.add(import_stmt)
                                    lines.append(line)
                            else:
                                lines.append(line)
                        
                        combined_file.write('\n'.join(lines))
                        combined_file.write('\n\n')
        
        size = os.path.getsize(combined_path) / 1024
        self.stdout.write(f'  📊 Combined CSS: {size:.1f}KB')
        return combined_path
    
    def _replace_font_urls(self, content):
        """Replace relative font URLs with absolute S3 URLs"""
        # Import settings to get S3 configuration
        from django.conf import settings
        
        # Get S3 URL base
        if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN'):
            s3_base = f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/public/static'
            
            # Replace various font URL patterns
            content = re.sub(
                r'url\(["\']?/static/fonts/([^"\']+)["\']?\)',
                rf'url("{s3_base}/fonts/\1")',
                content
            )
            content = re.sub(
                r'url\(["\']?static/fonts/([^"\']+)["\']?\)',
                rf'url("{s3_base}/fonts/\1")',
                content
            )
            content = re.sub(
                r'url\(["\']?fonts/([^"\']+)["\']?\)',
                rf'url("{s3_base}/fonts/\1")',
                content
            )
            
            self.stdout.write(f'  ✓ Replaced font URLs with S3 URLs')
        
        return content
    
    @timer
    def _run_postcss(self, base_dir, input_path, static_dir):
        """Run PostCSS with advanced configuration"""
        self.stdout.write('🎨 Running PostCSS with advanced minification...')
        
        output_path = os.path.join(static_dir, 'combined.processed.css')
        
        try:
            cmd = ['npx', 'postcss', input_path, '-o', output_path]
            
            if self.options.get('source_maps'):
                cmd.extend(['--map', 'true'])
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=base_dir
            )
            
            size = os.path.getsize(output_path) / 1024
            self.stdout.write(self.style.SUCCESS(f'  ✓ PostCSS complete: {size:.1f}KB'))
            return output_path
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ PostCSS failed: {e}'))
            return input_path
    
    @timer
    def _purge_css(self, base_dir, input_path, static_dir):
        """Purge unused CSS with PurgeCSS"""
        self.stdout.write('🧹 Purging unused CSS...')
        
        output_path = os.path.join(static_dir, 'combined.purged.css')
        
        try:
            cmd = ['npx', 'purgecss', 
                   '--css', input_path,
                   '--config', 'purgecss.config.js',
                   '--output', output_path]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=base_dir
            )
            
            original_size = os.path.getsize(input_path) / 1024
            purged_size = os.path.getsize(output_path) / 1024
            reduction = ((original_size - purged_size) / original_size) * 100
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'  ✓ Purged: {purged_size:.1f}KB (removed {reduction:.1f}%)'
                )
            )
            return output_path
            
        except subprocess.CalledProcessError as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ PurgeCSS failed: {e}'))
            return input_path
    
    @timer
    def _extract_critical_css(self, input_path, static_dir):
        """Extract critical CSS using the critical package"""
        self.stdout.write('⚡ Extracting critical CSS...')
        
        critical_path = os.path.join(static_dir, 'critical.css')
        
        try:
            # Create a simple critical CSS extraction script
            extract_script = """
const critical = require('critical');
const fs = require('fs');

critical.generate({
    inline: false,
    base: '.',
    src: 'templates/index.html',
    css: ['%s'],
    width: 1300,
    height: 900,
    extract: false,
    penthouse: {
        blockJSRequests: false
    }
}).then(({css}) => {
    fs.writeFileSync('%s', css);
    console.log('Critical CSS extracted');
}).catch(err => {
    console.error(err);
    process.exit(1);
});
""" % (input_path, critical_path)
            
            script_path = os.path.join(static_dir, 'extract_critical.js')
            with open(script_path, 'w') as f:
                f.write(extract_script)
            
            result = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=settings.BASE_DIR
            )
            
            if os.path.exists(critical_path):
                size = os.path.getsize(critical_path) / 1024
                self.stdout.write(self.style.SUCCESS(f'  ✓ Critical CSS: {size:.1f}KB'))
            
            # Clean up script
            os.remove(script_path)
            
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ⚠ Critical extraction failed: {e}'))
            self._fallback_critical_extraction(input_path, critical_path)
    
    def _fallback_critical_extraction(self, input_path, output_path):
        """Fallback critical CSS extraction"""
        critical_selectors = [
            'html', 'body', ':root',
            'header', 'nav', 'main',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            '.container', '.wrapper', '.content',
            '@font-face', '@keyframes'
        ]
        
        with open(input_path, 'r') as f:
            content = f.read()
        
        critical_css = []
        for selector in critical_selectors:
            pattern = rf'{re.escape(selector)}\s*\{{[^}}]*\}}'
            matches = re.findall(pattern, content, re.IGNORECASE)
            critical_css.extend(matches)
        
        with open(output_path, 'w') as f:
            f.write('\n'.join(critical_css))
    
    @timer
    def _final_minification(self, input_path, static_dir):
        """Final aggressive minification"""
        self.stdout.write('💎 Final minification...')
        
        output_path = os.path.join(static_dir, 'combined.min.css')
        
        try:
            cmd = ['npx', 'cssnano', input_path, output_path,
                   '--no-map' if not self.options.get('source_maps') else '--map']
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=settings.BASE_DIR
            )
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Fallback to simple minification
            with open(input_path, 'r') as f:
                content = f.read()
            
            # Aggressive minification
            content = re.sub(r'\s+', ' ', content)
            content = re.sub(r':\s+', ':', content)
            content = re.sub(r';\s+', ';', content)
            content = re.sub(r'\{\s+', '{', content)
            content = re.sub(r'\}\s+', '}', content)
            content = re.sub(r';\}', '}', content)
            
            with open(output_path, 'w') as f:
                f.write(content)
        
        # Create versioned file
        with open(output_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        
        versioned_path = os.path.join(static_dir, f'combined.min.{file_hash}.css')
        import shutil
        shutil.copy2(output_path, versioned_path)
        
        size = os.path.getsize(output_path) / 1024
        self.stdout.write(self.style.SUCCESS(f'  ✓ Final CSS: {size:.1f}KB'))
        self.stdout.write(f'  📌 Version: combined.min.{file_hash}.css')
        
        return output_path
    
    @timer
    def _create_compressed_versions(self, file_path):
        """Create gzip and brotli compressed versions"""
        self.stdout.write('🗜️  Creating compressed versions...')
        
        # Gzip compression
        with open(file_path, 'rb') as f_in:
            with gzip.open(file_path + '.gz', 'wb', compresslevel=9) as f_out:
                f_out.write(f_in.read())
        
        gz_size = os.path.getsize(file_path + '.gz') / 1024
        self.stdout.write(f'  ✓ Gzip: {gz_size:.1f}KB')
        
        # Brotli compression (if available)
        try:
            import brotli
            with open(file_path, 'rb') as f:
                compressed = brotli.compress(f.read(), quality=11)
            with open(file_path + '.br', 'wb') as f:
                f.write(compressed)
            br_size = os.path.getsize(file_path + '.br') / 1024
            self.stdout.write(f'  ✓ Brotli: {br_size:.1f}KB')
        except ImportError:
            self.stdout.write('  ℹ️  Brotli not available')
    
    def _cleanup_temp_files(self, static_dir, keep_file):
        """Clean up intermediate files"""
        self.stdout.write('🧹 Cleaning up temporary files...')
        
        if self.options.get('keep_artifacts'):
            self.stdout.write('  ℹ️  Keeping artifacts (--keep-artifacts specified)')
            return
        
        temp_patterns = [
            'combined.css',
            'combined.processed.css',
            'combined.purged.css',
            'extract_critical.js',
            '*.opt'  # Optimization temp files
        ]
        
        for pattern in temp_patterns:
            for file_path in Path(static_dir).glob(pattern):
                if str(file_path) != keep_file:
                    file_path.unlink()
        
        self.stdout.write('  ✓ Cleanup complete')
    
    # CSS Parsing and Optimization Methods
    
    def _parse_css(self, content):
        """
        Parse CSS content into structured rules.
        
        Breaks down CSS into:
        - @import statements
        - @font-face rules
        - @keyframes animations
        - @media queries
        - Regular CSS rules
        
        Returns list of structured rule dictionaries.
        """
        rules = []
        
        # Remove comments first
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        
        # Parse @import statements
        imports = re.findall(r'@import[^;]+;', content)
        for imp in imports:
            rules.append({'type': 'import', 'content': imp})
            content = content.replace(imp, '')
        
        # Parse @font-face rules
        font_faces = re.findall(r'@font-face\s*\{[^}]*\}', content, re.DOTALL)
        for ff in font_faces:
            rules.append({'type': 'font-face', 'content': ff})
            content = content.replace(ff, '')
        
        # Parse @keyframes
        keyframes = re.findall(r'@(?:-webkit-|-moz-|-o-)?keyframes\s+[\w-]+\s*\{(?:[^{}]*\{[^}]*\})*[^}]*\}', content, re.DOTALL)
        for kf in keyframes:
            rules.append({'type': 'keyframes', 'content': kf})
            content = content.replace(kf, '')
        
        # Parse media queries
        media_queries = re.findall(r'@media[^{]+\{(?:[^{}]*\{[^}]*\})*[^}]*\}', content, re.DOTALL)
        for mq in media_queries:
            media_match = re.match(r'@media([^{]+)\{(.*)\}', mq, re.DOTALL)
            if media_match:
                condition = media_match.group(1).strip()
                inner_content = media_match.group(2)
                inner_rules = self._parse_regular_rules(inner_content)
                rules.append({
                    'type': 'media',
                    'condition': condition,
                    'rules': inner_rules
                })
            content = content.replace(mq, '')
        
        # Parse regular rules
        regular_rules = self._parse_regular_rules(content)
        rules.extend(regular_rules)
        
        return rules
    
    def _parse_regular_rules(self, content):
        """Parse regular CSS rules"""
        rules = []
        
        pattern = r'([^{}]+)\{([^}]*)\}'
        matches = re.findall(pattern, content)
        
        for selector, properties in matches:
            selector = selector.strip()
            if selector:
                props = self._parse_properties(properties)
                if props:
                    rules.append({
                        'type': 'rule',
                        'selector': selector,
                        'properties': props
                    })
        
        return rules
    
    def _parse_properties(self, properties_str):
        """Parse CSS properties into a dictionary"""
        props = OrderedDict()
        
        for prop in properties_str.split(';'):
            prop = prop.strip()
            if prop and ':' in prop:
                key, value = prop.split(':', 1)
                key = key.strip()
                value = value.strip()
                if key and value:
                    props[key] = value
        
        return props
    
    def _merge_duplicate_selectors(self, rules):
        """Merge rules with identical selectors"""
        merged = []
        selector_map = defaultdict(list)
        
        for rule in rules:
            if rule['type'] == 'rule':
                selector_map[rule['selector']].append(rule['properties'])
            elif rule['type'] == 'media':
                rule['rules'] = self._merge_duplicate_selectors(rule['rules'])
                merged.append(rule)
            else:
                merged.append(rule)
        
        for selector, props_list in selector_map.items():
            merged_props = OrderedDict()
            for props in props_list:
                merged_props.update(props)
            merged.append({
                'type': 'rule',
                'selector': selector,
                'properties': merged_props
            })
        
        return merged
    
    def _consolidate_media_queries(self, rules):
        """Consolidate rules with the same media query conditions"""
        consolidated = []
        media_map = defaultdict(list)
        
        for rule in rules:
            if rule['type'] == 'media':
                media_map[rule['condition']].append(rule['rules'])
            else:
                consolidated.append(rule)
        
        for condition, rules_lists in media_map.items():
            merged_rules = []
            for rules_list in rules_lists:
                merged_rules.extend(rules_list)
            
            merged_rules = self._merge_duplicate_selectors(merged_rules)
            
            consolidated.append({
                'type': 'media',
                'condition': condition,
                'rules': merged_rules
            })
        
        return consolidated
    
    def _optimize_selectors(self, rules):
        """Optimize CSS selectors"""
        optimized = []
        
        for rule in rules:
            if rule['type'] == 'rule':
                selector = re.sub(r'\s+', ' ', rule['selector'])
                selector = re.sub(r'\s*([>+~,])\s*', r'\1', selector)
                rule['selector'] = selector
                optimized.append(rule)
            elif rule['type'] == 'media':
                rule['rules'] = self._optimize_selectors(rule['rules'])
                optimized.append(rule)
            else:
                optimized.append(rule)
        
        return optimized
    
    def _optimize_properties(self, rules):
        """Optimize CSS properties"""
        for rule in rules:
            if rule['type'] == 'rule':
                props = rule['properties']
                
                props = self._consolidate_shorthand(props, 'margin')
                props = self._consolidate_shorthand(props, 'padding')
                props = self._consolidate_shorthand(props, 'border')
                
                for key in props:
                    props[key] = self._optimize_color(props[key])
                    props[key] = self._optimize_units(props[key])
                
                rule['properties'] = props
                
            elif rule['type'] == 'media':
                rule['rules'] = self._optimize_properties(rule['rules'])
        
        return rules
    
    def _consolidate_shorthand(self, props, prefix):
        """
        Consolidate individual properties into shorthand notation.
        
        Converts margin-top, margin-right, margin-bottom, margin-left
        into a single margin property (same for padding, border).
        
        Optimizes based on value patterns:
        - All same: "10px"
        - Vertical/horizontal same: "10px 20px"
        - Bottom different: "10px 20px 30px"  
        - All different: "10px 20px 30px 40px"
        """
        sides = ['top', 'right', 'bottom', 'left']
        individual_props = [f'{prefix}-{side}' for side in sides]
        
        values = []
        for prop in individual_props:
            if prop in props:
                values.append(props[prop])
            else:
                return props
        
        for prop in individual_props:
            del props[prop]
        
        if len(set(values)) == 1:
            props[prefix] = values[0]
        elif values[0] == values[2] and values[1] == values[3]:
            props[prefix] = f'{values[0]} {values[1]}'
        elif values[1] == values[3]:
            props[prefix] = f'{values[0]} {values[1]} {values[2]}'
        else:
            props[prefix] = ' '.join(values)
        
        return props
    
    def _optimize_color(self, value):
        """Optimize color values"""
        # RGB to hex
        rgb_match = re.match(r'rgb\((\d+),\s*(\d+),\s*(\d+)\)', value)
        if rgb_match:
            r, g, b = map(int, rgb_match.groups())
            if r == 255 and g == 255 and b == 255:
                return '#fff'
            elif r == 0 and g == 0 and b == 0:
                return '#000'
            else:
                hex_color = f'#{r:02x}{g:02x}{b:02x}'
                if hex_color[1] == hex_color[2] and hex_color[3] == hex_color[4] and hex_color[5] == hex_color[6]:
                    return f'#{hex_color[1]}{hex_color[3]}{hex_color[5]}'
                return hex_color
        
        # Shorten hex colors
        hex_match = re.match(r'#([0-9a-fA-F]{6})', value)
        if hex_match:
            hex_val = hex_match.group(1).lower()
            if hex_val[0] == hex_val[1] and hex_val[2] == hex_val[3] and hex_val[4] == hex_val[5]:
                return f'#{hex_val[0]}{hex_val[2]}{hex_val[4]}'
        
        if 'rgba(0,0,0,0)' in value or 'rgba(0, 0, 0, 0)' in value:
            return 'transparent'
        
        return value
    
    def _optimize_units(self, value):
        """Optimize units in values"""
        value = re.sub(r'\b0(px|em|rem|%|vh|vw|deg|s|ms)\b', '0', value)
        value = re.sub(r'\b0+(\.\d+)', r'\1', value)
        value = re.sub(r'(\.\d*?)0+\b', r'\1', value)
        value = re.sub(r'\.0+\b', '', value)
        
        return value
    
    def _aggressive_optimizations(self, rules):
        """Apply aggressive optimizations"""
        for rule in rules:
            if rule['type'] == 'rule':
                props = rule['properties']
                
                keys_to_remove = []
                for key in props:
                    if key.startswith('-ms-') or key.startswith('-o-'):
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del props[key]
                
                if 'font-weight' in props:
                    weight = props['font-weight']
                    if weight in ['600', '700', '800', '900']:
                        props['font-weight'] = 'bold'
                    elif weight in ['100', '200', '300']:
                        props['font-weight'] = '300'
                    elif weight in ['400', '500']:
                        props['font-weight'] = 'normal'
                
                rule['properties'] = props
                
            elif rule['type'] == 'media':
                rule['rules'] = self._aggressive_optimizations(rule['rules'])
        
        return rules
    
    def _rebuild_css(self, rules):
        """Rebuild CSS from parsed rules"""
        output = []
        
        for rule in rules:
            if rule['type'] == 'import':
                output.append(rule['content'])
            elif rule['type'] == 'font-face':
                output.append(rule['content'])
            elif rule['type'] == 'keyframes':
                output.append(rule['content'])
            elif rule['type'] == 'rule':
                if rule['properties']:
                    props_str = ';'.join([f'{k}:{v}' for k, v in rule['properties'].items()])
                    output.append(f"{rule['selector']}{{{props_str}}}")
            elif rule['type'] == 'media':
                inner_css = self._rebuild_css(rule['rules'])
                if inner_css:
                    output.append(f"@media {rule['condition']}{{{inner_css}}}")
        
        return ''.join(output)
    
    def _text_level_optimizations(self, content):
        """Apply final text-level optimizations"""
        content = re.sub(r'\s+', ' ', content)
        content = re.sub(r'\s*([>+~,{}:;])\s*', r'\1', content)
        content = re.sub(r';\}', '}', content)
        content = re.sub(r'[^{}]+\{\}', '', content)
        
        if not self.options.get('aggressive'):
            content = re.sub(r'\}', '}\n', content)
            content = re.sub(r'\n+', '\n', content)
        
        return content.strip()
    
    def _print_optimization_summary(self, static_dir, css_files):
        """Print optimization summary for individual files"""
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 Individual File Optimization Summary:'))
        self.stdout.write('='*60)
        
        total_original = 0
        total_new = 0
        
        for css_file in css_files:
            file_path = os.path.join(static_dir, css_file)
            backup_path = file_path + '.backup'
            
            if os.path.exists(file_path):
                if os.path.exists(backup_path):
                    original_size = os.path.getsize(backup_path)
                else:
                    original_size = os.path.getsize(file_path)
                
                new_size = os.path.getsize(file_path)
                total_original += original_size
                total_new += new_size
                
                if original_size > 0:
                    reduction = ((original_size - new_size) / original_size) * 100
                    self.stdout.write(
                        f'  {css_file:20s}: {original_size:>6d}B → {new_size:>6d}B '
                        f'(-{reduction:>5.1f}%)'
                    )
        
        if total_original > 0:
            total_reduction = ((total_original - total_new) / total_original) * 100
            self.stdout.write('-'*60)
            self.stdout.write(
                f'  {"TOTAL":20s}: {total_original:>6d}B → {total_new:>6d}B '
                f'(-{total_reduction:>5.1f}%)'
            )
        
        self.stdout.write('='*60)
    
    def _cleanup_backup_files(self):
        """Clean up backup files created during optimization"""
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'css')
        
        removed_count = 0
        for backup_path in Path(static_dir).glob('*.css.backup'):
            backup_path.unlink()
            removed_count += 1
        
        if removed_count > 0:
            self.stdout.write(f'🧹 Removed {removed_count} backup files')
    
    def _cleanup_old_versions(self):
        """Clean up old versioned CSS files, keeping only the latest"""
        static_dir = os.path.join(settings.BASE_DIR, 'static', 'css')
        
        # Find all versioned files
        versioned_files = []
        for file_path in Path(static_dir).glob('combined.min.*.css*'):
            # Extract the hash from the filename
            name_parts = file_path.stem.split('.')
            if len(name_parts) >= 3:  # combined.min.hash
                versioned_files.append(file_path)
        
        # Sort by modification time and keep only the latest set
        if len(versioned_files) > 0:
            # Group by base name (without extension)
            file_groups = defaultdict(list)
            for file_path in versioned_files:
                # Get base name without any extension (.css, .css.gz, .css.br)
                base_name = str(file_path).split('.css')[0] + '.css'
                file_groups[base_name].append(file_path)
            
            # Find the latest version
            latest_time = 0
            latest_base = None
            for base_name, files in file_groups.items():
                base_path = Path(base_name)
                if base_path.exists():
                    mtime = base_path.stat().st_mtime
                    if mtime > latest_time:
                        latest_time = mtime
                        latest_base = base_name
            
            # Remove all except the latest version
            removed_count = 0
            for base_name, files in file_groups.items():
                if base_name != latest_base:
                    for file_path in files:
                        file_path.unlink()
                        removed_count += 1
                    # Also remove the base file
                    base_path = Path(base_name)
                    if base_path.exists():
                        base_path.unlink()
                        removed_count += 1
            
            if removed_count > 0:
                self.stdout.write(f'🧹 Removed {removed_count} old versioned files')
    
    def _print_build_summary(self, original_size_bytes, final_path):
        """Print build summary for combined CSS"""
        original_size = original_size_bytes / 1024  # Convert bytes to KB
        
        if os.path.exists(final_path):
            final_size = os.path.getsize(final_path) / 1024
        else:
            final_size = 0
        
        if final_path.endswith('.css'):
            gz_path = final_path + '.gz'
            br_path = final_path + '.br'
            gz_size = os.path.getsize(gz_path) / 1024 if os.path.exists(gz_path) else 0
            br_size = os.path.getsize(br_path) / 1024 if os.path.exists(br_path) else 0
        else:
            gz_size = 0
            br_size = 0
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('📊 Combined CSS Build Summary:'))
        self.stdout.write('='*60)
        self.stdout.write(f'  Original size:     {original_size:>8.1f} KB')
        self.stdout.write(f'  Minified size:     {final_size:>8.1f} KB')
        if gz_size:
            self.stdout.write(f'  Gzipped size:      {gz_size:>8.1f} KB')
        if br_size:
            self.stdout.write(f'  Brotli size:       {br_size:>8.1f} KB')
        
        if original_size > 0:
            reduction = ((original_size - final_size) / original_size) * 100
            self.stdout.write(f'  Minified reduction:{reduction:>8.1f}%')
            
            if gz_size:
                gz_reduction = ((original_size - gz_size) / original_size) * 100
                self.stdout.write(f'  With gzip:         {gz_reduction:>8.1f}%')
            
            if br_size:
                br_reduction = ((original_size - br_size) / original_size) * 100
                self.stdout.write(f'  With brotli:       {br_reduction:>8.1f}%')
                
                if gz_size and br_size:
                    br_vs_gz = ((gz_size - br_size) / gz_size) * 100
                    self.stdout.write(f'  Brotli vs gzip:    {br_vs_gz:>8.1f}% smaller')
        
        self.stdout.write('='*60)
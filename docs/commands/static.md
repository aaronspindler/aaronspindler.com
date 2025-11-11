# Static File Management Commands

Management commands for building, optimizing, and collecting static assets (CSS, JavaScript, images).

## Commands

### collectstatic_optimize

Collect static files with automatic image optimization and compression.

**Usage**:
```bash
python manage.py collectstatic_optimize
```

**What It Does**:
1. Runs standard Django collectstatic
2. Optimizes images (JPEG, PNG, WebP)
3. Creates gzip compressed versions
4. Creates brotli compressed versions (if available)
5. Uploads to S3 (if configured)

**Optimizations**:
- **JPEG**: Optimized quality, progressive encoding
- **PNG**: Lossless optimization
- **WebP**: Modern format generation
- **Compression**: Gzip and Brotli for faster serving

**Production Build**:
```bash
# Complete static file pipeline
python manage.py build_css
python manage.py optimize_js
python manage.py collectstatic_optimize
```

---

### build_css

Build and optimize CSS with PostCSS, PurgeCSS, and minification.

**Usage**:
```bash
python manage.py build_css
```

**Options**:
- `--dev`: Development mode (skip purging, keep source maps)

**Examples**:
```bash
# Production build (full optimization)
python manage.py build_css

# Development build (faster, unminified)
python manage.py build_css --dev
```

**Build Process**:
1. **Combine**: Concatenate all CSS files in load order → `combined.css`
2. **Minify**: Run PostCSS with cssnano for minification → `combined.processed.css`
3. **Purge**: Run PurgeCSS to remove unused CSS → `combined.purged.css` (production only)
4. **Output**: Create final `combined.min.css`
5. **Compress**: Generate Gzip (`.gz`) and Brotli (`.br`) compressed versions
6. **Cleanup**: Remove temporary build files

**CSS Source Files**:
- Stored in `static/css/` (formatted, developer-friendly)
- Never minified in git (pre-commit hooks enforce this)
- Build output: `combined.min.css` in `static/css/` (gitignored)

**Output Files**:
- `combined.min.css`: Non-versioned file for development
- `combined.min.css.gz`: Gzip compressed version
- `combined.min.css.br`: Brotli compressed version

**Versioning**:
- Content-hashed versions automatically created by WhiteNoise during `collectstatic`
- Example: `combined.min.css` → `combined.min.263d67867382.css`
- Manifest file maps non-versioned to versioned filenames
- Cache headers set to 1 year with `immutable` directive

---

### optimize_js

Optimize and minify JavaScript files with Terser.

**Usage**:
```bash
python manage.py optimize_js
```

**Options**:
- `--skip-minify`: Skip minification
- `--skip-compress`: Skip gzip/brotli compression

**Examples**:
```bash
# Full optimization
python manage.py optimize_js

# Skip minification (debugging)
python manage.py optimize_js --skip-minify

# Skip compression
python manage.py optimize_js --skip-compress
```

**What It Does**:
1. Minifies JavaScript with Terser
2. Removes console.log statements (production)
3. Creates source maps
4. Generates gzip compressed versions
5. Generates brotli compressed versions

---

### clear_cache

Clear all cache keys from Redis.

**Usage**:
```bash
python manage.py clear_cache
```

**What It Clears**:
- Knowledge graph cache
- Blog post cache
- Page cache
- Search cache
- Template cache
- View cache

**When to Use**:
- After major content updates
- After template changes
- When debugging cache issues
- Before deployment

---



## Related Documentation

- [Architecture](../architecture.md) - Static file optimization architecture
- [Commands Index](README.md) - All management commands
- [Deployment](../deployment.md) - Production static file serving with WhiteNoise

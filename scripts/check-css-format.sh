#!/bin/bash
# Pre-commit hook to prevent committing minified source CSS files
# This ensures developer-friendly CSS stays in git

set -e

# Only check source CSS files, not generated ones
SOURCE_CSS_FILES=(
    "static/css/base.css"
    "static/css/blog.css"
    "static/css/books.css"
    "static/css/photos.css"
    "static/css/category-colors.css"
    "static/css/theme-toggle.css"
    "static/css/knowledge_graph.css"
    "static/css/autocomplete.css"
    "static/css/fast-font.css"
)

exit_code=0

for file in "${SOURCE_CSS_FILES[@]}"; do
    # Skip if file doesn't exist or is not being committed
    if [ ! -f "$file" ]; then
        continue
    fi

    # Check if file is staged for commit
    if ! git diff --cached --name-only | grep -q "^$file$"; then
        continue
    fi

    # Count lines in the file (excluding empty lines)
    line_count=$(grep -cv "^$" "$file" || echo "0")

    # If file has only 1-3 lines, it's probably minified
    if [ "$line_count" -le 3 ]; then
        echo "❌ ERROR: $file appears to be minified (only $line_count lines)"
        echo "   Source CSS files should be developer-friendly with proper formatting."
        echo "   Run 'npx prettier --write $file' to format it."
        exit_code=1
    else
        echo "✓ $file looks properly formatted ($line_count lines)"
    fi
done

if [ $exit_code -ne 0 ]; then
    echo ""
    echo "💡 TIP: Source CSS files in git should be readable and formatted."
    echo "    The build process will create optimized .opt.css versions automatically."
fi

exit $exit_code

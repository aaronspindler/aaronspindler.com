# Management Command Template

> **Use this template when adding a new management command to `docs/commands.md`**

## Template

```markdown
### command_name

[Brief 1-2 sentence description of what the command does and when to use it.]

**Usage**:
\```bash
python manage.py command_name [required_arg] [options]
\```

**Arguments**:
- `required_arg`: Description of what this argument does

**Options**:
- `--option-name VALUE`: Description (default: default_value)
- `--flag`: Description of boolean flag
- `--optional VALUE`: Optional parameter description

**Examples**:

\```bash
# Example 1: Basic usage
python manage.py command_name basic_value

# Example 2: With options
python manage.py command_name value --option-name custom_value

# Example 3: Complex scenario
python manage.py command_name value --option1 val1 --option2 val2 --flag

# Example 4: Dry run (if applicable)
python manage.py command_name value --dry-run
\```

**Output**:
\```
[Example of typical command output]
📊 Starting process...
✓ Step 1 complete
✓ Step 2 complete
✅ Finished: processed X items in Y seconds
\```

**When to run**:
- [Scenario 1]: Description of when this is needed
- [Scenario 2]: Description of another use case
- [Scenario 3]: As part of [workflow name]

**Important notes**:
- ⚠️ [Any warnings or important considerations]
- 💡 [Any helpful tips]
- 🔗 See [Feature Name](../features/feature-name.md) for more details

**Related commands**:
- `related_command_1`: How it relates
- `related_command_2`: How it relates
```

## Placement in commands.md

Add the command to the appropriate section in `docs/commands.md`:

- **Blog Management**: Blog-related commands
- **Search Management**: Search index commands
- **Cache Management**: Cache-related commands
- **Performance Monitoring**: Lighthouse and performance
- **Request Tracking**: Security and analytics
- **FeeFiFoFunds Data Management**: Asset and price data
- **Static File Optimization**: Asset build and optimization
- **[New Section]**: Create a new section if needed

## Checklist

Before adding a command to commands.md:

- [ ] Command is fully implemented and tested
- [ ] Brief description clearly states purpose
- [ ] All arguments documented with types
- [ ] All options documented with defaults
- [ ] At least 3 practical examples provided
- [ ] Example output shown
- [ ] "When to run" scenarios listed
- [ ] Important warnings or notes included
- [ ] Related commands cross-referenced
- [ ] Link to feature documentation (if applicable)

## Example: Complete Command Documentation

```markdown
### rebuild_search_index

Rebuild the full-text search index for all searchable content (blog posts, photos, albums).

**Usage**:
\```bash
python manage.py rebuild_search_index [options]
\```

**Options**:
- `--content-type TYPE`: Rebuild only specific content type (choices: blog, photos, albums)
- `--clear`: Clear existing index before rebuilding
- `--batch-size SIZE`: Number of records to process per batch (default: 100)

**Examples**:

\```bash
# Rebuild entire search index
python manage.py rebuild_search_index

# Rebuild only blog posts
python manage.py rebuild_search_index --content-type blog

# Clear and rebuild all content
python manage.py rebuild_search_index --clear

# Rebuild with custom batch size
python manage.py rebuild_search_index --batch-size 50
\```

**Output**:
\```
🔍 Rebuilding search index...
📝 Processing blog posts: 150/150 [100%]
📸 Processing photos: 5000/5000 [100%]
📂 Processing albums: 25/25 [100%]
✅ Search index rebuilt successfully!
   Total documents indexed: 5,175
   Time elapsed: 12.3 seconds
\```

**When to run**:
- After adding new blog posts
- After bulk photo uploads
- When search results seem outdated
- After modifying search configuration
- As part of deployment process

**Important notes**:
- ⚠️ Large rebuilds may take several minutes
- 💡 Use `--content-type` to rebuild incrementally
- 💡 Run during low-traffic periods for large indexes
- 🔗 See [Search System](../features/search.md) for architecture details

**Related commands**:
- `clear_cache`: Clear cached search results
```

## Tips for Writing Good Command Documentation

1. **Be Specific**: Don't just say "processes data" - say "rebuilds search index for blog posts"

2. **Show Real Examples**: Use actual values that users would use, not placeholders

3. **Include Output**: Show what success looks like so users know what to expect

4. **Document Failures**: If there are common errors, document them

5. **Performance Notes**: If command is slow, mention it and give time estimates

6. **Cross-Reference**: Always link to relevant feature documentation

7. **Workflow Context**: Explain where this fits in the bigger picture

8. **Visual Hierarchy**: Use emojis sparingly for important warnings/tips

---

**Remember**: Good command documentation helps users succeed on first try!

# Documentation Templates

This directory contains standardized templates for creating new documentation in this project. Using these templates ensures consistency and completeness across all documentation.

## Available Templates

### 1. [Feature Template](feature-template.md)

**Use for**: New feature documentation in `docs/features/`

**Includes sections for**:
- Overview and key capabilities
- Architecture and design decisions
- Data models
- Management commands
- Usage examples
- Configuration
- API endpoints
- Performance optimization
- Troubleshooting
- Related documentation

**Example**: See [docs/apps/feefifofunds/overview.md](../apps/feefifofunds/overview.md) for a complete example

### 2. [Command Template](command-template.md)

**Use for**: Adding new management commands to `docs/commands.md`

**Includes sections for**:
- Brief description
- Usage syntax
- Arguments and options
- Examples (3+)
- Expected output
- When to run
- Important notes
- Related commands

**Example**: See any command in [docs/commands.md](../commands.md)

### 3. [API Endpoint Template](api-endpoint-template.md)

**Use for**: Adding new API endpoints to `docs/api.md`

**Includes sections for**:
- HTTP method and path
- Authentication requirements
- Request parameters (URL, query, body)
- Success responses with field descriptions
- Error responses (400, 404, 500)
- Rate limiting and caching
- Example usage (cURL, Python, JavaScript)
- Related endpoints

**Example**: See any endpoint in [docs/api.md](../api.md)

## How to Use Templates

### Creating New Feature Documentation

1. **Copy the template**:
   ```bash
   cp docs/templates/feature-template.md docs/features/your-feature-name.md
   ```

2. **Replace all placeholders**:
   - `[Feature Name]` → Your feature name
   - `[Description]` → Actual descriptions
   - `[ModelName]` → Actual model names
   - Remove sections that don't apply

3. **Fill in all sections**:
   - Don't leave TODO or placeholder text
   - Provide real code examples
   - Include actual output/responses
   - Add screenshots if helpful

4. **Update documentation index**:
   - Add to `docs/README.md` feature documentation table
   - Add to root `README.md` features table
   - Update `CLAUDE.md` if it's a major feature

5. **Add cross-references**:
   - Link from related feature docs
   - Link from architecture.md if relevant
   - Link from commands.md if you added commands
   - Link from api.md if you added endpoints

6. **Review checklist**:
   - [ ] All placeholders replaced
   - [ ] All code examples tested
   - [ ] Screenshots added (if applicable)
   - [ ] Cross-references added
   - [ ] Documentation index updated
   - [ ] Spelling and grammar checked
   - [ ] Links verified

### Adding New Management Command

1. **Use the command template** from `command-template.md`

2. **Add to appropriate section** in `docs/commands.md`:
   - Blog Management
   - Search Management
   - Cache Management
   - Performance Monitoring
   - Request Tracking
   - FeeFiFoFunds Data Management
   - Static File Optimization
   - Or create new section

3. **Follow the template structure** completely

4. **Test all examples** before committing

5. **Link from feature doc** if the command is feature-specific

### Adding New API Endpoint

1. **Use the API endpoint template** from `api-endpoint-template.md`

2. **Add to appropriate section** in `docs/api.md`:
   - Blog & Knowledge Graph
   - Search
   - Photos
   - Comments
   - Performance Monitoring
   - Or create new section

3. **Follow the template structure** completely

4. **Test with cURL** and verify all responses

5. **Link from feature doc** that owns this endpoint

## Documentation Standards

All documentation should follow these standards:

### Writing Style

- **Clear and Concise**: Simple language, no unnecessary jargon
- **Active Voice**: "The command processes data" not "Data is processed"
- **Present Tense**: "This endpoint returns" not "This endpoint will return"
- **Second Person**: "You can configure" not "One can configure"

### Code Examples

- **Complete**: Include all necessary imports and setup
- **Tested**: All examples must work as written
- **Realistic**: Use actual values, not foo/bar placeholders
- **Commented**: Explain non-obvious operations

### Formatting

- **Markdown**: Use proper Markdown syntax
- **Code Blocks**: Always specify language (python, bash, json, etc.)
- **Lists**: Use bullet points for lists, numbered for sequences
- **Headers**: Use proper hierarchy (##, ###, ####)
- **Links**: Use relative paths for internal docs

### Completeness

- **No Placeholders**: No TODO or TBD in published docs
- **No Broken Links**: Verify all links work
- **Cross-References**: Link to related documentation
- **Examples**: At least 2-3 practical examples per feature

## Template Maintenance

These templates should be updated when:
- Documentation patterns evolve
- New sections become standard
- Better examples are identified
- Feedback reveals missing information

To propose changes to templates:
1. Create an issue describing the improvement
2. Update the template
3. Update this README if structure changes
4. Update at least one example doc to demonstrate

## Questions?

- Check [Documentation Guidelines](../../.cursor/rules/documentation.mdc)
- See [AI Context Guidelines](../../.cursor/rules/ai-context.mdc)
- Review existing documentation for examples
- Create a GitHub issue for clarification

---

**Remember**: Good documentation helps users succeed on the first try!

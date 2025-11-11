# [Feature Name]

> **Brief tagline** - One sentence describing the feature's purpose

## Overview

[2-3 sentences describing what this feature does and why it exists. Focus on the problem it solves and the value it provides.]

**Key Capabilities:**
- [Capability 1]: Description
- [Capability 2]: Description
- [Capability 3]: Description
- [Capability 4]: Description

## Architecture

### Overview

[Brief description of how the feature is architected. Include key components and their relationships.]

**Key Components:**
- **Component 1**: Purpose and responsibility
- **Component 2**: Purpose and responsibility
- **Component 3**: Purpose and responsibility

### Design Decisions

#### [Decision 1]

**Chosen**: [What was chosen]
**Alternative**: [What was considered but not chosen]

**Reasoning**:
- ✅ [Pro 1]
- ✅ [Pro 2]
- ✅ [Pro 3]
- ❌ [Con / Trade-off]

#### [Decision 2]

**Chosen**: [What was chosen]
**Alternative**: [What was considered but not chosen]

**Reasoning**:
- ✅ [Pro 1]
- ✅ [Pro 2]
- ❌ [Con / Trade-off]

## Data Models

### [ModelName]

[Description of the model and its purpose]

**Fields:**
- `field_name` (Type): Description
- `field_name` (Type): Description
- `field_name` (Type): Description

**Indexes:**
- Index on `field_name`
- Composite index on (`field1`, `field2`)

**Usage:**
```python
from app.models import ModelName

# Example usage
instance = ModelName.objects.filter(field=value)
```

## Management Commands

### command_name

[Brief description of what the command does]

```bash
# Basic usage
python manage.py command_name [options]

# Common examples
python manage.py command_name --option value

# Advanced example
python manage.py command_name --option1 value1 --option2 value2
```

**Options:**
- `--option-name`: Description (default: value)
- `--flag`: Description

**When to run:**
- [Scenario 1]
- [Scenario 2]

**See** [Commands Reference](../commands.md#feature-name) **for complete command documentation.**

## Usage Examples

### Basic Usage

```python
# Example 1: Most common use case
from app.models import Model

result = Model.objects.do_something()
```

### Advanced Usage

```python
# Example 2: Complex scenario
from app.models import Model

# Setup
instance = Model.objects.create(field=value)

# Operation
result = instance.process()

# Verify
assert result.status == 'completed'
```

### Integration Example

```python
# Example 3: How this feature integrates with other parts
from app.models import Model
from other_app.models import OtherModel

# Integration pattern
combined = Model.integrate_with(OtherModel.objects.first())
```

## Configuration

### Environment Variables

```bash
# Required configuration
FEATURE_API_KEY=your_api_key_here
FEATURE_ENABLED=True

# Optional configuration (with defaults)
FEATURE_TIMEOUT=30  # seconds
FEATURE_CACHE_TTL=600  # seconds
```

### Django Settings

```python
# settings.py

FEATURE_CONFIG = {
    'option1': 'value1',
    'option2': 'value2',
    'nested': {
        'sub_option': 'value',
    }
}
```

## API Endpoints

### GET /api/feature/resource/

[Description of what this endpoint does]

**Request:**
```http
GET /api/feature/resource/?param=value HTTP/1.1
```

**Query Parameters:**
- `param` (string, optional): Description

**Response:**
```json
{
    "status": "success",
    "data": {
        "field1": "value1",
        "field2": "value2"
    }
}
```

**See** [API Reference](../api.md#feature-name) **for complete API documentation.**

## Performance Optimization

### Caching Strategy

[Description of caching approach]

**Cache Keys:**
```python
cache_key = f"feature:{resource_id}:{param}"
```

**TTL**: [X] minutes

### Database Optimization

**Indexes:**
- [Index 1]: Purpose and performance impact
- [Index 2]: Purpose and performance impact

**Query Patterns:**
```python
# Optimized query
Model.objects.select_related('relation').filter(condition)
```

## Troubleshooting

### [Common Issue 1]

**Symptoms:**
- [Symptom 1]
- [Symptom 2]

**Solutions:**
1. [Solution 1]
2. [Solution 2]
3. [Solution 3]

### [Common Issue 2]

**Symptoms:**
- [Symptom 1]

**Solutions:**
1. [Solution 1]
2. [Solution 2]

## Common Workflows

### Workflow 1: [Name]

```bash
# Step 1: Setup
python manage.py command_setup

# Step 2: Process
python manage.py command_process --option value

# Step 3: Verify
python manage.py command_verify
```

### Workflow 2: [Name]

```bash
# Complete workflow with explanation
python manage.py command1  # Does X
python manage.py command2  # Does Y
```

## Future Enhancements

### Planned Features

**Phase 2:**
- [Enhancement 1]
- [Enhancement 2]

**Phase 3:**
- [Enhancement 3]
- [Enhancement 4]

### Scalability Considerations

**Current Scale:**
- [Metric 1]: Current capacity
- [Metric 2]: Current capacity

**Future Scale:**
- [Metric 1]: Target capacity
- [Metric 2]: Target capacity

**Scaling Strategy:**
1. [Strategy 1]
2. [Strategy 2]

## Related Documentation

### Core Documentation
- [Architecture](../architecture.md) - [What to reference]
- [Commands](../commands.md#feature-section) - [What to reference]
- [API Reference](../api.md#feature-section) - [What to reference]
- [Documentation Index](../README.md) - Complete documentation map

### Related Features
- [Related Feature 1](related-feature-1.md) - How it relates
- [Related Feature 2](related-feature-2.md) - How it relates

### App-Specific Documentation
- [App Development Guide](../apps/app-name/development.md) - If applicable

### External Resources
- [External Doc 1](https://example.com) - Description
- [External Doc 2](https://example.com) - Description

---

**Questions?** Check the [Documentation Index](../README.md) or create a GitHub issue.

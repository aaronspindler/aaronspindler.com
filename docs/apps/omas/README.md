# Omas Coffee App Documentation

> **German coffee cart website** - Multi-domain website with traditional German branding served via Django domain routing.

## Overview

The Omas Coffee app serves a separate website at `omas.coffee` domain from the same Django project as aaronspindler.com. It features German-themed branding, traditional coffee cart design, and independent URL routing.

**Key Features:**
- Multi-domain routing (omas.coffee separate from main site)
- German-themed design and branding
- Traditional coffee cart homepage
- Independent URL configuration
- Comprehensive brand guidelines

## Documentation

### Technical Documentation

- **[Technical Setup](technical-setup.md)** - Django implementation and deployment
  - Domain routing middleware
  - Multi-domain configuration
  - Local development setup
  - DNS configuration
  - Production deployment
  - German translations

### Brand & Design Documentation

**Note:** Brand and design documentation has been moved to `/design/omas/` to keep technical documentation separate from design assets.

**Available Design Documents:**
- Brand Foundation - Mission, values, brand personality
- Brand Standards - Logo, colors, typography
- Design Guidelines - Design philosophy and principles
- Digital Design - Website and digital asset guidelines
- Physical Design - Coffee cart and physical branding
- Design Brief - Complete project overview

**Location:** `/design/omas/`

### Related Documentation

**Core Docs:**
- [Architecture](../../architecture.md) - Multi-domain routing in Django
- [Deployment](../../deployment.md) - DNS and domain configuration

## Quick Start

### Local Development

```bash
# 1. Add domain to /etc/hosts
sudo nano /etc/hosts
# Add: 127.0.0.1 omas.coffee

# 2. Run development server
python manage.py runserver

# 3. Access sites
# Main site: http://localhost:8000
# Omas Coffee: http://omas.coffee:8000
```

**See [Technical Setup](technical-setup.md) for complete development guide.**

### Production Deployment

```bash
# DNS Configuration
omas.coffee        A     <server-ip>
www.omas.coffee    CNAME omas.coffee
```

**Django settings** already configured:
- `ALLOWED_HOSTS` includes omas.coffee domains
- `CSRF_TRUSTED_ORIGINS` includes HTTPS URLs
- Domain routing middleware configured

**See [Technical Setup](technical-setup.md#production-deployment) for complete deployment guide.**

## Architecture

### Multi-Domain Routing

The app uses `config.domain_routing.DomainRoutingMiddleware` to route requests based on hostname:

```python
# config/domain_routing.py
domain_mapping = {
    "omas.coffee": "omas.urls",
    "www.omas.coffee": "omas.urls",
}
```

**Flow:**
1. Request arrives at Django
2. Middleware checks hostname
3. Routes to `omas.urls` for omas.coffee
4. Falls back to `config.urls` for other domains

**See [Technical Setup](technical-setup.md#architecture) for complete architecture.**

## Project Structure

```
omas/
├── __init__.py
├── apps.py
├── admin.py              # Django admin (if needed)
├── models.py             # Models (if needed)
├── views.py              # Views (homepage, etc.)
├── urls.py               # URL routing for omas.coffee
├── templates/
│   └── omas/
│       ├── base.html     # Base template with German branding
│       └── home.html     # Homepage
└── static/
    ├── css/omas.css      # Coffee-themed styling
    └── images/           # Brand assets
```

## Brand Guidelines

### Color Scheme

**Primary Colors:**
- Brown coffee tones: `#6B4423`, `#3E2723`
- Warm, traditional, inviting

**Background:**
- Gradient from light to dark brown
- Evokes warmth and coffee atmosphere

**Text:**
- Dark gray (`#333`) on white
- High contrast for readability

**See [Brand Standards](brand-standards.md) for complete color palette.**

### Typography

**Heading Font:** [Specified in brand-standards.md]
**Body Font:** [Specified in brand-standards.md]

**See [Brand Standards](brand-standards.md#typography) for complete typography system.**

### Logo Usage

**See [Brand Standards](brand-standards.md#logo) for:**
- Logo variations
- Minimum sizes
- Clear space requirements
- Incorrect usage examples

## Features

The homepage showcases four key features:

1. **Premium Beans** 🌱 - Highest quality coffee beans
2. **Traditional Methods** 👵 - Traditional German coffee cart approach
3. **Expert Craft** ☕ - Expertly crafted beverages
4. **Cozy Atmosphere** 🏡 - Warm, welcoming environment

## Configuration

### Environment Variables

```bash
# Django settings
ALLOWED_HOSTS=omas.coffee,www.omas.coffee,yourdomain.com
CSRF_TRUSTED_ORIGINS=https://omas.coffee,https://www.omas.coffee
```

### Domain Mapping

Update `config/domain_routing.py` to add new domains:

```python
domain_mapping = {
    "omas.coffee": "omas.urls",
    "www.omas.coffee": "omas.urls",
    # Add new domains here
}
```

**See [Technical Setup](technical-setup.md#configuration) for complete configuration.**

## Future Enhancements

### Planned Features

**Phase 2:**
- Menu/Products page
- Location/Contact information
- German language support (i18n)

**Phase 3:**
- Blog/News section
- Gallery of coffee products
- About/Story page
- Customer testimonials

**Phase 4:**
- Online ordering integration
- Loyalty program
- Events calendar
- Newsletter signup

## Contributing

When contributing to the Omas Coffee app:

1. **Follow brand guidelines**: See brand documentation in this directory
2. **Maintain German theme**: Keep traditional coffee cart aesthetic
3. **Test multi-domain**: Verify both omas.coffee and main site work
4. **Update brand docs**: If changing visual identity or branding
5. **Document changes**: Update relevant docs in this directory

**See [Technical Setup](technical-setup.md) for development guidelines.**

## Common Tasks

### Testing Multi-Domain

```bash
# Test main site
curl http://localhost:8000

# Test Omas Coffee site (requires /etc/hosts entry)
curl http://omas.coffee:8000

# Verify domain routing
python manage.py shell
>>> from config.domain_routing import domain_mapping
>>> domain_mapping
```

### Updating Brand Assets

1. Update brand documentation in this directory
2. Update static assets in `omas/static/`
3. Update templates in `omas/templates/`
4. Review brand consistency

**See brand documentation files for guidelines.**

---

**Questions?** Check the [Documentation Index](../../README.md) or create a GitHub issue.

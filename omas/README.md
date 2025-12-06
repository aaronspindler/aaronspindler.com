# Omas Coffee Documentation

> **German coffee cart website** - Separate domain served via Django multi-domain routing.

## 📚 Documentation Has Moved

All Omas Coffee documentation has been consolidated to the main project `docs/` directory for better organization and easier maintenance.

### 🚀 Quick Links

**Technical Documentation:**
- **[Omas Coffee Feature Guide](../../docs/features/omas-coffee.md)** - Domain routing, German translations, local setup, deployment

**Brand & Design Documentation:**
- **[Brand Foundation](../../docs/apps/omas/brand-foundation.md)** - Mission, values, brand personality
- **[Brand Standards](../../docs/apps/omas/brand-standards.md)** - Logo, colors, typography guidelines
- **[Design Guidelines](../../docs/apps/omas/design-guidelines.md)** - Design principles
- **[Digital Design](../../docs/apps/omas/digital-design.md)** - Website/digital presence guidelines
- **[Physical Design](../../docs/apps/omas/physical-design.md)** - Coffee cart physical design
- **[Design Brief](../../docs/apps/omas/DESIGN_BRIEF.md)** - Complete design specification

**Core Documentation:**
- **[Architecture Overview](../../docs/architecture.md)** - Multi-domain support explanation
- **[Documentation Index](../../docs/README.md)** - Complete documentation map

## 🏃 Quick Start

```bash
# Add domain to /etc/hosts for local development
sudo nano /etc/hosts
# Add: 127.0.0.1 omas.coffee

# Run development server
python manage.py runserver

# Access sites
# Main site: http://localhost:8000
# Omas Coffee: http://omas.coffee:8000
```

See the [Omas Coffee Feature Guide](../../docs/features/omas-coffee.md) for complete setup and deployment instructions.

## 📊 Overview

The Omas Coffee website is served from the same Django project as aaronspindler.com using domain-based routing:
- **Dedicated Homepage**: Coffee-themed design with feature showcase
- **Independent URL Routing**: Separate URL configuration (`omas.urls`)
- **Domain Routing**: `DomainRoutingMiddleware` routes `omas.coffee` requests
- **German Theme**: Traditional German coffee cart branding

## 🎨 Design

### Color Scheme
- Primary: Brown coffee tones (`#6B4423`, `#3E2723`)
- Background: Gradient from light to dark brown
- Accents: Coffee brown for interactive elements

### Features
1. **Premium Beans** 🌱
2. **Traditional Methods** 👵
3. **Expert Craft** ☕
4. **Cozy Atmosphere** 🏡

See [Brand Standards](../../docs/apps/omas/brand-standards.md) for complete brand guidelines.

## 🚀 Deployment

### DNS Configuration
```
omas.coffee        A     <server-ip>
www.omas.coffee    CNAME omas.coffee
```

### Django Settings
Already configured:
- `ALLOWED_HOSTS` includes `omas.coffee` and `www.omas.coffee`
- `CSRF_TRUSTED_ORIGINS` includes `https://omas.coffee` and `https://www.omas.coffee`

See [Omas Coffee Feature Guide](../../docs/features/omas-coffee.md#production-deployment) for complete deployment instructions.

---

**Note**: This directory previously contained brand documentation files (brand-foundation.md, brand-standards.md, etc.) which have been moved to `docs/apps/omas/` for centralized access and maintenance.

# Omas Coffee Website

This Django app serves the Omas Coffee website at `omas.coffee` domain.

## Overview

The Omas Coffee website is a separate website served from the same Django project as aaronspindler.com. It uses domain-based routing middleware to serve different content based on the request hostname.

## Features

- **Dedicated Homepage**: Coffee-themed homepage with feature showcase
- **Independent URL Routing**: Separate URL configuration (`omas.urls`)
- **Custom Templates**: Coffee-themed design and branding
- **Domain Routing**: Automatically serves when accessing omas.coffee

## Architecture

### Domain Routing

The app uses `config.domain_routing.DomainRoutingMiddleware` to route requests:
- Requests to `omas.coffee` or `www.omas.coffee` → `omas.urls`
- All other domains → `config.urls` (main site)

### URL Configuration

```python
# omas/urls.py
urlpatterns = [
    path("", views.home, name="home"),
]
```

### Views

- `home`: Displays the Omas Coffee homepage with welcome message and features

### Templates

- `omas/base.html`: Base template with coffee-themed styling
- `omas/home.html`: Homepage content extending base template

## Local Development

### Setup

1. Add domain to `/etc/hosts`:
   ```bash
   sudo nano /etc/hosts
   # Add: 127.0.0.1 omas.coffee
   ```

2. Run development server:
   ```bash
   python manage.py runserver
   ```

3. Access in browser:
   - Main site: `http://localhost:8000`
   - Omas Coffee: `http://omas.coffee:8000`

### Testing

Run tests for the omas app:
```bash
python manage.py test omas
```

## Production Deployment

### DNS Configuration

Point the domain to your server:
```
omas.coffee        A     <server-ip>
www.omas.coffee    CNAME omas.coffee
```

### Django Settings

Already configured in `config/settings.py`:
- `ALLOWED_HOSTS` includes `omas.coffee` and `www.omas.coffee`
- `CSRF_TRUSTED_ORIGINS` includes `https://omas.coffee` and `https://www.omas.coffee`

### Web Server (nginx example)

```nginx
server {
    server_name omas.coffee www.omas.coffee;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # SSL configuration
    listen 443 ssl;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
}
```

## Design

### Color Scheme

- Primary: Brown coffee tones (`#6B4423`, `#3E2723`)
- Background: Gradient from light to dark brown
- Text: Dark gray (`#333`) on white background
- Accents: Coffee brown (`#6B4423`)

### Features Section

The homepage showcases four key features:
1. **Premium Beans** 🌱
2. **Traditional Methods** 👵
3. **Expert Craft** ☕
4. **Cozy Atmosphere** 🏡

## Future Enhancements

Potential additions:
- Menu/Products page
- Location/Contact information
- Blog/News section
- Online ordering integration
- Gallery of coffee products
- About/Story page

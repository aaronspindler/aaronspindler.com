# Omas Coffee Website

## Overview

Omas Coffee (omas.coffee) is a separate website served from the same Django application using multi-domain routing. It's a premium coffee cart website honoring German Kaffeezeit tradition, featuring an elegant design with rich walnut and antique gold colors, and a unique German-English translation system.

## Multi-Domain Architecture

The application uses `DomainRoutingMiddleware` to serve multiple websites from a single Django project:

```python
# config/domain_routing.py
domain_mapping = {
    "omas.coffee": "omas.urls",
    "www.omas.coffee": "omas.urls",
}
```

### Key Components

- **App**: `omas/` - Separate Django app with its own URLs, views, and templates
- **Middleware**: `DomainRoutingMiddleware` inspects request hostname and routes to appropriate URL configuration
- **Static Files**: Located in `omas/static/omas/` for CSS, JavaScript, and images
- **Templates**: Located in `omas/templates/omas/` for HTML templates

## German Translation Hover System

One of the unique features of the Omas Coffee website is the interactive German-English translation system that provides hover tooltips for German terms throughout the site.

### Features

- **Automatic Detection**: Scans page content for German terms and makes them translatable
- **Elegant Tooltips**: Beautiful styled tooltips with German flag emoji and translation arrow
- **Mobile Support**: Touch-friendly with auto-dismiss after 3 seconds
- **Visual Indicators**: Subtle dotted underline appears on hover to indicate translatable text
- **Smart Positioning**: Tooltips automatically position above or below elements based on viewport space
- **Smooth Animations**: Fade-in animations with subtle scaling effects

### Implementation

#### JavaScript (`omas/static/omas/js/german-translations.js`)

The translation system is implemented as a self-contained JavaScript module that:

1. **Translation Dictionary**: Maintains a mapping of German terms to English translations
2. **DOM Scanning**: Automatically finds German text using:
   - Elements with `data-german` attributes
   - Text nodes containing known German terms
3. **Tooltip Management**: Creates and positions tooltips dynamically
4. **Event Handling**: Manages mouse hover, touch, and scroll events

#### CSS Styling (`omas/static/omas/css/main.css`)

The tooltip styling includes:

```css
.german-tooltip {
  background: linear-gradient(135deg, var(--rich-walnut), var(--deep-walnut));
  border: 1px solid var(--border-gold);
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.translatable-german:hover {
  text-decoration: underline;
  text-decoration-style: dotted;
  text-decoration-color: var(--antique-gold);
}
```

#### HTML Markup

German terms can be marked for translation in two ways:

```html
<!-- Method 1: Using data attributes -->
<span data-german="Kaffeezeit" data-translation="Coffee Time - The traditional German afternoon coffee break, typically at 3 PM">
  Kaffeezeit
</span>

<!-- Method 2: Automatic detection (for terms in the dictionary) -->
<em>Gemütlichkeit</em> <!-- Automatically detected and made translatable -->
```

### Adding New Translations

To add new German terms:

1. **Update the Dictionary** in `german-translations.js`:
```javascript
const translations = {
    // Add new term
    'Neue Begriff': 'New Term - Description',
    // ...existing translations
};
```

2. **Mark HTML Elements** (optional for explicit control):
```html
<span data-german="Neue Begriff" data-translation="New Term - Description">
  Neue Begriff
</span>
```

### Current Translations

The system includes translations for:

- **Brand Terms**: Omas Coffee, Mit Erinnerung Gebraut
- **Coffee Culture**: Kaffeezeit, Gemütlichkeit
- **Food Terms**: Streuselkuchen
- **Common Words**: Oma, Kaffee, Getränk, Lebensart, Erinnerung, Gebraut
- **Phrases**: "Kaffee ist nicht nur ein Getränk, sondern eine Lebensart"

## Design Elements

### Color Palette

The Omas Coffee website uses a sophisticated color scheme:

- **Antique Gold** (`#d4af37`): Primary accent, logo elements
- **Deep Walnut** (`#2c1810`): Primary dark background
- **Rich Walnut** (`#4a2c20`): Secondary backgrounds
- **Cream** (`#faf8f3`): Primary light text
- **Soft Gold** (`#f5e6d3`): Body text on dark backgrounds

### Typography

- **Gothic Font**: UnifrakturMaguntia for brand name (German traditional style)
- **Body Font**: Inter for modern, clean readability
- **Font Scaling**: Responsive typography using CSS clamp() functions

### Visual Elements

- **Butterfly Motif**: Golden butterfly symbol representing transformation and memory
- **Walnut Wood Texture**: Visual references to the grandmother's cutting board
- **Gradient Backgrounds**: Subtle gradients creating depth and warmth

## Page Structure

### Homepage (`omas/templates/omas/home.html`)

1. **Hero Section**: Minimalist design with brand mark and tagline
2. **Story Section**: The Kaffeezeit tradition narrative
3. **Features Section**: Three-card layout highlighting key aspects
4. **Memorial Section**: Tribute to the owner's grandmother
5. **Coming Soon Section**: Spring 2025 opening announcement
6. **Quote Section**: Bilingual coffee philosophy quote

### Base Template (`omas/templates/omas/base.html`)

- **Header**: Simple navigation with gothic-styled brand name
- **Footer**: Four-column layout with hours, contact, newsletter signup
- **Meta Tags**: Bilingual HTML lang attribute (`de-en`)
- **Script Loading**: German translation JavaScript loaded globally

## Local Development

### Setup

1. **Add to hosts file** (for local domain testing):
```bash
echo "127.0.0.1 omas.coffee" | sudo tee -a /etc/hosts
```

2. **Run development server**:
```bash
python manage.py runserver
```

3. **Access the site**:
```
http://omas.coffee:8000
```

### Testing German Translations

1. **Hover over German text** to see translations
2. **Check console** for any JavaScript errors
3. **Test on mobile** using touch events
4. **Verify tooltip positioning** near viewport edges

## Configuration

### Django Settings

Required settings in `config/settings.py`:

```python
INSTALLED_APPS = [
    # ...
    'omas',
]

ALLOWED_HOSTS = [
    'omas.coffee',
    'www.omas.coffee',
    # ... other hosts
]

CSRF_TRUSTED_ORIGINS = [
    'https://omas.coffee',
    'https://www.omas.coffee',
]
```

### Middleware Configuration

The `DomainRoutingMiddleware` must be first in the middleware stack:

```python
MIDDLEWARE = [
    'config.domain_routing.DomainRoutingMiddleware',
    # ... other middleware
]
```

## Deployment

### DNS Configuration

Point the following domains to your application:
- `omas.coffee`
- `www.omas.coffee`

### SSL Certificates

Ensure SSL certificates cover both domains for HTTPS support.

### Static Files

Static files are served via WhiteNoise with automatic versioning and compression:
- CSS files are optimized with PostCSS and PurgeCSS
- JavaScript is minified with Terser
- Brotli and Gzip compression for all static assets

## Future Enhancements

Potential improvements for the German translation system:

1. **Audio Pronunciations**: Add audio clips for German term pronunciation
2. **Expanded Dictionary**: Include more coffee-related German terms
3. **User Preferences**: Remember tooltip display preferences
4. **Keyboard Navigation**: Support keyboard shortcuts for translations
5. **Translation API**: Dynamic translations for user-generated content
6. **Language Toggle**: Full page translation option for German/English

## Troubleshooting

### Common Issues

1. **Translations not appearing**:
   - Check that `german-translations.js` is loaded
   - Verify terms are in the translation dictionary
   - Check browser console for JavaScript errors

2. **Tooltips positioning incorrectly**:
   - Ensure CSS is properly loaded
   - Check for conflicting z-index values
   - Verify viewport calculations in JavaScript

3. **Domain not routing correctly**:
   - Confirm domain is in ALLOWED_HOSTS
   - Check DomainRoutingMiddleware is first in middleware
   - Verify domain mapping in domain_routing.py

## Related Documentation

- [Architecture Documentation](../architecture.md) - Multi-domain routing details
- [Deployment Documentation](../deployment.md) - Production deployment configuration
- [Commands Documentation](../commands.md) - Management commands for static files

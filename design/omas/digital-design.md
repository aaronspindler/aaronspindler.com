# Digital Design

This document provides specifications for all digital applications, including website design and social media presence.

## Quick Start
Use this guide when building websites, creating social media content, designing email campaigns, or developing any digital touchpoints. Ensures consistent digital brand expression.

---

## Web Design Specifications

### Layout
- **Max Width:** 1200px for content
- **Spacing:** 16px base unit (8px, 16px, 24px, 32px, 48px, 64px)
- **Grid:** 12-column responsive grid
- **Breakpoints:** Mobile (0-640px), Tablet (641-1024px), Desktop (1025px+)

### Typography Scale
- **Hero Heading:** 48-72px (mobile: 32-48px) - Inter Bold
- **H1:** 36-48px (mobile: 28-36px) - Inter Bold
- **H2:** 28-32px (mobile: 24-28px) - Inter Semibold
- **H3:** 24px (mobile: 20px) - Inter Medium
- **Body:** 16-18px - Inter Regular
- **Small/Caption:** 14px - Inter Regular
- **Line Height:** 1.5 for body, 1.2 for headings
- **Letter Spacing:** 0.02em for body, -0.01em for headings

### Font Implementation
```css
font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
```

### Buttons
- **Primary:** Antique gold background, deep walnut text, 12px padding vertical, 24px horizontal
- **Secondary:** Transparent with antique gold border (2px), antique gold text
- **Hover:** Brighten gold by 10%, subtle scale (1.02x) or lift shadow
- **Border Radius:** 4px (slightly rounded)
- **Font:** Sans-serif, medium weight, 14-16px

### Navigation
- **Style:** Horizontal top nav with logo left, links right
- **Mobile:** Hamburger menu with slide-in drawer
- **Hover:** Underline with antique gold, smooth animation (0.3s)
- **Active:** Antique gold color

### Cards & Containers
- **Background:** Rich walnut (#4a2c20) or deep black (#0a0908)
- **Border:** None or subtle 1px antique gold
- **Shadow:** Soft elevation (0 4px 12px rgba(0,0,0,0.3))
- **Padding:** 24-32px
- **Border Radius:** 8px

### Forms
- **Input Background:** Deep walnut (#2c1810) or transparent with border
- **Border:** 2px cream (#faf8f3), antique gold on focus
- **Text Color:** Cream (#faf8f3)
- **Placeholder:** Soft gold (#f5e6d3) at 60% opacity
- **Padding:** 12px 16px
- **Border Radius:** 4px

### Animations
- **Duration:** 0.3s for most interactions, 0.6s for page transitions
- **Easing:** ease-in-out or cubic-bezier(0.4, 0, 0.2, 1)
- **Effects:** Fade, slide, scale (subtle), blur transitions
- **Butterfly:** Gentle floating/hover animation (optional)

### Responsive Approach
- Mobile-first design methodology
- Touch-friendly targets (minimum 44x44px)
- Simplified navigation on mobile
- Stacked layouts for small screens
- Progressive enhancement for desktop

### Link Styles
- **Default:** Cream (#faf8f3) with underline
- **Hover:** Antique gold (#d4af37), underline animates
- **Visited:** Soft gold (#f5e6d3)
- **Focus:** 2px antique gold outline with 2px offset
- **Transition:** all 0.3s ease-in-out

### Loading States
- **Spinner:** Animated butterfly icon rotating gently
- **Progress Bar:** Antique gold (#d4af37) on deep walnut (#2c1810) track
- **Skeleton Screens:** Soft gold (#f5e6d3) at 20% opacity, subtle pulse
- **Loading Text:** "Brewing something special..." in italic

### Error States
- **Color:** Warm orange-red (#d45837) - maintains brand warmth
- **Icon:** X in circle, 20px, left of message
- **Message Style:** Inter Regular, 16px, clear explanation
- **Recovery Action:** Always provide next steps in antique gold button

### Footer Design
- **Background:** Deep black (#0a0908)
- **Layout:** 4 columns on desktop, stacked on mobile
- **Content Sections:**
  - Column 1: Logo, tagline, social icons
  - Column 2: Quick links (Menu, About, Location)
  - Column 3: Hours & Contact
  - Column 4: Newsletter signup
- **Copyright:** Centered, cream text, 14px
- **Spacing:** 64px padding top, 32px padding bottom

---

## Social Media Templates

### Instagram Post Layouts

#### Quote Posts
- **Background:** Deep walnut or deep black with subtle wood grain
- **Text:** Gothic font for featured word, sans-serif for rest
- **Accent:** Small butterfly or oak leaf ornament
- **Size:** 1080x1080px

#### Product Shots
- **Composition:** Center product, dark background, natural light
- **Overlay:** Minimal text (drink name) in corner
- **Style:** Consistent warm filter
- **Size:** 1080x1080px or 1080x1350px (4:5)

#### Behind-the-Scenes
- **Style:** Candid, process-oriented, hands at work
- **Text:** Small caption overlay with sans-serif font
- **Border:** Optional 20px cream border for cohesion
- **Size:** 1080x1080px

#### Announcement Posts
- **Layout:** Centered text on dark background
- **Logo:** Top or bottom placement
- **Icons:** Relevant icon (clock for hours, pin for location)
- **Size:** 1080x1080px

### Story Templates
- **Daily Special:** Product photo with "Today's Special" text overlay (cream text)
- **Location Update:** Map or cart photo with "Find Us Here" and address
- **Poll/Quiz:** Interactive with antique gold accent colors
- **Behind-the-Scenes:** Full-frame video or photo with minimal text
- **Size:** 1080x1920px

### Profile & Cover Images
- **Profile Image:** Circular badge/seal version of logo on transparent or cream background
- **Instagram:** 320x320px (displays at 110x110px)
- **Facebook Cover:** 820x312px with logo left or center, tagline
- **Keep:** Logo and text within safe zones (avoid profile picture overlap)

### Highlight Cover Designs
- **Style:** Circular icons on deep walnut background
- **Icons:** Menu (coffee cup), Location (pin), Hours (clock), About (butterfly)
- **Color:** Antique gold icons, cream background circle
- **Size:** 1080x1920px (displays circular at 161x161px)

### Post Caption Style
- **Opening:** Hook or question to engage
- **Body:** 2-3 short paragraphs, emotional or educational
- **Hashtags:** 5-10 relevant hashtags (separate line)
- **Emoji:** Minimal use, ☕ and 🦋 only
- **Call-to-Action:** "Visit us today" or "Tag a friend who needs a coffee break"

### Hashtag Strategy
- **Brand:** #OmasCoffee #BrewedWithMemory
- **Local:** #[City]Coffee #[City]Foodie
- **Category:** #CoffeeCart #MobileCoffee #GermanCoffee #CoffeeTime
- **Lifestyle:** #CoffeeMoments #Gemutlichkeit #AfternoonCoffee

### Posting Frequency
- **Instagram:** 4-5 posts per week, daily stories
- **Facebook:** 2-3 posts per week
- **Best Times:** Afternoon (2-4 PM) to align with Kaffeezeit theme

---

## Email Newsletter Templates

### Layout Structure
- **Width:** 600px maximum (responsive)
- **Background:** Cream (#faf8f3) with white content blocks
- **Font:** Georgia or system serif for better email client support
- **Fallback Fonts:** 'Times New Roman', serif

### Header Section
- **Height:** 120px
- **Logo:** Centered, 80px wide
- **Tagline:** Below logo, 14px, deep walnut (#2c1810)
- **Border Bottom:** 2px antique gold (#d4af37) line

### Content Sections

#### Hero Image
- **Size:** 600px wide, 400px height max
- **Alt Text:** Always descriptive for accessibility
- **Overlay Text:** Optional, cream on semi-transparent deep walnut

#### Body Content
- **Padding:** 32px all sides
- **Heading:** 24px, deep walnut (#2c1810), serif
- **Body Text:** 16px, dark gray (#333), 1.6 line height
- **Links:** Antique gold (#d4af37), underlined

#### Call-to-Action Buttons
- **Style:** Antique gold background, deep walnut text
- **Padding:** 16px 32px
- **Border Radius:** 4px
- **Full Width on Mobile:** Yes

### Footer Section
- **Background:** Deep walnut (#2c1810)
- **Text:** Cream (#faf8f3), 14px
- **Links:** Antique gold (#d4af37)
- **Content:** Social links, unsubscribe, address
- **Padding:** 24px

### Email Types

#### Welcome Series (3 emails)
1. **Welcome:** Brand story, Oma's legacy, first-visit discount
2. **Coffee Education:** Kaffeezeit tradition, brewing tips
3. **Community Invitation:** Social media, loyalty program

#### Weekly Newsletter
- **Subject Line Style:** "Oma's Weekly Brew: [Topic]"
- **Sections:** Featured drink, German word of week, upcoming events
- **Length:** 300-500 words maximum

#### Promotional Emails
- **Frequency:** Monthly maximum
- **Focus:** New offerings, seasonal items
- **Discount Code Style:** OMAS[SEASON][YEAR] (e.g., OMASFALL24)

---

## App Icons & Favicon

### Favicon Specifications
- **Size:** 32x32px and 16x16px
- **Design:** Simplified butterfly silhouette
- **Color:** Antique gold (#d4af37) on transparent
- **Format:** ICO for maximum compatibility, PNG for modern browsers

### App Icon Sizes
- **iOS:** 180x180px (iPhone), 152x152px (iPad)
- **Android:** 192x192px, 512x512px (Play Store)
- **Design:** Badge version with solid background
- **Background:** Deep walnut (#2c1810)
- **Safe Zone:** Keep logo within 80% of canvas

### Social Media Profile Images
- **Format:** Same design across all platforms
- **Background:** Deep walnut or cream depending on platform
- **Safe Area:** Center 80% for platform crop variations

---

**Related Documentation:**
- [Brand Foundation](brand-foundation.md) - Core brand identity
- [Design Guidelines](design-guidelines.md) - Photography, voice, iconography
- [Physical Design](physical-design.md) - Cart, packaging, and print materials
- [Brand Standards](brand-standards.md) - Usage rules and accessibility

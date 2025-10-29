# Deployment Guide

## Overview

Comprehensive guide for deploying the Django application to production using Docker, with WhiteNoise for static files, AWS S3 for media storage, Redis caching, PostgreSQL database, and Celery for background tasks.

## Prerequisites

- Docker and Docker Compose installed
- PostgreSQL 15+ database
- Redis server
- AWS S3 bucket (for media storage - photos, uploads)
- Domain name with DNS configured
- SSL certificate (Let's Encrypt recommended)

## Environment Configuration

### Required Environment Variables

Create a `.env.production` file:

```bash
# Core Django Settings
SECRET_KEY=your-long-random-secret-key-change-this-in-production
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
SITE_URL=https://yourdomain.com

# Database (PostgreSQL)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Redis (Cache & Celery Broker)
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# AWS S3 Storage (Required for media files - photos, uploads)
# Static files (CSS, JS, fonts) are served by WhiteNoise from the container
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=us-east-1
AWS_S3_CUSTOM_DOMAIN=your-cloudfront-domain  # Optional, for CloudFront CDN on media

# Email (Optional - for notifications)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# SMS Notifications (Optional - Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=+1234567890

# Optional Features
RESUME_ENABLED=True
RESUME_FILENAME=Your_Resume_2025.pdf

# Sentry (Error Tracking - Optional)
SENTRY_DSN=your-sentry-dsn

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Generating SECRET_KEY

```python
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

## Docker Deployment

### Dockerfile

The project includes a multi-stage Dockerfile optimized for production:

```dockerfile
# Stage 1: Build stage
FROM python:3.13-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Install Pyppeteer for screenshots
RUN pip install pyppeteer && python -c "from pyppeteer import chromium_downloader; chromium_downloader.download_chromium()"

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.13/site-packages/ /usr/local/lib/python3.13/site-packages/

# Copy application code
COPY . .

# Collect static files
RUN python manage.py collectstatic --noinput

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health/')"

# Run Gunicorn
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

### docker-compose.yml

Production Docker Compose configuration:

```yaml
version: '3.8'

services:
  web:
    build: .
    image: aaronspindler.com:latest
    container_name: website
    env_file:
      - .env.production
    ports:
      - "80:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health/"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:15
    container_name: postgres_db
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: redis_cache
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  celery:
    build: .
    container_name: celery_worker
    command: celery -A config worker --loglevel=info
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    volumes:
      - media_volume:/app/media
    restart: unless-stopped

  celery-beat:
    build: .
    container_name: celery_beat
    command: celery -A config beat --loglevel=info
    env_file:
      - .env.production
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  flower:
    build: .
    container_name: celery_flower
    command: celery -A config flower --port=5555
    env_file:
      - .env.production
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  static_volume:
  media_volume:
```

### Build and Deploy

```bash
# Build Docker image
docker-compose -f docker-compose.production.yml build

# Start services
docker-compose -f docker-compose.production.yml up -d

# View logs
docker-compose -f docker-compose.production.yml logs -f

# Stop services
docker-compose -f docker-compose.production.yml down

# Restart services
docker-compose -f docker-compose.production.yml restart
```

## Database Setup

### Create PostgreSQL Database

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE aaronspindler_db;

# Create user
CREATE USER aaronspindler WITH PASSWORD 'your-secure-password';

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE aaronspindler_db TO aaronspindler;

# Enable extensions
\c aaronspindler_db
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

### Run Migrations

```bash
# Inside Docker container
docker exec -it website python manage.py migrate

# Or with docker-compose
docker-compose -f docker-compose.production.yml exec web python manage.py migrate
```

### Create Superuser

```bash
# Interactive mode
docker exec -it website python manage.py createsuperuser

# Or programmatically
docker exec -it website python manage.py shell -c "
from accounts.models import User;
User.objects.create_superuser('admin', 'admin@example.com', 'secure-password')
"
```

## AWS S3 Configuration

### S3 Bucket Setup

1. **Create S3 Bucket**:
   - Bucket name: `your-bucket-name`
   - Region: `us-east-1` (or your preferred region)
   - Block all public access: Disabled (for media files)

2. **Bucket Policy** (for public read access to media files):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::your-bucket-name/media/*"
    }
  ]
}
```

3. **CORS Configuration**:

```json
[
  {
    "AllowedHeaders": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedOrigins": ["https://yourdomain.com"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3000
  }
]
```

### CloudFront CDN (Optional but Recommended)

1. **Create CloudFront Distribution**:
   - Origin: Your S3 bucket
   - Viewer Protocol Policy: Redirect HTTP to HTTPS
   - Compress Objects Automatically: Yes
   - Price Class: Use only North America and Europe (or All Edge Locations)

2. **Configure Django Settings**:

```python
# settings.py
AWS_S3_CUSTOM_DOMAIN = 'd1234567890abc.cloudfront.net'
```

### IAM User Permissions

Create IAM user with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::your-bucket-name",
        "arn:aws:s3:::your-bucket-name/*"
      ]
    }
  ]
}
```

## Web Server Configuration

### Nginx Reverse Proxy

**File**: `/etc/nginx/sites-available/aaronspindler.com`

```nginx
upstream django {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Static files (served by nginx)
    location /static/ {
        alias /app/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files (if not using S3)
    location /media/ {
        alias /app/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    # Django application
    location / {
        proxy_pass http://django;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (skip logging)
    location /health/ {
        proxy_pass http://django;
        access_log off;
    }

    # Increase client body size for photo uploads
    client_max_body_size 50M;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss application/rss+xml image/svg+xml;

    # Logging
    access_log /var/log/nginx/aaronspindler_access.log;
    error_log /var/log/nginx/aaronspindler_error.log;
}
```

### Enable Site

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/aaronspindler.com /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## SSL Certificate (Let's Encrypt)

### Install Certbot

```bash
# Install Certbot
sudo apt-get update
sudo apt-get install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

## Post-Deployment Tasks

### 1. Run Management Commands

```bash
# Collect static files
docker exec -it website python manage.py collectstatic_optimize

# Build CSS
docker exec -it website python manage.py build_css

# Rebuild knowledge graph
docker exec -it website python manage.py rebuild_knowledge_graph

# Rebuild search index
docker exec -it website python manage.py rebuild_search_index

# Setup periodic tasks
docker exec -it website python manage.py setup_periodic_tasks

# Generate album zips
docker exec -it website python manage.py generate_album_zips --all
```

### 2. Run Initial Lighthouse Audit

```bash
docker exec -it website python manage.py run_lighthouse_audit
```

### 3. Test Application

```bash
# Check health endpoint
curl https://yourdomain.com/health/

# Check API endpoints
curl https://yourdomain.com/api/knowledge-graph/
curl https://yourdomain.com/api/search/autocomplete/?q=test

# Check admin panel
curl https://yourdomain.com/admin/
```

## Monitoring

### Application Monitoring

- **Health Checks**: `/health/` endpoint
- **Uptime Monitoring**: UptimeRobot, Pingdom, or StatusCake
- **Error Tracking**: Sentry integration
- **Performance**: Lighthouse audits (automated nightly)

### Server Monitoring

```bash
# Docker stats
docker stats

# Container logs
docker-compose logs -f web
docker-compose logs -f celery
docker-compose logs -f celery-beat

# System resources
htop
df -h
free -m
```

### Celery Monitoring (Flower)

Access Flower dashboard: `https://yourdomain.com:5555`

**Secure Flower with Basic Auth**:

```yaml
# docker-compose.yml
flower:
  command: celery -A config flower --port=5555 --basic_auth=admin:secure-password
```

## Backups

### Database Backups

```bash
# Automated daily backup script
#!/bin/bash
BACKUP_DIR="/backups/postgres"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="backup_$DATE.sql.gz"

docker exec postgres_db pg_dump -U aaronspindler aaronspindler_db | gzip > "$BACKUP_DIR/$FILENAME"

# Keep only last 30 days
find "$BACKUP_DIR" -type f -mtime +30 -delete

# Upload to S3
aws s3 cp "$BACKUP_DIR/$FILENAME" s3://your-backup-bucket/postgres/
```

**Crontab**:
```cron
0 2 * * * /path/to/backup-script.sh
```

### Media Backups

S3 automatically handles media file storage. Enable S3 versioning for additional protection.

## Scaling

### Horizontal Scaling

1. **Multiple Web Workers**:

```yaml
# docker-compose.yml
web:
  deploy:
    replicas: 3
```

2. **Load Balancer**:
   - Use AWS ALB, Nginx, or HAProxy
   - Configure health checks
   - Enable session stickiness (if needed)

### Database Read Replicas

```python
# settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aaronspindler_db',
        'USER': 'aaronspindler',
        'PASSWORD': 'password',
        'HOST': 'primary-db',
        'PORT': '5432',
    },
    'replica': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'aaronspindler_db',
        'USER': 'aaronspindler',
        'PASSWORD': 'password',
        'HOST': 'replica-db',
        'PORT': '5432',
    }
}
```

### Celery Worker Scaling

```bash
# Scale Celery workers
docker-compose up -d --scale celery=4
```

## Security Hardening

### Firewall Configuration

```bash
# Allow SSH, HTTP, HTTPS
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

### Fail2Ban

```bash
# Install Fail2Ban
sudo apt-get install fail2ban

# Configure for nginx
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Regular Updates

```bash
# Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# Update Docker images
docker-compose pull
docker-compose up -d

# Update Python dependencies
pip install --upgrade -r requirements.txt
```

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker-compose logs web

# Check container status
docker ps -a

# Restart services
docker-compose restart web
```

### Database Connection Issues

```bash
# Test database connection
docker exec -it website python manage.py dbshell

# Check PostgreSQL logs
docker logs postgres_db
```

### Static Files Not Loading

```bash
# Re-collect static files
docker exec -it website python manage.py collectstatic --clear --noinput

# Check S3 bucket permissions
aws s3 ls s3://your-bucket-name/static/
```

### Celery Tasks Not Running

```bash
# Check Celery worker logs
docker logs celery_worker

# Check Celery Beat scheduler
docker logs celery_beat

# Monitor with Flower
open http://localhost:5555
```

## Related Documentation

- [Architecture](architecture.md) - System design
- [Commands](commands.md) - Management commands
- [Maintenance](maintenance.md) - Ongoing maintenance
- [Testing](testing.md) - Pre-deployment testing

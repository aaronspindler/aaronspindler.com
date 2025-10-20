# FeeFiFoFunds Development Environment Setup

Complete Docker-based development environment with all services pre-configured.

## Quick Start

```bash
# Start the entire development environment
make dev-up

# View logs
make dev-logs

# Access the application
open http://localhost:8002

# When done
make dev-down
```

That's it! 🎉

## What's Included

The development environment includes:

- **Django Web Server** (localhost:8002)
  - Hot-reload enabled
  - Debug mode active
  - Admin user pre-created
  - All migrations auto-applied

- **PostgreSQL with TimescaleDB** (localhost:5434)
  - Optimized for time-series data
  - Pre-configured hypertables
  - Persistent data volumes

- **Redis** (localhost:6381)
  - Caching layer
  - Celery message broker
  - Session storage

- **Celery Worker**
  - Async task processing
  - 4 concurrent workers
  - Auto-reload on code changes

- **Celery Beat**
  - Scheduled task runner
  - Database scheduler
  - Auto-configured periodic tasks

- **Flower** (localhost:5557)
  - Celery monitoring UI
  - Task history
  - Worker status

## Available Commands

### Environment Management

```bash
make dev-up          # Start all services
make dev-down        # Stop all services
make dev-restart     # Restart all services
make dev-clean       # Stop and remove volumes (fresh start)
make dev-build       # Rebuild Docker images
make dev-logs        # View logs (Ctrl+C to stop)
```

### Development Tools

```bash
make dev-shell       # Open Django shell
make dev-bash        # Open bash shell in container
make dev-psql        # Open PostgreSQL shell
make dev-redis       # Open Redis CLI
```

### Database Operations

```bash
make dev-migrate          # Run migrations
make dev-makemigrations   # Create new migrations
```

### Testing

```bash
make dev-test        # Run tests in dev environment
```

## Default Credentials

- **Admin User**: admin / admin123
- **PostgreSQL**: feefifofunds_dev / dev_password_change_in_production
- **Database Name**: feefifofunds_dev

## Service URLs

- Django Admin: http://localhost:8002/admin/
- API Root: http://localhost:8002/api/v1/
- Swagger Docs: http://localhost:8002/api/docs/
- ReDoc: http://localhost:8002/api/redoc/
- Flower (Celery): http://localhost:5557/

## Ports

To avoid conflicts with other services:
- Web: 8002 (instead of 8000)
- PostgreSQL: 5434 (instead of 5432)
- Redis: 6381 (instead of 6379)
- Flower: 5557 (instead of 5555)

## File Structure

```
docker-compose.dev.yml   # Main compose file
.env.dev.example         # Environment template
Makefile                 # Convenient commands
```

## Environment Variables

Copy `.env.dev.example` to `.env.dev` and update values:

```bash
cp .env.dev.example .env.dev
```

Key variables:
- `SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection
- `REDIS_URL` - Redis connection
- API keys for external data sources (optional)

## Volumes

Persistent data is stored in Docker volumes:
- `postgres_dev_data` - Database files
- `redis_dev_data` - Redis persistence
- `static_volume` - Collected static files
- `media_volume` - Uploaded media

To reset everything:
```bash
make dev-clean  # Removes all volumes and data
```

## Workflows

### First Time Setup

```bash
# 1. Build images
make dev-build

# 2. Start environment
make dev-up

# 3. Watch logs to see progress
make dev-logs

# Wait for "Starting development server..." message
# Then access http://localhost:8002
```

### Daily Development

```bash
# Start services
make dev-up

# Work on code (changes auto-reload)
# ...

# When done
make dev-down
```

### Running Migrations

```bash
# Create migration
make dev-makemigrations

# Apply migration
make dev-migrate
```

### Debugging

```bash
# View logs
make dev-logs

# Open Django shell
make dev-shell

# Check database
make dev-psql

# Check Redis
make dev-redis

# Restart specific service
docker-compose -f docker-compose.dev.yml restart web
```

### Resetting Database

```bash
# Stop and remove all data
make dev-clean

# Start fresh
make dev-up
```

## Troubleshooting

### Port Already in Use

Change ports in `docker-compose.dev.yml`:
```yaml
ports:
  - "8003:8000"  # Use 8003 instead of 8002
```

### Database Connection Issues

```bash
# Check if postgres is healthy
docker-compose -f docker-compose.dev.yml ps

# View postgres logs
docker-compose -f docker-compose.dev.yml logs postgres

# Restart postgres
docker-compose -f docker-compose.dev.yml restart postgres
```

### Celery Not Processing Tasks

```bash
# Check worker logs
docker-compose -f docker-compose.dev.yml logs celery_worker

# Restart worker
docker-compose -f docker-compose.dev.yml restart celery_worker

# Check in Flower
open http://localhost:5557
```

### Changes Not Reflecting

```bash
# Rebuild images
make dev-build

# Restart services
make dev-restart
```

## Performance

The development environment is optimized for:
- Fast startup (~30 seconds)
- Auto-reload on code changes
- Persistent data (survives restarts)
- Minimal resource usage

## Production vs Development

| Feature | Development | Production |
|---------|-------------|-----------|
| Debug mode | Enabled | Disabled |
| Auto-reload | Yes | No |
| Database | TimescaleDB (dev) | TimescaleDB (production) |
| Static files | CollectStatic | S3 + CloudFront |
| Workers | 4 | 16+ |
| Logging | Console | File + Sentry |
| CORS | Permissive | Strict |

## Next Steps

After environment is running:
1. Access admin panel: http://localhost:8002/admin/
2. Explore API docs: http://localhost:8002/api/docs/
3. Monitor Celery: http://localhost:5557/
4. Start implementing features!

## Related Documentation

- Main README: `/README.md`
- CLAUDE.md: `/CLAUDE.md`
- Tickets: `/feefifofunds/TICKETS.md`

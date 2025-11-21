# Quick Start Guide

*Get aaronspindler.com running locally in 10 minutes*

## Prerequisites

- Python 3.13+
- Docker & Docker Compose
- Git

## 1. Clone & Setup (2 min)

```bash
# Clone repository
git clone https://github.com/aaronspindler/aaronspindler.com.git
cd aaronspindler.com

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install uv
uv pip install -r requirements/base.txt -r requirements/local.txt
```

## 2. Configure Environment (1 min)

```bash
# Copy environment template
cp .env.example .env

# Edit .env with minimal required settings:
echo "SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" >> .env
echo "DEBUG=True" >> .env
echo "DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aaronspindler_dev" >> .env
echo "REDIS_URL=redis://localhost:6379/0" >> .env
```

## 3. Start Services (2 min)

```bash
# Start PostgreSQL, Redis, and QuestDB
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps
```

## 4. Initialize Database (2 min)

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Load sample data (optional)
python manage.py loaddata fixtures/sample_data.json
```

## 5. Build Assets (1 min)

```bash
# Install Node dependencies
npm install

# Build CSS and JavaScript
npm run build
```

## 6. Run Development Server (1 min)

```bash
# Start Django development server
python manage.py runserver

# Access the application
open http://localhost:8000        # Main site
open http://localhost:8000/admin  # Admin panel
```

## 🎉 You're Running!

The application is now running locally with:
- ✅ Django development server on port 8000
- ✅ PostgreSQL database on port 5432
- ✅ Redis cache on port 6379
- ✅ QuestDB (if using FeeFiFoFunds) on ports 8812/9000

## Essential Commands

### Development

```bash
# Run tests
python manage.py test

# Run tests with Docker (full stack)
make test

# Format code
pre-commit run --all-files

# Django shell
python manage.py shell_plus

# Database shell
python manage.py dbshell
```

### Docker

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Stop all services
docker-compose -f docker-compose.dev.yml down

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Clean everything
docker-compose -f docker-compose.dev.yml down -v
```

### Static Files

```bash
# Collect static files
python manage.py collectstatic

# Build CSS
python manage.py build_css

# Watch for changes
npm run watch:css
```

## Project Structure

```
aaronspindler.com/
├── apps/              # Django applications
│   ├── blog/         # Blog with knowledge graph
│   ├── photos/       # Photo gallery
│   └── ...
├── config/           # Django settings
├── deployment/       # Docker & deployment files
├── docs/            # Documentation
├── static/          # Static assets
├── templates/       # HTML templates
└── requirements/    # Python dependencies
```

## Common Issues

### Port Already in Use

```bash
# Find and kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or use a different port
python manage.py runserver 8001
```

### Database Connection Error

```bash
# Ensure PostgreSQL is running
docker-compose -f docker-compose.dev.yml up -d postgres

# Check connection
psql postgresql://postgres:postgres@localhost:5432/aaronspindler_dev
```

### Missing Dependencies

```bash
# Python dependencies
uv pip install -r requirements/base.txt -r requirements/local.txt

# Node dependencies
npm install

# Pre-commit hooks
pre-commit install
```

## Docker Development (Alternative)

Run everything in Docker:

```bash
# Build and start all services
docker-compose -f docker-compose.dev.yml up --build

# Access at http://localhost:8000
```

## Next Steps

### Set Up Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files  # Initial check
```

### Configure Your Editor

- **VS Code**: Install Python and Django extensions
- **PyCharm**: Mark `apps/` as Sources Root
- **Vim/Neovim**: Install CoC or LSP with Pylsp

### Explore the Documentation

- [Development Guide](development.md) - Detailed development setup
- [Architecture Overview](infrastructure/architecture.md) - System design
- [Testing Guide](testing.md) - Running and writing tests
- [Commands Reference](commands.md) - All management commands

### Try Key Features

1. **Create a Blog Post**: Visit `/admin/blog/blogpost/`
2. **Upload a Photo**: Visit `/admin/photos/photo/`
3. **View Knowledge Graph**: Visit `/knowledge-graph/`
4. **Search**: Try the search box on the homepage

## Useful Resources

- **Documentation**: `/docs/README.md`
- **Admin Panel**: `http://localhost:8000/admin`
- **API Endpoints**: `http://localhost:8000/api/`
- **Flower (Celery)**: `http://localhost:5555`

## Getting Help

- Check [Troubleshooting Guide](troubleshooting/ci-cd.md)
- Review [Development Guide](development.md) for detailed setup
- Open an issue on [GitHub](https://github.com/aaronspindler/aaronspindler.com)

## Tips for New Contributors

1. **Always run tests before committing**:
   ```bash
   python manage.py test
   pre-commit run --all-files
   ```

2. **Follow the commit convention**:
   ```bash
   git commit -m "feat(photos): add EXIF extraction"
   git commit -m "fix(auth): correct login redirect"
   ```

3. **Keep your branch updated**:
   ```bash
   git checkout main
   git pull origin main
   git checkout your-branch
   git rebase main
   ```

4. **Use the Makefile for common tasks**:
   ```bash
   make help     # Show all available commands
   make test     # Run tests
   make format   # Format code
   make clean    # Clean up
   ```

---

**Ready to contribute?** Check out the [Development Guide](development.md) for the complete development workflow!

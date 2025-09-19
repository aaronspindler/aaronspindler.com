# ActionsUptime

A comprehensive monitoring service for GitHub Actions workflows and web endpoints, providing real-time status tracking, notifications, and uptime analytics.

## 🚀 Features

### GitHub Actions Monitoring
- **Workflow Status Tracking**: Monitor the health of your GitHub Actions workflows
- **Branch-Specific Monitoring**: Track specific branches (main, develop, feature branches)
- **Multiple Check Methods**:
  - Badge-based checking for public repositories
  - API-based checking for private repositories (with GitHub OAuth)
- **Historical Timeline**: View success/failure rates over hourly, daily, or monthly periods

### Web Endpoint Monitoring
- **Multi-Region Monitoring**: Check endpoints from multiple AWS Lambda regions
- **Flexible HTTP Methods**: Support for GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
- **Advanced Configuration**:
  - Custom status codes for "up" state
  - Request timeout configuration
  - SSL certificate validation
  - Domain expiration monitoring
  - Custom headers and request body
  - Authentication support (Basic, Digest)
- **Latency Tracking**: Monitor response times across regions

### Notification System
- **Multi-Channel Alerts**:
  - Email notifications via AWS SES
  - SMS notifications
  - In-app notification center
- **Smart Alerting**: Only notify on status changes (success → failure or failure → success)
- **Customizable Recipients**: Add multiple email addresses and phone numbers per monitor

### Analytics & Reporting
- **Uptime Percentage**: Real-time calculation of success rates
- **Performance Metrics**: Average latency, response time trends
- **Visual Timeline**: Interactive charts showing status history
- **Public Status Pages**: Share monitor status via unique URLs

## 🛠 Technology Stack

### Backend
- **Framework**: Django 5.1.7
- **Database**: PostgreSQL (via psycopg)
- **Cache**: Redis
- **Task Queue**: Celery with Redis broker
- **Scheduled Tasks**: Celery Beat with django-celery-beat

### Infrastructure
- **Container Orchestration**: Docker with multiple services
- **Email Service**: AWS SES (django-ses)
- **Error Tracking**: Sentry
- **Static Files**: WhiteNoise with compression

### Authentication & Payments
- **OAuth**: GitHub integration via django-allauth
- **Payments**: Stripe integration via dj-stripe
- **User Management**: Custom user model with subscription tracking

### Deployment
- **Web Server**: Gunicorn with gevent workers
- **Services**:
  - Main web application
  - Celery worker for background tasks
  - Celery Beat for scheduled tasks
  - Flower for task monitoring

## 📦 Installation

### Prerequisites
- Python 3.10+
- PostgreSQL
- Redis
- Node.js (for frontend assets)

### Local Development Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd ActionsUptime
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
Create a `.env` file in the project root:
```env
SECRET_KEY=your_secret_key_here
DEBUG=True
DATABASE_URL=postgresql://user:password@localhost/actionsuptime
REDIS_URL=redis://localhost:6379

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# AWS SES
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Stripe
STRIPE_LIVE_MODE=False
STRIPE_TEST_PUBLIC_KEY=your_stripe_public_key
STRIPE_TEST_SECRET_KEY=your_stripe_secret_key

# Sentry (optional)
SENTRY_DSN=your_sentry_dsn
```

5. **Run database migrations**
```bash
python manage.py migrate
```

6. **Create superuser**
```bash
python manage.py createsuperuser
```

7. **Start development server**
```bash
python manage.py runserver
```

8. **Start Celery worker (in separate terminal)**
```bash
celery -A config worker -l INFO
```

9. **Start Celery Beat (in separate terminal)**
```bash
celery -A config beat -l INFO
```

## 🐳 Docker Deployment

The project includes Docker configuration for production deployment with four services:

1. **Web Service** (`backend.Dockerfile`)
   - Main Django application
   - Serves via Gunicorn

2. **Celery Worker** (`celery.Dockerfile`)
   - Processes background tasks
   - Handles status checks and notifications

3. **Celery Beat** (`celery-beat.Dockerfile`)
   - Schedules periodic tasks
   - Manages monitoring intervals

4. **Flower** (`flower.Dockerfile`)
   - Web interface for monitoring Celery tasks
   - Provides task statistics and worker status

### Captain Definition Files
The project uses CapRover for deployment with separate captain definitions for each service:
- `captain-definition-web`: Main web application
- `captain-definition-celery`: Background task worker
- `captain-definition-celery-beat`: Task scheduler
- `captain-definition-flower`: Task monitoring UI

## 📋 Management Commands

### Actions Management
```bash
# Check all actions status
python manage.py check_actions

# Sync actions with scheduled tasks
python manage.py sync_action_intervals
```

### Endpoint Management
```bash
# Check all endpoints
python manage.py check_all_endpoints

# Deploy Lambda functions for endpoint monitoring
python manage.py lambda_deploy

# Sync endpoint intervals
python manage.py sync_endpoint_intervals

# Update Lambda functions
python manage.py update_lambdas
```

## 🔧 Configuration

### Monitoring Intervals
Available intervals for both Actions and Endpoints:
- 1 minute (`1M`)
- 5 minutes (`5M`) - Default
- 10 minutes (`10M`)
- 30 minutes (`30M`)
- 1 hour (`1H`)
- 6 hours (`6H`)
- 12 hours (`12H`)
- 24 hours (`24H`)

### Supported AWS Regions for Endpoint Monitoring
- US East (N. Virginia)
- US West (Oregon)
- EU (Ireland)
- AP (Singapore)
- And more...

## 📊 API Endpoints

### Actions
- `GET /actions/` - List all monitored actions
- `GET /action-status/<uuid>/` - Public status page for an action

### Endpoints
- `GET /endpoints/` - List all monitored endpoints
- `POST /endpoints/add/` - Add new endpoint
- `GET /endpoints/<id>/edit/` - Edit endpoint configuration
- `DELETE /endpoints/<id>/delete/` - Remove endpoint

### Account
- `/accounts/login/` - User login
- `/accounts/signup/` - User registration
- `/accounts/github/login/` - GitHub OAuth login

## 🔒 Security Features

- CSRF protection
- Secure session management
- OAuth 2.0 for GitHub integration
- Encrypted password storage
- SSL/TLS support
- Environment-based configuration
- Sentry error tracking in production

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📄 License

[Add your license information here]

## 🌐 Live Service

Visit [actionsuptime.com](https://actionsuptime.com) to use the hosted version of ActionsUptime.

## 📞 Support

For support, please visit the [support page](https://actionsuptime.com/support) or open an issue in the repository.

## 🗺 Roadmap

Check out our [public roadmap](https://actionsuptime.com/roadmap) to see what features are coming next!

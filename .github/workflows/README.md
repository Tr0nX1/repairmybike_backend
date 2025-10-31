# GitHub Workflows Documentation

This directory contains GitHub Actions workflows for the RepairMyBike Django backend project.

## Workflows

### 1. CI/CD Pipeline (`ci-cd.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

**Jobs:**
- **Test**: Runs Django tests with PostgreSQL and Redis services
- **Security Scan**: Performs security analysis using Bandit and Safety
- **Build and Deploy**: Builds the application and prepares for deployment (main branch only)
- **Notify**: Sends notifications about workflow status

**Features:**
- ✅ Automated testing with coverage reporting
- ✅ Code formatting checks (Black, isort)
- ✅ Linting with flake8
- ✅ Security vulnerability scanning
- ✅ Database migrations validation
- ✅ Docker image building (if Dockerfile exists)
- ✅ Coverage reporting to Codecov

### 2. Dependency Updates & Security (`dependency-update.yml`)

**Triggers:**
- Scheduled: Every Monday at 9 AM UTC
- Manual trigger via workflow_dispatch

**Jobs:**
- **Dependency Check**: Scans for security vulnerabilities in dependencies
- **Outdated Dependencies**: Identifies packages that need updates

**Features:**
- ✅ Automated vulnerability scanning with pip-audit
- ✅ Automatic issue creation for security vulnerabilities
- ✅ Weekly dependency health reports

## Required Secrets

Configure these secrets in your GitHub repository settings (`Settings > Secrets and variables > Actions`):

### Production Secrets
```
SECRET_KEY              # Django secret key for production
DATABASE_URL           # Production database connection string
REDIS_URL             # Production Redis connection string
ALLOWED_HOSTS         # Comma-separated list of allowed hosts
```

### Optional Deployment Secrets
```
HEROKU_API_KEY        # For Heroku deployment
AWS_ACCESS_KEY_ID     # For AWS deployment
AWS_SECRET_ACCESS_KEY # For AWS deployment
DOCKER_USERNAME       # For Docker Hub
DOCKER_PASSWORD       # For Docker Hub
```

### Third-party Service Secrets
```
DESCOPE_PROJECT_ID    # Descope authentication
RAZORPAY_KEY_ID      # Razorpay payment gateway
RAZORPAY_KEY_SECRET  # Razorpay payment gateway
CODECOV_TOKEN        # For coverage reporting (optional)
```

## Environment Variables

The workflows use these environment variables:

### Test Environment
- `PYTHON_VERSION`: Python version to use (default: 3.11)
- `POSTGRES_PASSWORD`: PostgreSQL password for testing
- `POSTGRES_USER`: PostgreSQL username for testing
- `POSTGRES_DB`: PostgreSQL database name for testing

### Production Environment
- `DEBUG`: Set to False for production
- `SECRET_KEY`: Django secret key
- `DATABASE_URL`: Database connection string
- `REDIS_URL`: Redis connection string
- `ALLOWED_HOSTS`: Allowed hosts for Django

## Setup Instructions

1. **Enable GitHub Actions** in your repository settings
2. **Add required secrets** in repository settings
3. **Customize deployment** in the `build-and-deploy` job
4. **Configure branch protection** rules for main branch
5. **Set up Codecov** (optional) for coverage reporting

## Customization

### Adding New Tests
- Tests are automatically discovered by Django's test runner
- Add new test files following Django conventions
- Coverage reports will include new tests automatically

### Modifying Deployment
Edit the `build-and-deploy` job in `ci-cd.yml`:
- Uncomment and configure deployment commands
- Add platform-specific deployment steps
- Configure environment-specific secrets

### Security Scanning
- Bandit scans for common security issues
- Safety checks for known vulnerabilities
- pip-audit provides comprehensive dependency scanning

### Code Quality
- Black enforces code formatting
- isort organizes imports
- flake8 performs linting

## Troubleshooting

### Common Issues

1. **Test failures**: Check database connections and migrations
2. **Security scan failures**: Review and update vulnerable dependencies
3. **Deployment failures**: Verify secrets and deployment configuration
4. **Coverage issues**: Ensure all code paths are tested

### Debugging Workflows
- Check workflow logs in the Actions tab
- Verify secrets are properly configured
- Ensure branch protection rules allow workflow execution
- Review artifact uploads for detailed reports

## Best Practices

1. **Keep secrets secure**: Never commit secrets to the repository
2. **Test locally**: Run tests and linting locally before pushing
3. **Review security reports**: Address vulnerabilities promptly
4. **Monitor dependencies**: Keep packages updated regularly
5. **Use branch protection**: Require status checks before merging
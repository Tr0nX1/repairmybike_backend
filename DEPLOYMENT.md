# RepairMyBike Backend - Multi-Environment Setup

This Django backend is configured to work seamlessly across different environments:

## 🏠 Local Development
- **Database**: SQLite (`db.sqlite3`)
- **Configuration**: `.env` file with `DATABASE_URL` commented out
- **Cache**: Local memory cache
- **Server**: `python manage.py runserver`

## 🧪 CI/CD Testing (GitHub Actions)
- **Database**: SQLite (automatic fallback)
- **Configuration**: Environment variables set in workflow
- **Cache**: Local memory cache
- **Tests**: Automated on push/PR to main branch

## 🚀 Production (Railway)
- **Database**: PostgreSQL (Railway managed)
- **Configuration**: Railway environment variables
- **Cache**: Redis (Railway managed)
- **Server**: Gunicorn/uWSGI

## Environment Configuration

### Local Development Setup
1. Copy `.env.example` to `.env`
2. Keep `DATABASE_URL` commented out for SQLite
3. Run migrations: `python manage.py migrate`
4. Start server: `python manage.py runserver`

### Production Deployment
1. Set environment variables in Railway:
   ```
   DATABASE_URL=postgresql://user:pass@host:port/db
   SECRET_KEY=your-production-secret
   DEBUG=False
   ALLOWED_HOSTS=your-domain.railway.app
   ```
2. Deploy via Railway CLI or GitHub integration

## Database Configuration Logic

The Django settings automatically detect the environment:

```python
DATABASE_URL = config('DATABASE_URL', default=None)

if DATABASE_URL:
    # Production: Use PostgreSQL via DATABASE_URL
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL)}
else:
    # Local/CI: Use SQLite
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
```

## GitHub Actions Workflow

The CI/CD pipeline:
1. ✅ Uses SQLite for testing (no external database needed)
2. ✅ Runs Django system checks
3. ✅ Executes database migrations
4. ✅ Runs test suite
5. ✅ Validates code quality

## Switching Between Environments

### Local → Production
1. Uncomment `DATABASE_URL` in `.env`
2. Set production database URL
3. Run migrations: `python manage.py migrate`

### Production → Local
1. Comment out `DATABASE_URL` in `.env`
2. Run migrations: `python manage.py migrate`
3. SQLite database will be created automatically

## Benefits of This Setup

- 🔄 **Seamless switching** between environments
- 🚀 **Fast local development** with SQLite
- 🧪 **Reliable CI/CD** without external dependencies
- 🔒 **Secure production** with managed PostgreSQL
- 📦 **Easy deployment** to Railway or other platforms

## Troubleshooting

### "Connection failed" errors
- Check if you're trying to use production database locally
- Ensure `DATABASE_URL` is commented out for local development

### Migration issues
- Run `python manage.py showmigrations` to check status
- Use `python manage.py migrate` to apply pending migrations

### CI/CD failures
- Verify GitHub Actions workflow uses SQLite (no `DATABASE_URL` set)
- Check that PostgreSQL service is removed from workflow
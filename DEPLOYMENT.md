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

## 📦 Media Storage (Cloudflare R2)

Use Cloudflare R2 to store and serve media files (images, uploads) with CDN caching.

### Setup Steps
1. Create an R2 bucket in Cloudflare dashboard.
2. Generate an R2 API token with permissions: `Object Read/Write` for the bucket.
3. Note the R2 endpoint URL (looks like `https://<accountid>.r2.cloudflarestorage.com`).
4. (Recommended) Create a DNS record for a custom media domain, e.g. `media.yourdomain.com`, and proxy it through Cloudflare pointing to the R2 public bucket or a Worker route.

### Required Environment Variables
Set these in Railway (or your environment):

```
USE_CLOUDFLARE_R2=true
R2_ACCESS_KEY_ID=<your-access-key>
R2_SECRET_ACCESS_KEY=<your-secret-key>
R2_BUCKET_NAME=<your-bucket>
R2_ENDPOINT_URL=https://<accountid>.r2.cloudflarestorage.com
R2_REGION=auto
R2_SIGNATURE_VERSION=s3v4
R2_QUERYSTRING_AUTH=false
# Optional if you have a proxied custom domain
CF_MEDIA_DOMAIN=media.yourdomain.com
```

### Django Configuration
When `USE_CLOUDFLARE_R2=true`, the backend switches to `django-storages` S3 backend targeting Cloudflare R2. `MEDIA_URL` is built from `CF_MEDIA_DOMAIN` if provided, otherwise from `R2_ENDPOINT_URL` and `R2_BUCKET_NAME`.

All `ImageField`/`FileField` uploads will go to R2, and API responses will include absolute URLs suitable for the Flutter app.

### Flutter Integration
- The backend now returns absolute media URLs. Use `Image.network(url)` directly.
- Existing relative paths will be normalized to absolute URLs in API serializers (e.g., Services `images`).

### Migration Notes
- If you have existing local files, upload them to R2 and update DB references if they were stored as plain relative paths.
- New uploads will automatically be stored in R2 once the env vars are set and the app is redeployed.

## 📦 Media Storage (Cloudinary)

Use Cloudinary to store and serve media files with built-in transformations and a global CDN.

### Setup Steps
1. Create a Cloudinary account and a product environment (Cloud Name).
2. From the dashboard, copy your `Cloud Name`, `API Key`, and `API Secret`.
3. Option A: Copy the consolidated `CLOUDINARY_URL` (it looks like `cloudinary://<api_key>:<api_secret>@<cloud_name>`).

### Required Environment Variables
Set one of the following options:

```
USE_CLOUDINARY=true

# Option A: Single URL
CLOUDINARY_URL=cloudinary://<api_key>:<api_secret>@<cloud_name>

# Option B: Discrete keys
CLOUDINARY_CLOUD_NAME=<cloud_name>
CLOUDINARY_API_KEY=<api_key>
CLOUDINARY_API_SECRET=<api_secret>
```

### Django Configuration
When `USE_CLOUDINARY=true`, the backend switches to `django-cloudinary-storage` for media:

- Adds `cloudinary` and `cloudinary_storage` to `INSTALLED_APPS`.
- Sets `DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'`.
- If `CLOUDINARY_URL` is not provided, uses the discrete keys from env.
- `MEDIA_URL` remains for compatibility; uploaded files return absolute Cloudinary URLs.

### API Serialization Behavior
- `ImageField`/`FileField` `.url` values are absolute Cloudinary URLs.
- Services `images` JSON entries are normalized:
  - If a value is absolute (`http/https`), it’s returned as-is.
  - Otherwise, it’s treated as a Cloudinary public ID and converted to an absolute URL.

### Migration Notes
- If you have existing local files, upload them to Cloudinary and update DB rows where values are simple paths or filenames to match Cloudinary public IDs if desired.
- New uploads will automatically go to Cloudinary once env vars are set and the app is redeployed.

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
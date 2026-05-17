# Security Configuration Guide

## Overview

The updated `settings.py` implements strict security controls to prevent common vulnerabilities including:
- Host header injection (ALLOWED_HOSTS validation)
- CORS misconfiguration (explicit origin allowlist)
- Weak SECRET_KEY (minimum length validation)
- Hardcoded credentials (environment-only for sensitive keys)

## Required Environment Variables

### Critical (Required in Production)

#### `SECRET_KEY`
- **Description**: Django's secret key for cryptographic operations
- **Type**: String (minimum 50 characters recommended)
- **Generate**: `openssl rand -base64 32` or `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
- **Example**: `Super+7k9@mK#vL$pQ%wX&yZ!aB(cD)eF`
- **Production**: REQUIRED - application will fail to start without it
- **Development**: Optional - auto-generated (changes on each reload)

#### `DEBUG`
- **Description**: Django debug mode
- **Type**: Boolean (true/false)
- **Values**: 
  - `false` (production) - Enables strict security checks
  - `true` (development) - Relaxes some settings for convenience
- **Default**: `false`
- **Warning**: Never use `DEBUG=true` in production

#### `ALLOWED_HOSTS` (Production Only)
- **Description**: Comma-separated list of allowed hostnames
- **Type**: String (comma-separated values)
- **Examples**:
  ```
  ALLOWED_HOSTS=example.com,www.example.com,api.example.com
  ALLOWED_HOSTS=repairmybike.in,www.repairmybike.in
  ```
- **Production**: REQUIRED - application will fail to start without it
- **Development**: Auto-configured to `localhost,127.0.0.1,10.0.2.2,[::1]`
- **Security Note**: `*` (wildcard) is explicitly forbidden

#### `CORS_ALLOWED_ORIGINS` (Production Only)
- **Description**: Comma-separated list of allowed origins for CORS
- **Type**: String (comma-separated URLs)
- **Examples**:
  ```
  CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com,https://app.example.com
  CORS_ALLOWED_ORIGINS=https://repairmybike.in,https://admin.repairmybike.in
  ```
- **Production**: REQUIRED - application will fail to start without it
- **Development**: Auto-configured to common localhost variants (3000, 8000, 8080)
- **Important**: Must use HTTPS in production, HTTP only for development

#### `DESCOPE_PROJECT_ID`
- **Description**: Descope authentication service project ID
- **Type**: String
- **Source**: Descope console
- **Production**: REQUIRED for authentication to work
- **Development**: Optional (can be set for testing)
- **Note**: Must not use example/test credentials

#### `DESCOPE_MANAGEMENT_KEY`
- **Description**: Descope management API key
- **Type**: String
- **Source**: Descope console
- **Production**: REQUIRED for authentication to work
- **Development**: Optional (can be set for testing)
- **Security**: Treat as sensitive as database passwords

### Optional (Development/Production)

#### `CSRF_TRUSTED_ORIGINS` (Production Only)
- **Description**: Origins trusted for CSRF validation
- **Type**: String (comma-separated URLs)
- **Default**: Derived from ALLOWED_HOSTS if not set
- **Example**: `CSRF_TRUSTED_ORIGINS=https://example.com,https://www.example.com`

#### `DATABASE_URL`
- **Description**: Database connection string
- **Type**: String (PostgreSQL URI)
- **Production**: PostgreSQL URL with SSL
- **Development**: Optional (uses SQLite by default)
- **Example**: `postgresql://user:pass@host:5432/dbname?sslmode=require`

#### `REDIS_URL`
- **Description**: Redis cache connection string
- **Type**: String (Redis URI)
- **Production**: Recommended for performance
- **Development**: Optional (uses in-memory cache by default)
- **Example**: `redis://:password@host:6379/0`

#### `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET`
- **Description**: Razorpay payment gateway credentials
- **Type**: String
- **Source**: Razorpay dashboard
- **Optional**: Only if payments are enabled

#### `CLOUDINARY_URL` / Cloudinary Credentials
- **Description**: Cloudinary media storage
- **Type**: String (connection URL or individual credentials)
- **Optional**: Only if `USE_CLOUDINARY=true`

## Environment Setup Examples

### Development (.env file)

```bash
# Core settings
DEBUG=true
SECRET_KEY=dev-key-for-testing-only-change-this

# Database (optional - uses SQLite)
# DATABASE_URL=postgresql://user:pass@localhost:5432/repairmybike_dev

# Descope (optional for local testing)
DESCOPE_PROJECT_ID=your-test-project-id
DESCOPE_MANAGEMENT_KEY=your-test-management-key

# Razorpay (optional)
RAZORPAY_ENABLED=false
```

### Production (.env file or Platform Settings)

```bash
# Core settings - CRITICAL
DEBUG=false
SECRET_KEY=your-super-secure-50-character-key-from-openssl
ALLOWED_HOSTS=example.com,www.example.com,api.example.com
CORS_ALLOWED_ORIGINS=https://example.com,https://www.example.com,https://app.example.com

# Database - REQUIRED
DATABASE_URL=postgresql://user:very-secure-password@production-host:5432/repairmybike?sslmode=require

# Cache - RECOMMENDED
REDIS_URL=redis://:secure-password@redis-host:6379/0

# Authentication - REQUIRED
DESCOPE_PROJECT_ID=your-production-project-id
DESCOPE_MANAGEMENT_KEY=your-production-management-key

# Payments (if enabled)
RAZORPAY_KEY_ID=your-razorpay-key-id
RAZORPAY_KEY_SECRET=your-razorpay-secret

# Media Storage
USE_CLOUDINARY=true
CLOUDINARY_URL=cloudinary://key:secret@cloud-name
```

## Security Validation Checks

The application performs automatic security validation on startup:

### ALLOWED_HOSTS Validation
- ❌ Rejects `*` (wildcard)
- ✅ Requires explicit hostname list in production
- ✅ Auto-configured in development

### CORS Validation
- ❌ Rejects `CORS_ALLOW_ALL_ORIGINS=True` 
- ✅ Requires explicit origin allowlist
- ✅ Prevents credential + wildcard CORS vulnerability

### SECRET_KEY Validation
- ❌ Rejects missing SECRET_KEY in production
- ❌ Rejects SECRET_KEY < 32 characters
- ✅ Auto-generates for development only

### Production Mode Security
- ✅ Enforces SSL redirect
- ✅ Requires secure session cookies
- ✅ Requires secure CSRF cookies
- ✅ Validates ALLOWED_HOSTS is configured
- ✅ Validates Descope credentials

### Authentication Check
- ⚠️  Warns if Descope is not configured (may cause auth failures)

## Deploying to Railway

### 1. Set Environment Variables

In Railway dashboard → Environment tab:

```
DEBUG=false
SECRET_KEY=<generate with: openssl rand -base64 32>
ALLOWED_HOSTS=your-app.railway.app,your-domain.com,www.your-domain.com
CORS_ALLOWED_ORIGINS=https://your-app.railway.app,https://your-domain.com,https://www.your-domain.com
DESCOPE_PROJECT_ID=<your-production-project-id>
DESCOPE_MANAGEMENT_KEY=<your-production-management-key>
DATABASE_URL=<automatically set by Railway PostgreSQL plugin>
REDIS_URL=<set if you added Redis plugin>
```

### 2. Verify Security

After deployment, check logs for:
```
✅ SECURITY CONFIGURATION VALIDATED
  - DEBUG mode: OFF (Production)
  - ALLOWED_HOSTS: 3 host(s) allowed
  - CORS Origins: 2 origin(s) allowed
  - SSL Redirect: ENABLED
  - HSTS: 31536000 seconds
```

## Common Issues and Solutions

### Issue: "ALLOWED_HOSTS contains '*'"
**Cause**: Old settings.py with wildcard
**Solution**: Set `ALLOWED_HOSTS` to comma-separated list of actual hostnames

### Issue: "CORS_ALLOWED_ORIGINS is empty"
**Cause**: Production mode without CORS_ALLOWED_ORIGINS env var
**Solution**: Set `CORS_ALLOWED_ORIGINS` to your frontend URL(s)

### Issue: "SECRET_KEY is too short"
**Cause**: Using weak key
**Solution**: Generate new key: `openssl rand -base64 32`

### Issue: "ALLOWED_HOSTS environment variable is required in production"
**Cause**: Production mode (DEBUG=false) without ALLOWED_HOSTS
**Solution**: Set `ALLOWED_HOSTS` env var with your domain(s)

### Issue: "DESCOPE_PROJECT_ID and DESCOPE_MANAGEMENT_KEY are required"
**Cause**: Production mode without Descope credentials
**Solution**: Set both environment variables from your Descope console

## Security Best Practices

### ✅ DO:
- Generate unique SECRET_KEY for each environment
- Store sensitive variables in environment (not in code)
- Use HTTPS only in production
- Verify all ALLOWED_HOSTS values are legitimate domains you own
- Use strong, randomly generated values for API keys
- Rotate credentials regularly
- Enable DEBUG=false in production

### ❌ DON'T:
- Commit `.env` files to git
- Use `*` for ALLOWED_HOSTS (allows any Host header)
- Use `CORS_ALLOW_ALL_ORIGINS=True` with credentials
- Hardcode SECRET_KEY or API keys in settings.py
- Use same SECRET_KEY across environments
- Leave DEBUG=true in production
- Share credentials in logs or error messages

## Monitoring Security

### Check Production Configuration
```bash
# SSH into production and verify settings
curl https://your-domain.com/api/health/

# Check security headers in response
curl -I https://your-domain.com/api/health/
```

Expected headers:
```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
```

## Reference

- [Django Security Documentation](https://docs.djangoproject.com/en/5.2/topics/security/)
- [OWASP Security Headers](https://owasp.org/www-project-secure-headers/)
- [CORS Security Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Origin_Resource_Sharing_Cheat_Sheet.html)

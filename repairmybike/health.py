"""
Health check views for Railway deployment monitoring.
"""
import logging
from django.http import JsonResponse
from django.db import connection, transaction

logger = logging.getLogger(__name__)

@transaction.non_atomic_requests
def health_check(request):
    """
    Health check endpoint for Railway deployment monitoring.
    Runs non-atomically so database connectivity issues do not trigger
    an unhandled 500 error from the global ATOMIC_REQUESTS wrapper.
    """
    db_connected = False
    db_note = "Database query successful"
    try:
        # Basic database connectivity check
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_connected = True
    except Exception as e:
        logger.warning(f"Health check database query warning: {e}")
        db_connected = False
        db_note = f"Database unavailable: {type(e).__name__}"

    return JsonResponse({
        'status': 'healthy' if db_connected else 'degraded',
        'database': 'connected' if db_connected else 'disconnected',
        'version': '1.0.0',
        'note': db_note
    }, status=200 if db_connected else 503)

@transaction.non_atomic_requests
def readiness_check(request):
    """
    Readiness check for Railway deployment.
    Runs non-atomically to verify application process liveness independently.
    """
    return JsonResponse({
        'status': 'ready',
        'message': 'Application is ready to serve requests'
    }, status=200)

"""
Health check views for Railway deployment monitoring.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Health check endpoint for Railway deployment.
    Checks database connectivity and basic application health.
    """
    try:
        # Check database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        db_status = 'connected'
        
        # Check cache connectivity (gracefully handle failures)
        cache_status = 'disconnected'
        try:
            cache.set('health_check', 'ok', 30)
            if cache.get('health_check') == 'ok':
                cache_status = 'connected'
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            # Don't fail health check if cache is down
        
        return JsonResponse({
            'status': 'healthy',
            'database': db_status,
            'cache': cache_status,
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e),
            'database': 'disconnected',
            'cache': 'unknown'
        }, status=503)

def readiness_check(request):
    """
    Readiness check for Railway deployment.
    """
    return JsonResponse({
        'status': 'ready',
        'message': 'Application is ready to serve requests'
    })
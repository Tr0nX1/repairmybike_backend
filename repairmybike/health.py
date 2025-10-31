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
        
        # Check cache connectivity (if not in debug mode)
        try:
            cache.set('health_check', 'ok', 30)
            cache_status = cache.get('health_check') == 'ok'
        except Exception as e:
            logger.warning(f"Cache check failed: {e}")
            cache_status = False
        
        return JsonResponse({
            'status': 'healthy',
            'database': 'connected',
            'cache': 'connected' if cache_status else 'disconnected',
            'version': '1.0.0'
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JsonResponse({
            'status': 'unhealthy',
            'error': str(e)
        }, status=503)

def readiness_check(request):
    """
    Readiness check for Railway deployment.
    """
    return JsonResponse({
        'status': 'ready',
        'message': 'Application is ready to serve requests'
    })
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
    diag = {}

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

        # Safe diagnostic inspection (no secrets exposed)
        try:
            import socket
            from django.conf import settings
            db_conf = settings.DATABASES.get('default', {})
            host = db_conf.get('HOST', '')
            port = db_conf.get('PORT', '') or 5432
            
            diag['target_host'] = host or 'localhost'
            diag['target_port'] = port
            
            # Test target host DNS & TCP
            if host and host not in ['localhost', '127.0.0.1', '']:
                try:
                    resolved_ip = socket.gethostbyname(host)
                    diag['dns'] = f"resolved: {resolved_ip}"
                    try:
                        sock = socket.create_connection((resolved_ip, int(port)), timeout=3)
                        sock.close()
                        diag['tcp'] = "connected"
                    except Exception as tcp_err:
                        diag['tcp'] = f"failed: {type(tcp_err).__name__}"
                except Exception as dns_err:
                    diag['dns'] = f"failed: {type(dns_err).__name__}"

            # Probe common Railway internal candidate hostnames
            candidate_dns = {}
            for candidate in ['postgres.railway.internal', 'postgresql.railway.internal', 'repairmybikedb.railway.internal', 'database.railway.internal']:
                try:
                    c_ip = socket.gethostbyname(candidate)
                    candidate_dns[candidate] = f"resolved: {c_ip}"
                except Exception:
                    candidate_dns[candidate] = "unresolved"
            diag['candidates'] = candidate_dns
        except Exception:
            pass

    response_data = {
        'status': 'healthy' if db_connected else 'degraded',
        'database': 'connected' if db_connected else 'disconnected',
        'version': '1.0.0',
        'note': db_note
    }
    if diag:
        response_data['diagnostics'] = diag

    return JsonResponse(response_data, status=200 if db_connected else 503)

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

from django.http import JsonResponse
from django.db import connection

def health_check(request):
    health = {
        'status': 'ok',
        'database': 'down',
        'message': ''
    }
    try:
        connection.ensure_connection()
        health['database'] = 'ok'
    except Exception as e:
        health['status'] = 'error'
        health['message'] = str(e)
        
    return JsonResponse(health, status=200 if health['status'] == 'ok' else 500)
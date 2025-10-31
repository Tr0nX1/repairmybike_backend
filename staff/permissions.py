from rest_framework import permissions
from django.conf import settings


class IsStaffAPIKey(permissions.BasePermission):
    """
    Simple API key based authentication for staff endpoints
    """
    message = 'Invalid or missing API key'
    
    def has_permission(self, request, view):
        api_key = request.headers.get('X-API-Key')
        
        if not api_key:
            return False
        
        return api_key == settings.STAFF_API_KEY
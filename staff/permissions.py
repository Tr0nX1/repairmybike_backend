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


class IsStaffAuthenticated(permissions.BasePermission):
    """
    Authenticated user must be staff or superuser.
    Replaces API-key gate with identity-based authorization.
    """

    message = 'Staff access requires an authenticated staff/admin user'

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)
        return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))